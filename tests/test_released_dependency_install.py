"""Issue #59: test real pip resolution, not a --no-deps installation."""

from __future__ import annotations

import hashlib
import subprocess
import tomllib
import zipfile
from pathlib import Path
from runpy import run_path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _wheel(root: Path, name: str, version: str, *dependencies: str) -> Path:
    normalized = name.replace("-", "_")
    info = f"{normalized}-{version}.dist-info"
    path = root / f"{normalized}-{version}-py3-none-any.whl"
    metadata = f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n"
    metadata += "".join(f"Requires-Dist: {item}\n" for item in dependencies)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(f"{info}/METADATA", metadata + "\n")
        archive.writestr(
            f"{info}/WHEEL",
            "Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        )
        archive.writestr(f"{info}/RECORD", "")
    return path


def _verifier() -> dict[str, Any]:
    return run_path(str(ROOT / "scripts" / "validate_wheelhouse_install.py"))


def test_package_requires_the_released_version_without_a_vcs_url() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    assert "tf-build==0.1.0rc1" in project["dependencies"]
    assert not any("git+" in item for item in project["dependencies"])


@pytest.mark.parametrize("missing_dependency", [False, True])
def test_real_offline_resolver_and_relocatable_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, missing_dependency: bool,
) -> None:
    wheels = tmp_path / "original wheelhouse"
    wheels.mkdir()
    _wheel(wheels, "oraec-tf", "0.1.0rc1", "tf-build==0.1.0rc1")
    tf_build = _wheel(wheels, "tf-build", "0.1.0rc1", "test-leaf==1.0")
    if not missing_dependency:
        _wheel(wheels, "test-leaf", "1.0")
    module = _verifier()
    writer = module["write_hash_manifest"]
    monkeypatch.setitem(
        writer.__globals__, "TF_BUILD_SHA256",
        hashlib.sha256(tf_build.read_bytes()).hexdigest(),
    )
    lock = tmp_path / "requirements.txt"
    writer(wheels, lock)
    assert "file:" not in lock.read_text()
    assert "tf-build==0.1.0rc1 --hash=sha256:" in lock.read_text()
    moved = tmp_path / "relocated wheelhouse"
    wheels.rename(moved)
    source = tmp_path / "source"
    scripts = source / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "smoke_installed_distribution.py").write_text(
        "import shutil\nfrom importlib.metadata import version\n"
        "assert shutil.which('git') is None\n"
        "assert version('test-leaf') == '1.0'\n",
    )
    # No index, no Git, and pip must resolve tf-build's declared dependency.
    monkeypatch.setenv("PIP_INDEX_URL", "https://example.invalid/never")
    monkeypatch.setenv("PIP_FIND_LINKS", "https://example.invalid/never")
    install = module["verify_installed_wheels"]
    if missing_dependency:
        with pytest.raises(subprocess.CalledProcessError) as error:
            install(source, lock, tmp_path / "venv", wheelhouse=moved)
        assert "install" in error.value.cmd  # resolution fails before pip check/smoke
        assert "--no-deps" not in error.value.cmd
    else:
        # The documented CLI accepts relative paths while its subprocesses
        # deliberately run outside the source checkout.
        monkeypatch.chdir(tmp_path)
        (tmp_path / "nested").mkdir()
        install(
            Path("source"), Path("requirements.txt"), Path("nested/venv"),
            wheelhouse=Path("relocated wheelhouse"),
        )


def test_manifest_rejects_substituted_release_wheel(tmp_path: Path) -> None:
    _wheel(tmp_path, "oraec-tf", "0.1.0rc1", "tf-build==0.1.0rc1")
    _wheel(tmp_path, "tf-build", "0.1.0rc1")
    with pytest.raises(ValueError, match="SHA256"):
        _verifier()["write_hash_manifest"](tmp_path, tmp_path / "lock.txt")
    assert not (tmp_path / "lock.txt").exists()


def test_manifest_refuses_transitive_direct_url(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _wheel(tmp_path, "oraec-tf", "0.1.0rc1", "tf-build==0.1.0rc1")
    tf_build = _wheel(tmp_path, "tf-build", "0.1.0rc1", "leaf@https://example.invalid/x.whl")
    writer = _verifier()["write_hash_manifest"]
    monkeypatch.setitem(
        writer.__globals__, "TF_BUILD_SHA256",
        hashlib.sha256(tf_build.read_bytes()).hexdigest(),
    )
    with pytest.raises(ValueError, match="direct URLs"):
        writer(tmp_path, tmp_path / "lock.txt")
    assert not (tmp_path / "lock.txt").exists()
