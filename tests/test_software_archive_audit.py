"""Release gate #100: reject corpus and non-software content in built archives."""

from __future__ import annotations

import io
import stat
import tarfile
import zipfile
from collections.abc import Callable
from pathlib import Path
from runpy import run_path
from typing import cast

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _audit(which: str, archive: Path) -> None:
    module = run_path(str(ROOT / "scripts/audit_software_release.py"))
    checker = cast(Callable[[Path], None], module[which])
    checker(archive)


def _wheel(path: Path, extra: str | None = None, *, symlink: bool = False) -> Path:
    members = {
        "oraec_tf/__init__.py": "version = '0.1.0rc1'",
        "oraec_tf/schema_core.json": "{}",
        "oraec_tf/tf_app/config.yaml": "apiVersion: 3",
        "oraec_tf-0.1.0rc1.dist-info/METADATA": "Name: oraec-tf",
        "oraec_tf-0.1.0rc1.dist-info/WHEEL": "Wheel-Version: 1.0",
        "oraec_tf-0.1.0rc1.dist-info/RECORD": "",
    }
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in members.items():
            archive.writestr(name, content)
        if extra:
            if symlink:
                link = zipfile.ZipInfo(extra)
                link.create_system = 3
                link.external_attr = (stat.S_IFLNK | 0o777) << 16
                archive.writestr(link, "/private/corpus")
            else:
                archive.writestr(extra, "corpus bytes")
    return path


def _sdist(path: Path, extra: str | None = None, *, symlink: bool = False) -> Path:
    prefix = "oraec_tf-0.1.0rc1/"
    members = [
        "README.md", "pyproject.toml", "schema/core.json",
        "src/oraec_tf/__init__.py", "src/oraec_tf/tf_app/config.yaml",
        "tests/test_writer_wheel.py",
    ]
    if extra:
        members.append(extra)
    with tarfile.open(path, "w:gz") as archive:
        for name in members:
            info = tarfile.TarInfo(prefix + name)
            if symlink and name == extra:
                info.type = tarfile.SYMTYPE
                info.linkname = "/private/corpus"
                archive.addfile(info)
            else:
                data = b"synthetic software file"
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))
    return path


def test_valid_software_archive_members_and_canonical_resources(tmp_path: Path) -> None:
    _audit("audit_wheel", _wheel(tmp_path / "clean.whl"))
    _audit("audit_sdist", _sdist(tmp_path / "clean.tar.gz"))


@pytest.mark.parametrize(
    "member",
    [
        "oraec_tf/otype.tf",
        "oraec_tf/oraec1.json",
        "oraec_tf/mapping_oraec_karnak.tsv",
        "oraec_tf/cache/4/features.cfr",
        "oraec_tf/_cache/generated.tfx",
        "oraec_tf/unknown_resource.json",
        "unexpected_package/data.py",
        "../oraec1.json",
    ],
)
def test_wheel_rejects_non_software_payload(tmp_path: Path, member: str) -> None:
    with pytest.raises(ValueError):
        _audit("audit_wheel", _wheel(tmp_path / "forged.whl", member))


@pytest.mark.parametrize(
    "member",
    [
        "oraec1.json",
        "mapping_oraec_karnak.tsv",
        "reports/generated/tf/otype.tf",
        "src/oraec_tf/other.json",
        "src/oraec_tf/cache/4/features.cfr",
        "../foreign.txt",
    ],
)
def test_sdist_rejects_non_software_payload(tmp_path: Path, member: str) -> None:
    with pytest.raises(ValueError):
        _audit("audit_sdist", _sdist(tmp_path / "forged.tar.gz", member))


@pytest.mark.parametrize("kind", ["wheel", "sdist"])
def test_archives_reject_symlinks(tmp_path: Path, kind: str) -> None:
    if kind == "wheel":
        path = _wheel(tmp_path / "link.whl", "oraec_tf/link.py", symlink=True)
        operation = "audit_wheel"
    else:
        path = _sdist(tmp_path / "link.tar.gz", "docs/link.md", symlink=True)
        operation = "audit_sdist"
    with pytest.raises(ValueError):
        _audit(operation, path)


def test_archive_audit_changes_trigger_real_installed_wheel_job() -> None:
    workflow = (ROOT / ".github/workflows/installed-wheelhouse.yml").read_text(
        encoding="utf-8"
    )
    paths = workflow.split("pull_request:", 1)[1].split("permissions:", 1)[0]
    for item in (
        "scripts/audit_software_release.py",
        "tests/test_software_archive_audit.py",
        "tests/test_writer_wheel.py",
    ):
        assert f'"{item}"' in paths
