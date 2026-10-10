"""RED-first standalone Agora materializer contract (#11)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from oraec_tf.source import DEFAULT_SOURCE_REVISION

ROOT = Path(__file__).resolve().parents[1]


def test_manifest_declares_pinned_offline_native_tf_materializer() -> None:
    manifest = json.loads(
        (ROOT / "agora.materializer.json").read_text(encoding="utf-8")
    )
    assert manifest["schema_version"] == 1
    assert manifest["plugin"]["id"] == "oraec-tf"
    assert len(manifest["materializers"]) == 1
    materializer = manifest["materializers"][0]
    sources = [
        item for item in materializer["acquisition"] if item["type"] == "git"
    ]
    assert len(sources) == 1
    assert sources[0]["url"] == "https://github.com/oraec/corpus_raw_data.git"
    assert sources[0]["ref"] == DEFAULT_SOURCE_REVISION
    assert materializer["input"]["type"] == "directory"
    assert materializer["input"]["allow_symlinks"] is False
    assert materializer["execution"]["type"] == "python-module"
    assert materializer["execution"]["module"] == "oraec_tf.agora"
    assert materializer["execution"]["network"] == "deny"
    assert materializer["execution"]["args"] == [
        "{source}", "{output}", "--source-revision", "{source_revision}"
    ]
    assert set(materializer["output"]["required_paths"]) >= {
        "tf/otype.tf", "tf/oslots.tf", "tf/otext.tf", "conversion-summary.json"
    }


def test_adapter_delegates_to_public_cli_without_fetching(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    from oraec_tf import agora
    from oraec_tf import cli

    called: list[list[str]] = []

    def fake_main(argv: list[str]) -> int:
        called.append(argv)
        assert argv[0] == "convert"
        assert argv[1] == str(tmp_path / "verified-source")
        assert argv[2] == "--output"
        assert argv[4:] == ["--upstream-commit", DEFAULT_SOURCE_REVISION]
        tf_dir = Path(argv[3])
        tf_dir.mkdir()
        for name in ("otype.tf", "oslots.tf", "otext.tf"):
            (tf_dir / name).write_text(f"@demo\n{name}\n", encoding="utf-8")
        print(json.dumps({
            "output": str(tf_dir),
            "revision": DEFAULT_SOURCE_REVISION,
            "counts": {"texts": 1, "sentences": 1, "tokens": 1,
                       "technical_anchors": 0, "slots": 1},
        }))
        return 0

    monkeypatch.setattr(cli, "main", fake_main)
    source = tmp_path / "verified-source"
    destination = tmp_path / "published"
    assert agora.main([
        str(source), str(destination),
        "--source-revision", DEFAULT_SOURCE_REVISION,
    ]) == 0
    assert len(called) == 1
    assert destination.joinpath("tf/otype.tf").is_file()
    report = json.loads(
        destination.joinpath("conversion-summary.json").read_text(encoding="utf-8")
    )
    assert report["source_revision"] == DEFAULT_SOURCE_REVISION
    assert report["counts"]["texts"] == 1
    assert "source" not in str(report).lower() or report["source_revision"]
    assert not destination.joinpath("verified-source").exists()


def test_adapter_rejects_mutable_or_unapproved_source_revision(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    from oraec_tf import agora
    from oraec_tf import cli

    def should_not_run(argv: list[str]) -> int:
        raise AssertionError("conversion was invoked for an invalid revision")

    monkeypatch.setattr(cli, "main", should_not_run)
    for revision in ("main", "b83a0ee", "0" * 40):
        with pytest.raises(ValueError, match="revision"):
            agora.materialize(
                tmp_path / "source", tmp_path / "output",
                source_revision=revision,
            )
    assert not (tmp_path / "output").exists()


def test_adapter_failure_does_not_publish_partial_output(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    from oraec_tf import agora
    from oraec_tf import cli

    def fail_after_partial_output(argv: list[str]) -> int:
        tf_dir = Path(argv[3])
        tf_dir.mkdir()
        (tf_dir / "otype.tf").write_text("partial", encoding="utf-8")
        raise ValueError("deliberate writer failure")

    monkeypatch.setattr(cli, "main", fail_after_partial_output)
    with pytest.raises(ValueError, match="deliberate"):
        agora.materialize(
            tmp_path / "source", tmp_path / "output",
            source_revision=DEFAULT_SOURCE_REVISION,
        )
    assert not (tmp_path / "output").exists()
