"""Pinned ORAEC source acquisition and identity helpers."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

SOURCE_REPOSITORY = "https://github.com/oraec/corpus_raw_data.git"
DEFAULT_SOURCE_REVISION = "b83a0ee5fae27a40d4c0a2a9a8c9c2973d45e9cd"


class SourceAcquisitionError(RuntimeError):
    """Raised when a source checkout cannot be acquired or verified."""


@dataclass(frozen=True, slots=True)
class SourceSnapshot:
    """Identity of a locally acquired ORAEC source checkout."""

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


def resolve_revision(source: Path) -> str:
    """Return the exact HEAD revision for a local Git source checkout."""
    result = _run_git(["-C", str(source), "rev-parse", "HEAD"], capture_output=True)
    revision = result.stdout.strip()
    if not revision:
        raise SourceAcquisitionError(f"could not resolve source revision: {source}")
    return revision


def fetch_source(
    destination: str | Path,
    *,
    revision: str = DEFAULT_SOURCE_REVISION,
) -> SourceSnapshot:
    """Clone ORAEC to *destination*, detach at *revision*, and verify exact identity."""
    target = Path(destination)

    if target.exists():
        if not target.is_dir():
            raise SourceAcquisitionError(f"destination exists and is not a directory: {target}")
        if any(target.iterdir()):
            raise SourceAcquisitionError(f"destination is not empty: {target}")
    else:
        target.parent.mkdir(parents=True, exist_ok=True)

    _run_git(
        [
            "clone",
            "--filter=blob:none",
            "--no-checkout",
            SOURCE_REPOSITORY,
            str(target),
        ]
    )
    _run_git(["-C", str(target), "checkout", "--detach", revision])

    resolved = resolve_revision(target)
    if resolved != revision:
        raise SourceAcquisitionError(
            f"source revision mismatch: expected {revision}, resolved {resolved}"
        )

    return SourceSnapshot(path=target.resolve(), revision=resolved)
