"""Issue #62: landing-page truthfulness is a release/documentation contract."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_readme_describes_implemented_schema_and_real_release_boundaries() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    obsolete = (
        "research and converter bootstrap",
        "being audited in issue #2",
        "will be completed after the native TF schema is frozen in issue #3",
        "materializer contract is tracked in issue #11",
    )
    for phrase in obsolete:
        assert phrase not in readme
    for claim in (
        "schema v3", "2,930", "13,026", "815,026",
        "0.1.0.dev0", "no released TF corpus", "NativeCRIndex",
        "CC BY-SA", "Karnak", "network",
    ):
        assert claim.casefold() in readme.casefold(), claim
    for destination in (
        "docs/feature-reference.md",
        "docs/query-recipes.md",
        "docs/app-browser.md",
        "docs/agora.md",
        "docs/installed-distribution.md",
        "docs/adr/0007-native-carriage-return-occurrences.md",
    ):
        assert f"]({destination})" in readme, destination
        assert (ROOT / destination).is_file(), destination


def test_readme_never_claims_unreleased_or_network_free_cold_install() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "tf-build #60" in readme
    assert "ORAEC-TF issue #59" in readme
    assert "Agora #224" in readme
    assert "no publicly released" in readme.casefold()
    assert "wheelhouse" in readme
