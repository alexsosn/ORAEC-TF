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
