"""RED: independent wheelhouse install must exercise the *installed* package.

An editable-checkout pytest pass does not prove that the oraec-tf wheel has
all its modules, scripts, schema resources, or compatible pinned dependencies.
"""

from __future__ import annotations

import ast
from pathlib import Path

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
    for required in (
        "pip wheel",
        "--no-index",
        "--no-deps",
        "pip check",
        "smoke_installed_distribution.py",
        "sha256",
        "ORAEC_SOURCE_TREE",
    ):
        assert required in workflow
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
