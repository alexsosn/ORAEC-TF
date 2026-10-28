"""Fail closed if an ORAEC software wheel/sdist contains corpus or cache payloads.

The release distributes only the converter, standard Text-Fabric app/configuration,
schema, tests and documentation. This inspect-only tool never extracts archives.
"""

from __future__ import annotations

import argparse
import re
import stat
import tarfile
import zipfile
from pathlib import Path

_WHEEL_RESOURCES = {"schema_core.json", "tf_app/config.yaml"}
_WHEEL_METADATA = {
    "METADATA", "WHEEL", "RECORD", "entry_points.txt", "top_level.txt",
    "LICENSE", "licenses/LICENSE",
}
_SDIST_ROOT_FILES = {
    "README.md", "LICENSE", "LICENSE_SCOPE.md", "AGENTS.md", "CONTRIBUTING.md",
    "MANIFEST.in", "setup.py", "pyproject.toml", "plan.md", "research.md",
    "design.md", "agora.materializer.json",
}
_EGG_METADATA = {
    "PKG-INFO", "SOURCES.txt", "requires.txt", "entry_points.txt",
    "top_level.txt", "dependency_links.txt",
}
_REQUIRED_WHEEL = {
    "oraec_tf/__init__.py",
    "oraec_tf/schema_core.json",
    "oraec_tf/tf_app/config.yaml",
}
_REQUIRED_SDIST = {
    "pyproject.toml", "schema/core.json", "src/oraec_tf/__init__.py",
    "src/oraec_tf/tf_app/config.yaml",
}


def _checked_parts(name: str) -> tuple[str, ...]:
    """Reject path traversal, ambiguous separators and empty components."""
    if not name or name.startswith("/") or "\\" in name:
        raise ValueError(f"unsafe software archive path: {name!r}")
    clean = name.rstrip("/")
    parts = tuple(clean.split("/"))
    if any(part in {"", ".", ".."} for part in parts):
        raise ValueError(f"unsafe software archive path: {name!r}")
    return parts


def _wheel_is_software(name: str) -> bool:
    if name.startswith("oraec_tf/"):
        relative = name.removeprefix("oraec_tf/")
        return relative.endswith(".py") or relative in _WHEEL_RESOURCES
    head, sep, member = name.partition("/")
    if not sep or re.fullmatch(r"oraec_tf-[^/]+\\.dist-info", head) is None:
        return False
    return member in _WHEEL_METADATA


def _sdist_is_software(relative: str) -> bool:
    if relative in _SDIST_ROOT_FILES or relative in {
        "schema/core.json", "app/config.yaml",
    }:
        return True
    if relative.startswith("src/oraec_tf/"):
        member = relative.removeprefix("src/oraec_tf/")
        return member.endswith(".py") or member in _WHEEL_RESOURCES
    if relative.startswith("src/oraec_tf.egg-info/"):
        return relative.removeprefix("src/oraec_tf.egg-info/") in _EGG_METADATA
    if relative.startswith("tests/"):
        return relative.endswith(".py")
    if relative.startswith("scripts/"):
        return relative.endswith(".py")
    if relative.startswith("docs/"):
        return relative.endswith(".md")
    if relative.startswith("requirements/"):
        return relative.endswith((".in", ".lock", ".txt"))
    if relative.startswith(".github/workflows/"):
        return relative.endswith((".yml", ".yaml"))
    return False


def audit_wheel(archive_path: Path) -> None:
    """Inspect all actual wheel members; do not assume setuptools exclusions."""
    seen: set[str] = set()
    with zipfile.ZipFile(archive_path) as archive:
        for member in archive.infolist():
            _checked_parts(member.filename)
            if member.create_system == 3 and stat.S_IFMT(member.external_attr >> 16) == stat.S_IFLNK:
                raise ValueError(f"symlink in wheel: {member.filename}")
            if member.is_dir():
                continue
            if member.filename in seen:
                raise ValueError(f"duplicate wheel member: {member.filename}")
            seen.add(member.filename)
            if not _wheel_is_software(member.filename):
                raise ValueError(f"non-software wheel member: {member.filename}")
    missing = _REQUIRED_WHEEL - seen
    if missing:
        raise ValueError(f"wheel missing mandatory software resources: {sorted(missing)}")


def audit_sdist(archive_path: Path) -> None:
    """Inspect every tar member under exactly one sdist prefix, without extraction."""
    seen: set[str] = set()
    roots: set[str] = set()
    with tarfile.open(archive_path, "r:gz") as archive:
        for member in archive.getmembers():
            parts = _checked_parts(member.name)
            root = parts[0]
            roots.add(root)
            if not re.fullmatch(r"oraec_tf-[^/]+", root):
                raise ValueError(f"unexpected source archive root: {root}")
            if not (member.isfile() or member.isdir()):
                raise ValueError(f"nonregular source archive member: {member.name}")
            if len(parts) == 1:
                if not member.isdir():
                    raise ValueError(f"unexpected root file: {member.name}")
                continue
            relative = "/".join(parts[1:])
            if member.isdir():
                continue
            if relative in seen:
                raise ValueError(f"duplicate sdist member: {relative}")
            seen.add(relative)
            if not _sdist_is_software(relative):
                raise ValueError(f"non-software sdist member: {relative}")
    if len(roots) != 1:
        raise ValueError(f"sdist must have exactly one source root: {sorted(roots)}")
    missing = _REQUIRED_SDIST - seen
    if missing:
        raise ValueError(f"sdist missing mandatory software resources: {sorted(missing)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit an ORAEC software-only release archive")
    parser.add_argument("archives", nargs="+", type=Path)
    args = parser.parse_args()
    for archive in args.archives:
        if archive.suffix == ".whl":
            audit_wheel(archive)
        elif archive.name.endswith(".tar.gz"):
            audit_sdist(archive)
        else:
            parser.error(f"unsupported software archive: {archive}")
        print(f"Software-only inventory OK: {archive.name}")


if __name__ == "__main__":
    main()
