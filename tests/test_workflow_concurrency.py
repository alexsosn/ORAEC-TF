from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
GROUP = (
    "group: ${{ github.workflow }}-"
    "${{ github.event.pull_request.number || github.ref }}"
)


def _pull_request_workflows() -> list[Path]:
    return sorted(
        path
        for path in WORKFLOWS.glob("*.yml")
        if "pull_request:" in path.read_text(encoding="utf-8")
    )


def test_every_pull_request_workflow_cancels_superseded_heads() -> None:
    workflows = _pull_request_workflows()

    assert {path.name for path in workflows} == {
        "ci.yml",
        "linecount-research.yml",
        "schema-preflight.yml",
        "source-audit.yml",
    }

    for path in workflows:
        text = path.read_text(encoding="utf-8")
        assert "\nconcurrency:\n" in text, path.name
        assert GROUP in text, path.name
        assert "cancel-in-progress: true" in text, path.name


def test_concurrency_is_top_level_before_jobs() -> None:
    for path in _pull_request_workflows():
        text = path.read_text(encoding="utf-8")
        assert text.index("\nconcurrency:\n") < text.index("\njobs:\n"), path.name
