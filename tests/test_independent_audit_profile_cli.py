"""#74 RED: independent audit timing is opt-in and separate from conservation."""

from __future__ import annotations

import json
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any

import pytest

# The installed package exposes src/, not the repository's CLI script directory.
# Load the exact real script by path without depending on a pytest sys.path alias.
_SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "validate_graph_source.py"
_SCRIPT_SPEC = spec_from_file_location("oraec_graph_audit_cli_under_test", _SCRIPT_PATH)
assert _SCRIPT_SPEC is not None and _SCRIPT_SPEC.loader is not None
audit_cli = module_from_spec(_SCRIPT_SPEC)
_SCRIPT_SPEC.loader.exec_module(audit_cli)


def test_audit_cli_optional_profile_keeps_canonical_report_identical(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_marker = "SECRET SOURCE TEXT MAY NOT APPEAR IN PROFILE"
    expected = {
        "ok": True,
        "counts": {"texts": 1, "sentences": 2, "tokens": 1, "anchors": 1},
        "native_cr_occurrences": {"total": 0},
        "output_semantic_sha256": {"otype.tf": "a" * 64},
        "raw_source_test_marker": raw_marker,
    }
    recorder_states: list[bool] = []

    def fake_audit(*args: Any, **kwargs: Any) -> dict[str, Any]:
        recorder = kwargs.get("profile_recorder")
        recorder_states.append(recorder is not None and recorder.enabled)
        if recorder is not None:
            with recorder.phase("source_graph_audit"):
                with recorder.phase("independent_fabric_load"):
                    with recorder.phase("independent_fabric_warp_load"):
                        with recorder.phase("independent_fabric_warp_precompute"):
                            with recorder.phase("independent_fabric_compute_levels"):
                                pass
                        with recorder.phase("independent_fabric_warp_api"):
                            pass
                    with recorder.phase("independent_fabric_features_load"):
                        pass
            with recorder.phase("feature_hashes"):
                pass
        return expected

    monkeypatch.setattr(audit_cli, "audit_graph_with_provenance", fake_audit)
    input_args = [
        "validate_graph_source.py", str(tmp_path), str(tmp_path / "tf"),
        "--source-revision", "a" * 40,
        "--converter-revision", "b" * 40,
        "--schema-version", "3",
    ]
    normal = tmp_path / "plain.json"
    monkeypatch.setattr(sys, "argv", input_args + ["--report", str(normal)])
    assert audit_cli.main() == 0
    profiled = tmp_path / "profiled.json"
    timing = tmp_path / "timing.json"
    monkeypatch.setattr(
        sys, "argv",
        input_args + ["--report", str(profiled), "--profile-report", str(timing)],
    )
    assert audit_cli.main() == 0
    assert normal.read_bytes() == profiled.read_bytes()
    assert recorder_states == [False, True]
    assert not (tmp_path / "plain-profile.json").exists()
    payload = json.loads(timing.read_text(encoding="utf-8"))
    assert payload["format"] == "oraec-independent-audit-profile-v1"
    assert [phase["name"] for phase in payload["phases"]] == [
        "independent_fabric_compute_levels",
        "independent_fabric_warp_precompute",
        "independent_fabric_warp_api",
        "independent_fabric_warp_load",
        "independent_fabric_features_load",
        "independent_fabric_load", "source_graph_audit", "feature_hashes",
    ]
    assert payload["environment"]["text_fabric_version"]
    assert payload["total_wall_seconds"] >= 0
    assert raw_marker not in json.dumps(payload)
    assert str(tmp_path) not in json.dumps(payload)
    assert "output_semantic_sha256" not in payload
