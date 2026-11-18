"""Regression gate for exercising supported Python on actual ORAEC workflows.

The job results, rather than this source-text check, establish compatibility.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_ci_exercises_supported_python_314() -> None:
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    matrix = re.search(r'python-version:\s*\[([^\]]+)\]', ci)
    assert matrix, "existing CI Python-version matrix missing"
    versions = set(re.findall(r'["\'](3\.\d+)["\']', matrix.group(1)))
    assert {"3.11", "3.12", "3.13", "3.14"} <= versions


def test_full_native_source_audit_runs_on_python_314_without_extra_matrix() -> None:
    workflow = (ROOT / ".github" / "workflows" / "writer-validation.yml").read_text(
        encoding="utf-8"
    )
    assert re.search(r'python-version:\s*["\']3\.14["\']', workflow)
    assert workflow.count("Convert complete source and independently reload TF") == 1
    assert "Independently audit raw source against generated TF" in workflow
    assert "Smoke local standard Text-Fabric advanced app and browser" in workflow
