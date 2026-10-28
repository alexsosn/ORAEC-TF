"""Release candidate #98: exact ORAEC version across source and installed-wheel gates."""

from __future__ import annotations

import ast
import tomllib
from pathlib import Path
from runpy import run_path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = "0.1.0rc1"


def _package_version() -> str:
    source = ast.parse(
        (ROOT / "src/oraec_tf/__init__.py").read_text(encoding="utf-8")
    )
    versions = [
        node.value.value
        for node in source.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "__version__"
                for target in node.targets)
        and isinstance(node.value, ast.Constant)
    ]
    assert len(versions) == 1
    assert isinstance(versions[0], str)
    return versions[0]


def test_release_candidate_metadata_is_frozen_and_consistent() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
        "project"
    ]
    assert project["version"] == CANDIDATE
    assert _package_version() == CANDIDATE
    assert "tf-build==0.1.0rc1" in project["dependencies"]
    assert all("git+" not in requirement for requirement in project["dependencies"])


def test_real_wheel_and_installed_smoke_enforce_candidate_version() -> None:
    verifier = run_path(str(ROOT / "scripts/validate_wheelhouse_install.py"))
    smoke = run_path(str(ROOT / "scripts/smoke_installed_distribution.py"))
    assert verifier["ORAEC_VERSION"] == CANDIDATE
    assert smoke["ORAEC_VERSION"] == CANDIDATE


def test_readme_clearly_identifies_unpublished_candidate() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert CANDIDATE in readme
    assert "not yet published" in readme
    assert "issue #12" in readme
    assert "tf-build==0.1.0rc1" in readme


@pytest.mark.parametrize("version", ["0.1.0.dev0", "0.1.0", "0.1.0rc2"])
def test_verifier_rejects_wrong_oraec_wheel_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, version: str,
) -> None:
    import hashlib
    import zipfile

    wheels = tmp_path / "wheels"
    wheels.mkdir()
    for name, release, requirement in (
        ("oraec-tf", version, "tf-build==0.1.0rc1"),
        ("tf-build", "0.1.0rc1", ""),
    ):
        normalized = name.replace("-", "_")
        path = wheels / f"{normalized}-{release}-py3-none-any.whl"
        metadata = (
            f"Metadata-Version: 2.1\\nName: {name}\\nVersion: {release}\\n"
        )
        if requirement:
            metadata += f"Requires-Dist: {requirement}\\n"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr(
                f"{normalized}-{release}.dist-info/METADATA",
                metadata.replace("\\n", "\n"),
            )
    verifier = run_path(str(ROOT / "scripts/validate_wheelhouse_install.py"))
    tf_build = next(wheels.glob("tf_build-*.whl"))
    writer = verifier["write_hash_manifest"]
    monkeypatch.setitem(
        writer.__globals__, "TF_BUILD_SHA256",
        hashlib.sha256(tf_build.read_bytes()).hexdigest(),
    )
    with pytest.raises(ValueError, match="unexpected ORAEC-TF"):
        writer(wheels, tmp_path / "manifest.txt")
    assert not (tmp_path / "manifest.txt").exists()
