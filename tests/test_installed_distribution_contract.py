"""RED: independent wheelhouse install must exercise the *installed* package.

An editable-checkout pytest pass does not prove that the oraec-tf wheel has
all its modules, scripts, schema resources, or compatible pinned dependencies.
"""

from __future__ import annotations

import ast
import hashlib
import zipfile
from pathlib import Path

import pytest

from scripts.validate_wheelhouse_install import write_hash_manifest

ROOT = Path(__file__).resolve().parents[1]


def test_installed_smoke_is_syntax_valid_and_checks_real_wheel_api() -> None:
    path = ROOT / "scripts" / "smoke_installed_distribution.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    functions = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    required_functions = {
        "verify_installed_modules", "verify_native_tf", "verify_no_clobber", "main",
    }
    assert required_functions <= functions
    for required in (
        "ORAEC_SOURCE_TREE",
        "NativeCRIndex",
        "publish_path_no_clobber",
        "0.1.0.dev0",
        "source-info",
        "bibliography",
    ):
        assert required in source


def test_ci_builds_wheels_online_but_installs_offline_without_git() -> None:
    # Parse the YAML as raw text to keep this regression test independent
    # from PyYAML's YAML-1.1 handling of GitHub Actions 'on' keys.
    workflow = (
        ROOT / ".github" / "workflows" / "installed-wheelhouse.yml"
    ).read_text(encoding="utf-8")
    runner = (
        ROOT / "scripts" / "validate_wheelhouse_install.py"
    ).read_text(encoding="utf-8")
    assert "pip wheel" in workflow
    for required in (
        "--no-index",
        "--no-deps",
        "pip check",
        "smoke_installed_distribution.py",
        "sha256",
        "ORAEC_SOURCE_TREE",
    ):
        assert required in runner
    assert "pip install -e" not in workflow
    assert "workflow_dispatch:" in workflow


def test_offline_wheelhouse_runs_real_windows_and_linux_installed_smokes() -> None:
    """#59: Linux-only source-built wheelhouse is not cross-platform evidence."""
    workflow = (
        ROOT / ".github" / "workflows" / "installed-wheelhouse.yml"
    ).read_text(encoding="utf-8")
    helper = ROOT / "scripts" / "validate_wheelhouse_install.py"
    assert helper.is_file(), "wheelhouse verifier must be platform portable"
    source = helper.read_text(encoding="utf-8")
    ast.parse(source, filename=str(helper))
    assert "ubuntu-latest" in workflow and "windows-latest" in workflow
    assert "matrix.os" in workflow
    assert "validate_wheelhouse_install.py" in workflow
    assert "pip wheel" in workflow
    for literal in (
        "--no-index", "--no-deps", "--require-hashes", "pip check",
        "wheel-manifest.txt", "PIP_NO_INDEX", "ORAEC_SOURCE_TREE",
        "smoke_installed_distribution.py", "PATH", "sha256",
        "Requires-Dist", "da7ff9618259f1669bdb89b134970399919accc0",
    ):
        assert literal in source, literal
    # A platform-specific venv/Scripts vs venv/bin layout must be resolved
    # by the helper, never hardcoded to POSIX inside the workflow.
    assert "offline-venv/bin" not in workflow
    assert "source-built-wheelhouse" in workflow


def test_installed_distribution_rejects_git_on_smoke_path() -> None:
    source = (
        ROOT / "scripts" / "smoke_installed_distribution.py"
    ).read_text(encoding="utf-8")
    assert 'shutil.which("git")' in source
    assert "ORAEC_SOURCE_TREE" in source


def _synthetic_wheel(
    root: Path, distribution: str, *, requirement: str = "",
) -> Path:
    normalized = distribution.replace("-", "_")
    file = root / f"{normalized}-0.1.0.dev0-py3-none-any.whl"
    meta = f"Metadata-Version: 2.1\\nName: {distribution}\\nVersion: 0.1.0.dev0\\n"
    if requirement:
        meta += f"Requires-Dist: {requirement}\\n"
    with zipfile.ZipFile(file, "w") as archive:
        archive.writestr(f"{normalized}-0.1.0.dev0.dist-info/METADATA", meta)
    return file


def test_portable_manifest_binds_real_wheel_bytes_and_pinned_vcs_metadata(
    tmp_path: Path,
) -> None:
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()
    sha = "da7ff9618259f1669bdb89b134970399919accc0"
    oraec = _synthetic_wheel(
        wheelhouse, "oraec-tf",
        requirement=f"tf-build @ git+https://github.com/alexsosn/tf-build.git@{sha}",
    )
    _synthetic_wheel(wheelhouse, "tf-build")
    lock = tmp_path / "manifest.txt"
    recorded = write_hash_manifest(wheelhouse, lock)
    lines = lock.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert all(line.startswith("file://") and "--hash=sha256:" in line for line in lines)
    assert recorded[oraec.name] == hashlib.sha256(oraec.read_bytes()).hexdigest()
    assert f"--hash=sha256:{recorded[oraec.name]}" in lock.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "requirement",
    [
        "",
        "tf-build>=0.1",
        "tf-build @ git+https://github.com/alexsosn/tf-build.git@" + "0" * 40,
    ],
)
def test_portable_manifest_refuses_missing_or_mutable_tf_build_pin(
    tmp_path: Path, requirement: str,
) -> None:
    wheels = tmp_path / "wheels"
    wheels.mkdir()
    _synthetic_wheel(wheels, "oraec-tf", requirement=requirement)
    _synthetic_wheel(wheels, "tf-build")
    with pytest.raises(ValueError, match="pin"):
        write_hash_manifest(wheels, tmp_path / "manifest.txt")
    assert not (tmp_path / "manifest.txt").exists()
