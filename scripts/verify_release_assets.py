"""Check real ORAEC software release archives and record their immutable digests.

No extraction, corpus payload or network requests. The ordinary wheel and the
sdist-rebuilt wheel must agree on actual package, metadata and app payload bytes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from email.parser import Parser
from pathlib import Path
from runpy import run_path
from typing import Any

VERSION = "0.1.0rc1"
FORMAT = "oraec-software-release-assets-v1"


def _wheel_members(path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as archive:
        members = {
            name: archive.read(name)
            for name in archive.namelist()
            if (
                name.startswith("oraec_tf/") or name.endswith(".dist-info/METADATA")
                or name.endswith(".dist-info/entry_points.txt")
            ) and not name.endswith("/")
        }
    metadata_names = [name for name in members if name.endswith(".dist-info/METADATA")]
    if len(metadata_names) != 1:
        raise ValueError("release wheel must have exactly one METADATA file")
    metadata = Parser().parsestr(members[metadata_names[0]].decode("utf-8"))
    if metadata.get("Name", "").lower().replace("_", "-") != "oraec-tf":
        raise ValueError("release wheel METADATA has wrong distribution name")
    if metadata.get("Version") != VERSION:
        raise ValueError("release wheel METADATA has wrong version")
    if "oraec_tf/__init__.py" not in members:
        raise ValueError("release wheel missing package source")
    return members


def _entry(path: Path) -> dict[str, Any]:
    return {
        "name": path.name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "size": path.stat().st_size,
    }


def verify_release_assets(
    wheel: Path, sdist: Path, rebuilt_wheel: Path, *,
    revision: str, manifest: Path,
) -> dict[str, object]:
    """Audit both software distributions, compare rebuilt content, write digest record."""
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("source revision must be an exact lowercase 40-hex commit")
    name = f"oraec_tf-{VERSION}-py3-none-any.whl"
    if wheel.name != name or rebuilt_wheel.name != name:
        raise ValueError("unexpected release wheel version/name")
    if sdist.name != f"oraec_tf-{VERSION}.tar.gz":
        raise ValueError("unexpected sdist version/name")
    if manifest.exists():
        raise ValueError("release manifest must not already exist")

    audit = run_path(str(Path(__file__).resolve().parent / "audit_software_release.py"))
    audit["audit_wheel"](wheel)
    audit["audit_sdist"](sdist)
    audit["audit_wheel"](rebuilt_wheel)

    source = _wheel_members(wheel)
    rebuilt = _wheel_members(rebuilt_wheel)
    if source != rebuilt:
        changed = sorted(
            path for path in source.keys() | rebuilt.keys()
            if source.get(path) != rebuilt.get(path)
        )
        raise ValueError(f"sdist-rebuilt wheel software payload differs: {changed}")

    report: dict[str, object] = {
        "format": FORMAT,
        "version": VERSION,
        "source_revision": revision,
        "artifacts": [_entry(wheel), _entry(sdist)],
    }
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def verify_staged_manifest(directory: Path, manifest: Path, revision: str) -> None:
    """Recheck exactly the three allowed release files after CI artifact transfer."""
    report = json.loads(manifest.read_text(encoding="utf-8"))
    if (
        report.get("format") != FORMAT or report.get("version") != VERSION
        or report.get("source_revision") != revision
    ):
        raise ValueError("release manifest identity mismatch")
    artifacts = report.get("artifacts")
    if not isinstance(artifacts, list) or len(artifacts) != 2:
        raise ValueError("release manifest must name precisely wheel and sdist")
    expected = {
        f"oraec_tf-{VERSION}-py3-none-any.whl",
        f"oraec_tf-{VERSION}.tar.gz",
    }
    if {a.get("name") for a in artifacts if isinstance(a, dict)} != expected:
        raise ValueError("release manifest contains unexpected assets")
    names = {p.name for p in directory.iterdir()}
    if names != expected | {manifest.name}:
        raise ValueError(f"unexpected staged release files: {sorted(names)}")
    for entry in artifacts:
        path = directory / entry["name"]
        if not path.is_file() or path.is_symlink() or _entry(path) != entry:
            raise ValueError(f"release asset digest/size mismatch: {path.name}")
    audit = run_path(str(Path(__file__).resolve().parent / "audit_software_release.py"))
    audit["audit_wheel"](directory / f"oraec_tf-{VERSION}-py3-none-any.whl")
    audit["audit_sdist"](directory / f"oraec_tf-{VERSION}.tar.gz")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheel", type=Path)
    parser.add_argument("--sdist", type=Path)
    parser.add_argument("--rebuilt-wheel", type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--verify-staged", type=Path)
    args = parser.parse_args()
    if args.verify_staged:
        verify_staged_manifest(args.verify_staged, args.manifest, args.revision)
    elif args.wheel and args.sdist and args.rebuilt_wheel:
        verify_release_assets(
            args.wheel, args.sdist, args.rebuilt_wheel,
            revision=args.revision, manifest=args.manifest,
        )
    else:
        parser.error("provide --verify-staged or all three archive paths")
    print("ORAEC software release asset inventory and SHA256 OK")


if __name__ == "__main__":
    main()
