"""Pinned ORAEC source acquisition and identity helpers."""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

SOURCE_REPOSITORY = "https://github.com/oraec/corpus_raw_data.git"
DEFAULT_SOURCE_REVISION = "b83a0ee5fae27a40d4c0a2a9a8c9c2973d45e9cd"

FULL_COMMIT_RE = re.compile(r"^[0-9a-fA-F]{40}$")


class SourceAcquisitionError(RuntimeError):
    """Raised when a source checkout cannot be acquired or verified."""


@dataclass(frozen=True, slots=True)
class SourceSnapshot:
    """Identity of a verified local ORAEC source checkout."""

    path: Path
    revision: str


def _run_git(
    args: list[str], *, capture_output: bool = False
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["git", *args],
            check=True,
            capture_output=capture_output,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise SourceAcquisitionError(f"git command failed: {' '.join(args)}") from exc


def validate_revision(revision: str) -> str:
    """Return a normalized immutable Git commit id or reject the revision."""
    if not FULL_COMMIT_RE.fullmatch(revision):
        raise SourceAcquisitionError(
            "source revision must be a full 40-hex immutable Git commit id"
        )
    return revision.lower()


def resolve_revision(source: Path) -> str:
    """Return the exact HEAD revision for a local Git source checkout."""
    result = _run_git(["-C", str(source), "rev-parse", "HEAD"], capture_output=True)
    revision = result.stdout.strip()
    if not revision:
        raise SourceAcquisitionError(f"could not resolve source revision: {source}")
    try:
        return validate_revision(revision)
    except SourceAcquisitionError as exc:
        raise SourceAcquisitionError(
            f"git returned a non-commit source revision for {source}: {revision!r}"
        ) from exc


def verify_source(
    source: str | Path,
    *,
    expected_revision: str | None = None,
) -> SourceSnapshot:
    """Verify that *source* is a clean Git checkout at the expected commit."""
    path = Path(source).resolve()
    if not path.is_dir():
        raise SourceAcquisitionError(f"source directory does not exist: {path}")

    expected = (
        None if expected_revision is None else validate_revision(expected_revision)
    )
    resolved = resolve_revision(path)

    if expected is not None and resolved != expected:
        raise SourceAcquisitionError(
            f"source revision mismatch: expected {expected}, resolved {resolved}"
        )

    status = _run_git(
        [
            "-C",
            str(path),
            "status",
            "--porcelain",
            "--untracked-files=all",
        ],
        capture_output=True,
    ).stdout
    if status.strip():
        raise SourceAcquisitionError(f"source checkout is dirty: {path}")

    return SourceSnapshot(path=path, revision=resolved)


def fetch_source(
    destination: str | Path,
    *,
    revision: str = DEFAULT_SOURCE_REVISION,
) -> SourceSnapshot:
    """Fetch one immutable ORAEC commit and atomically install a clean checkout."""
    requested_revision = validate_revision(revision)
    target = Path(destination)
    # exists() is false for dangling symlinks; never overwrite an existing link.
    target_preexisted = target.exists() or target.is_symlink()

    if target_preexisted:
        if target.is_symlink():
            raise SourceAcquisitionError(f"destination must not be a symlink: {target}")
        if not target.is_dir():
            raise SourceAcquisitionError(
                f"destination exists and is not a directory: {target}"
            )
        if any(target.iterdir()):
            raise SourceAcquisitionError(f"destination is not empty: {target}")

    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(
            prefix=f".{target.name}.oraec-tf-",
            dir=target.parent,
        )
    )

    try:
        _run_git(["-C", str(staging), "init", "--quiet"])
        _run_git(
            [
                "-C",
                str(staging),
                "remote",
                "add",
                "origin",
                SOURCE_REPOSITORY,
            ]
        )
        _run_git(
            [
                "-C",
                str(staging),
                "fetch",
                "--depth",
                "1",
                "origin",
                requested_revision,
            ]
        )
        _run_git(
            [
                "-C",
                str(staging),
                "checkout",
                "--detach",
                "FETCH_HEAD",
            ]
        )
        snapshot = verify_source(
            staging,
            expected_revision=requested_revision,
        )

        if target_preexisted:
            target.rmdir()
        staging.replace(target)

        return SourceSnapshot(
            path=target.resolve(),
            revision=snapshot.revision,
        )
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        if target_preexisted and not target.exists():
            target.mkdir(parents=False, exist_ok=True)
        raise
