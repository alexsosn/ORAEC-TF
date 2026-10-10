from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
GROUP = (
    "group: ${{ github.workflow }}-${{ github.event_name }}-"
    "${{ github.event_name == 'workflow_dispatch' && github.run_id || "
    "github.event.pull_request.number || github.ref }}"
)


def _pull_request_workflows(root: Path = WORKFLOWS) -> list[Path]:
    return sorted(
        path
        for path in root.iterdir()
        if path.is_file()
        and path.suffix in {".yml", ".yaml"}
        and "pull_request:" in path.read_text(encoding="utf-8")
    )


def test_every_pull_request_workflow_cancels_superseded_heads() -> None:
    workflows = _pull_request_workflows()

    # Discover all PR workflows instead of freezing the current file list.
    # Future workflows must inherit the same concurrency policy.
    assert workflows, "no pull-request workflows found"

    for path in workflows:
        text = path.read_text(encoding="utf-8")
        assert "\nconcurrency:\n" in text, path.name
        assert GROUP in text, path.name
        assert "cancel-in-progress: true" in text, path.name


def test_concurrency_is_top_level_before_jobs() -> None:
    for path in _pull_request_workflows():
        text = path.read_text(encoding="utf-8")
        assert text.index("\nconcurrency:\n") < text.index("\njobs:\n"), path.name


def test_manual_runs_are_isolated_from_push_runs_and_each_other() -> None:
    # Event type prevents push/dispatch collisions. Unique run_id prevents
    # independently requested manual dispatches on the same branch colliding.
    for path in _pull_request_workflows():
        text = path.read_text(encoding="utf-8")
        assert GROUP in text, path.name
        assert "github.event_name" in text, path.name
        assert "github.run_id" in text, path.name


def test_yaml_suffix_pull_request_workflows_are_discovered(tmp_path: Path) -> None:
    yaml_path = tmp_path / "additional-validation.yaml"
    yaml_path.write_text("on:\n  pull_request:\n", encoding="utf-8")
    assert _pull_request_workflows(tmp_path) == [yaml_path]
