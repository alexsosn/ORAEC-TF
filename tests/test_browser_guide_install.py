"""Browser clone instructions must agree with the working dependency install (#117)."""

from __future__ import annotations

import shlex
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs/app-browser.md"
CLONE_HEADING = "## Rebuild and browse from a software clone\n"


def _clone_install_command() -> list[str]:
    guide = GUIDE.read_text(encoding="utf-8")
    assert guide.count(CLONE_HEADING) == 1
    clone_section = guide.split(CLONE_HEADING, 1)[1]
    bash_example = clone_section.split("```bash\n", 1)[1].split("\n```", 1)[0]
    install_lines = [
        line.strip()
        for line in bash_example.splitlines()
        if line.strip().startswith("python -m pip install ")
    ]
    assert len(install_lines) == 1
    return shlex.split(install_lines[0])


def test_browser_clone_install_uses_actual_hash_pinned_dependency() -> None:
    """Do not accidentally imply the tf-build prerelease is on PyPI."""
    assert _clone_install_command() == [
        "python", "-m", "pip", "install", "-r", "requirements/tf-build.txt",
        "-e", ".[dev]",
    ]
    ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "python -m pip install -r requirements/tf-build.txt -e '.[dev]'" in ci
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "tf-build==0.1.0rc1" in project
    requirement = (ROOT / "requirements/tf-build.txt").read_text(encoding="utf-8")
    assert "tf_build-0.1.0rc1-py3-none-any.whl#sha256=" in requirement


def test_browser_guide_has_no_resolved_packaging_blocker() -> None:
    guide = GUIDE.read_text(encoding="utf-8")
    assert "blocked under #59" not in guide
    assert "installed-distribution.md" in guide
    assert "0.1.0rc1" in guide
    assert "unpublished" in guide.lower()
