"""Issue #102: release rehearsal must follow the installed-wheel researcher path."""

from __future__ import annotations

import inspect
import subprocess
import sys
from pathlib import Path
from runpy import run_path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "release-rehearsal.yml"


def test_advanced_app_accepts_explicit_installed_app_directory() -> None:
    verifier = run_path(str(ROOT / "scripts" / "validate_advanced_app.py"))
    signature = inspect.signature(verifier["verify_local_advanced_app"])
    assert "app_dir" in signature.parameters
    help_result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate_advanced_app.py"), "--help"],
        capture_output=True, text=True, check=True,
    )
    assert "--app-dir" in help_result.stdout


def test_release_rehearsal_follows_isolated_real_researcher_journey() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    for command in (
        "workflow_dispatch:",
        "requirements/tf-build.txt",
        "requirements/runtime.lock",
        "validate_wheelhouse_install.py",
        "audit_software_release.py",
        "offline-venv",
        "oraec-tf",
        "fetch",
        "verify-source",
        "convert",
        "b83a0ee5fae27a40d4c0a2a9a8c9c2973d45e9cd",
        "validate_graph_source.py",
        "validate_advanced_app.py",
        "--app-dir",
        "app-path",
        "13026",
        "101796",
        "815026",
        "815029",
    ):
        assert command in text, command
    assert "pip install -e" not in text
    assert "python -I" in text
    assert "PYTHONPATH" in text
    assert "reports/generated/tf" not in text


def test_release_rehearsal_artifacts_are_source_free() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "upload-artifact" in text
    upload = text.split("uses: actions/upload-artifact@v4", 1)[1]
    assert "source" not in upload.lower().split("if-no-files-found", 1)[0] or (
        "source-free" in upload.lower()
    )
    for unsafe in ("*.tf", "*.tsv", "*.cfr", "*.tfx", "oraec*.json", "upstream/"):
        assert unsafe not in upload
    assert "rehearsal-summary.json" in upload
    assert "graph-conservation.json" in upload
