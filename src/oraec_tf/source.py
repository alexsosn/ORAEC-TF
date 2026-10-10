"""Pinned ORAEC source acquisition and identity helpers."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from tf_build.source import (
    GitSourceError,
    fetch_git_source,
    validate_git_revision,
    verify_git_source,
)

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
    try:
        return validate_git_revision(revision)
    except GitSourceError as exc:
        raise SourceAcquisitionError(str(exc)) from exc


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
    """Verify a clean ORAEC Git worktree root at an immutable 40-hex commit."""
    expected = (
        None if expected_revision is None else validate_revision(expected_revision)
    )
    path = Path(source).resolve()
    if not path.is_dir():
        raise SourceAcquisitionError(f"source directory does not exist: {path}")
    try:
        verified = verify_git_source(
            path, expected_revision=expected, reject_ignored_files=True,
        )
    except GitSourceError as exc:
        raise SourceAcquisitionError(str(exc)) from exc
    if verified.path != verified.repository_root:
        raise SourceAcquisitionError(
            f"source path must be the Git worktree root: {path}"
        )
    return SourceSnapshot(path=verified.path, revision=validate_revision(verified.revision))


def fetch_source(
    destination: str | Path,
    *,
    revision: str = DEFAULT_SOURCE_REVISION,
) -> SourceSnapshot:
    """Acquire one pinned 40-hex ORAEC commit without publishing remote credentials."""
    requested = validate_revision(revision)
    try:
        verified = fetch_git_source(
            SOURCE_REPOSITORY,
            destination,
            revision=requested,
        )
    except (GitSourceError, OSError) as exc:
        # Preserve ORAEC's public error contract while delegating atomic
        # no-clobber publication, Git timeouts and staging cleanup to tf-build.
        raise SourceAcquisitionError(str(exc)) from exc
    return SourceSnapshot(
        path=verified.path, revision=validate_revision(verified.revision)
    )
