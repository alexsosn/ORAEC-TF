"""Guard the documented release-operator route against a fake prerelease claim.

This tests the public operator contract without creating tags or running GH CLI.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs" / "software-release-runbook.md"


def test_release_runbook_covers_exact_head_gates() -> None:
    guide = GUIDE.read_text(encoding="utf-8")
    for required in (
        "v0.1.0rc1",
        "main",
        "git rev-parse",
        "gh workflow run",
        "gh run view",
        "ci.yml",
        "writer-validation.yml",
        "release-rehearsal.yml",
        "agora-materializer.yml",
        "software-release.yml",
        "workflow_dispatch",
        "SHA",
        "git tag",
        "git push",
        "--ref main",
        "-f tag=v0.1.0rc1",
    ):
        assert required in guide, f"missing operator prerequisite: {required}"
    assert "gh release create" not in guide, "publication must use verified workflow"


def test_release_runbook_has_software_only_consumer_checks() -> None:
    guide = GUIDE.read_text(encoding="utf-8")
    for required in (
        "oraec_tf-0.1.0rc1-py3-none-any.whl",
        "oraec_tf-0.1.0rc1.tar.gz",
        "release-manifest.json",
        "verify_release_assets.py",
        "--verify-staged",
        "sha256",
        "#106",
        "#12",
        "no ORAEC source",
        "not",
    ):
        assert required in guide, f"missing release boundary: {required}"
    assert "CITATION.cff" in guide


def test_public_readme_links_release_runbook_without_claiming_a_release() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "[software release operator runbook](docs/software-release-runbook.md)" in readme
    assert "Unpublished software release candidate" in readme


def test_tag_probe_must_not_silence_remote_authentication_failure() -> None:
    guide = GUIDE.read_text(encoding="utf-8")
    assert "git ls-remote --refs origin refs/tags/v0.1.0rc1" in guide
    assert "|| true" not in guide, "tag probe errors must abort instead of passing"
    assert 'test -z "$remote_tag"' in guide


def test_failed_publication_retry_preserves_existing_tag_and_sha() -> None:
    guide = GUIDE.read_text(encoding="utf-8")
    assert "## Recovery: failed publication with an existing tag" in guide
    assert 'refs/tags/v0.1.0rc1^{commit}' in guide
    assert 'gh release view v0.1.0rc1' in guide
    assert "Never move or recreate the tag" in guide
    assert "gh workflow run software-release.yml --ref main -f tag=v0.1.0rc1" in guide
