"""Workflow invariants: costly source validation is mandatory on ready PRs.

Issue #38: RED-first contract checks. Only full-snapshot CI is deferred on
draft PRs; unit tests remain on every pushed commit.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml  # type: ignore[import-untyped]

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("workflow_name", ["writer-validation.yml"])
def test_pinned_source_gates_run_on_exact_ready_head_and_manual_dispatch(
    workflow_name: str,
) -> None:
    file = ROOT / ".github" / "workflows" / workflow_name
    config = yaml.safe_load(file.read_text(encoding="utf-8"))
    # PyYAML YAML 1.1 may parse the GitHub Actions 'on' key as True.
    events = config.get("on", config.get(True))
    assert isinstance(events, dict)
    assert "workflow_dispatch" in events
    pull_request = events["pull_request"]
    assert set(pull_request["types"]) >= {
        "opened", "reopened", "synchronize", "ready_for_review",
    }
    jobs = config["jobs"]
    assert jobs
    for job in jobs.values():
        guard = job.get("if", "")
        assert "github.event_name" in guard
        assert "workflow_dispatch" in guard
        assert "github.event.pull_request.draft" in guard
        assert "false" in guard
        # Preserve actual full-snapshot operations, rather than skipping the
        # semantic audit itself to make a check superficially green.
        assert "runs-on" in job


def test_unit_ci_remains_unconditional_for_draft_prs() -> None:
    ci = yaml.safe_load(
        (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    )
    assert "draft" not in str(ci["jobs"]["test"].get("if", ""))
    steps = ci["jobs"]["test"]["steps"]
    assert {"Ruff", "Mypy", "Pytest"} <= {step.get("name") for step in steps}
