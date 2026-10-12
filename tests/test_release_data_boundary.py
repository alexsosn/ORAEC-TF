"""Software-only release and Karnak corpus-distribution boundary (#12/#17/#85)."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_release_policy_does_not_require_karnak_data_redistribution_licence() -> None:
    readme = _text("README.md")
    scope = _text("LICENSE_SCOPE.md")
    agent = _text("AGENTS.md")

    assert "software-only release" in readme.lower()
    assert "Karnak licence clarification does not block" in readme
    assert "does not block the software-only v0.1.0 release" in scope
    assert "generated corpora" in scope
    assert "not a software-release blocker" in agent


def test_current_converter_exclusion_is_not_misrepresented_as_local_support() -> None:
    readme = _text("README.md")
    scope = _text("LICENSE_SCOPE.md")
    adr = _text("docs/adr/0005-native-tf-schema.md")
    schema = json.loads(_text("schema/core.json"))

    assert "#85" in readme and "--include-karnak" in readme
    assert "#85" in scope and "--include-karnak" in scope
    assert "#85" in adr and "current default" in adr
    assert "--include-karnak" in adr
    assert set(schema["release"]["excludedMappings"]) == {
        "mapping_oraec_karnak.tsv",
        "mapping_oraec_lemmata_karnak.tsv",
    }


def test_agora_hosted_karnak_artifacts_have_separate_rights_review() -> None:
    docs = _text("docs/agora.md")
    scope = _text("LICENSE_SCOPE.md")

    assert "Agora #224" in docs
    assert "remote execution" in docs
    assert "Karnak-bearing" in docs
    assert "rights review" in docs
    assert "Karnak mapping redistribution terms: unresolved" in scope


def test_researcher_docs_and_roadmap_distinguish_current_exclusion_from_rights() -> None:
    feature_ref = _text("docs/feature-reference.md")
    recipes = _text("docs/query-recipes.md")
    plan = _text("plan.md")
    research = _text("research.md")

    assert "currently excludes the Karnak" in feature_ref
    assert "#85" in recipes and "currently excludes" in recipes
    assert "#85" in plan and "separate from software release #12" in plan
    assert "2026-10-12 release-boundary clarification" in research
    assert "Karnak mappings remain excluded by the #17 fail-closed licence gate" not in research
