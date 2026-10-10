"""Agora materializer: a thin, offline, transactional wrapper around the public CLI.

Agora acquires the pinned source and constrains execution to no network. This
module does not fetch, parse, or transform ORAEC semantics itself: it invokes
the same public conversion path as a researcher running `oraec-tf convert`.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import shutil
import tempfile
from importlib.metadata import version
from pathlib import Path
from collections.abc import Sequence
from typing import Any

from . import cli
from .source import (
    DEFAULT_SOURCE_REVISION,
    SOURCE_REPOSITORY,
    SourceAcquisitionError,
    validate_revision,
)

REQUIRED_WARP = ("otype.tf", "oslots.tf", "otext.tf")


def _fingerprints(tf_path: Path) -> dict[str, str]:
    """Hash research features without copying their source contents."""
    result: dict[str, str] = {}
    for path in sorted(tf_path.glob("*.tf")):
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        result[path.name] = digest.hexdigest()
    return result


def materialize(
    source: str | Path, destination: str | Path, *,
    source_revision: str = DEFAULT_SOURCE_REVISION,
) -> dict[str, Any]:
    """Build only standard TF plus minimal output validation/provenance.

    No partial artifact can be published: conversion happens in a private
    sibling staging directory; final destination is renamed only on success.
    """
    try:
        revision = validate_revision(source_revision)
    except SourceAcquisitionError as exc:
        raise ValueError(f"invalid source revision: {source_revision!r}") from exc
    if revision != DEFAULT_SOURCE_REVISION:
        raise ValueError("unsupported source revision for frozen ORAEC schema")

    target = Path(destination)
    if target.is_symlink() or (target.exists() and (
        not target.is_dir() or any(target.iterdir())
    )):
        raise ValueError("output must be an absent or empty directory, not a symlink")

    source_path = Path(source).resolve()
    resolved_target = target.resolve()
    if source_path == resolved_target or source_path in resolved_target.parents:
        raise ValueError("output cannot be inside the ORAEC source worktree")

    parent = target.parent
    parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{target.name}.agora-", dir=parent))
    preexisting_empty_dir = target.exists()
    try:
        tf_dir = stage / "tf"
        capture = io.StringIO()
        with contextlib.redirect_stdout(capture):
            exit_code = cli.main([
                "convert", str(source),
                "--output", str(tf_dir),
                "--upstream-commit", revision,
            ])
        if exit_code != 0:
            raise RuntimeError(f"ORAEC conversion exited with {exit_code}")
        try:
            cli_summary = json.loads(capture.getvalue())
        except json.JSONDecodeError as exc:
            raise RuntimeError("converter did not produce its JSON summary") from exc
        if not isinstance(cli_summary, dict):
            raise RuntimeError("converter summary must be an object")
        if cli_summary.get("revision") != revision:
            raise RuntimeError("converter reported wrong source revision")
        if cli_summary.get("output") != str(tf_dir.resolve()):
            raise RuntimeError("converter reported wrong artifact path")
        if not isinstance(cli_summary.get("counts"), dict):
            raise RuntimeError("converter omitted native TF conservation counts")
        missing = [name for name in REQUIRED_WARP if not (tf_dir / name).is_file()]
        if missing:
            raise RuntimeError(f"converted TF missing mandatory warp files: {missing}")
        hashes = _fingerprints(tf_dir)
        if not hashes:
            raise RuntimeError("converted TF has no feature files")
        report: dict[str, Any] = {
            "format": "text-fabric",
            "source_repository": SOURCE_REPOSITORY,
            "source_revision": revision,
            "converter_package": "oraec-tf",
            "converter_version": version("oraec-tf"),
            "validation": "public CLI pinned-source preflight + TF reload and counts",
            "counts": cli_summary["counts"],
            "tf_sha256": hashes,
        }
        (stage / "conversion-summary.json").write_text(
            json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        if preexisting_empty_dir:
            target.rmdir()
        stage.replace(target)
        return report
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        if preexisting_empty_dir and not target.exists():
            target.mkdir()
        raise


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Agora offline ORAEC-TF materializer")
    parser.add_argument("source", type=Path, help="Agora-provided pinned Git source")
    parser.add_argument("output", type=Path, help="empty output artifact root")
    parser.add_argument("--source-revision", required=True)
    args = parser.parse_args(argv)
    result = materialize(
        args.source, args.output, source_revision=args.source_revision,
    )
    print(json.dumps({
        "ok": True,
        "source_revision": result["source_revision"],
        "counts": result["counts"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
