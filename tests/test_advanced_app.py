"""RED-first advanced Text-Fabric app smoke tests for #9.

All corpus data here are synthesized; source data are not checked into Git.
The real tf.advanced.app.App is exercised with an already loaded local TF API.
"""

from __future__ import annotations

from pathlib import Path

from tf.advanced.app import App
from tf.advanced.find import findAppConfig
from tf.fabric import Fabric

from oraec_tf.ir import CreditsIR, SentenceIR, TextIR, TokenIR
from oraec_tf.writer import write_tf

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "app"
REVISION = "b83a0ee5fae27a40d4c0a2a9a8c9c2973d45e9cd"


def _tiny_corpus(destination: Path) -> None:
    text = TextIR(
        oraec_id="oraec42",
        title="Unicode preservation",
        credits=CreditsIR(
            license="cc-by-sa-4.0",
            author="Editor",
            sources=("https://example.invalid/source",),
        ),
        sentences=(
            SentenceIR(
                index=1,
                translation="translated",
                tokens=(
                    TokenIR(
                        token_id="oraec42-1-1",
                        written_form="nṯr",
                        hiero="𓀀[⯑]�",
                        pos="substantive",
                        line_count="[Vs 1]",
                    ),
                    TokenIR(
                        token_id="oraec42-1-2",
                        written_form="ḫpr",
                        # Source does not provide a hieroglyphic form.
                    ),
                ),
            ),
            SentenceIR(index=2, translation="", tokens=()),
        ),
    )
    write_tf((text,), destination, source_revision=REVISION)


def test_frozen_tf_graph_supports_all_documented_builtin_text_formats(
    tmp_path: Path,
) -> None:
    output = tmp_path / "tf"
    _tiny_corpus(output)
    api = Fabric(locations=str(output), silent="deep").load(
        "written_form hiero trailer token_id is_anchor oraec_id sentence_index",
        silent="deep",
    )
    assert api
    sentence = api.F.otype.s("sentence")[0]
    original = api.T.text(sentence, fmt="text-orig-full")
    assert "nṯr" in original
    assert "ḫpr" in original
    assert api.T.text(sentence, fmt="text-translit") == original
    hiero = api.T.text(sentence, fmt="text-hiero")
    assert "𓀀[⯑]�" in hiero
    assert "ḫpr" not in hiero
    assert api.T.sectionFromNode(sentence) == ("oraec42", 1)
    assert api.T.nodeFromSection(("oraec42", 2)) in api.F.otype.s("sentence")


def test_advanced_app_loads_local_generated_graph_and_renders_both_scripts(
    tmp_path: Path,
) -> None:
    output = tmp_path / "tf"
    _tiny_corpus(output)
    api = Fabric(locations=str(output), silent="deep").loadAll(silent="deep")
    assert api
    assert (APP_DIR / "config.yaml").is_file()
    cfg = findAppConfig(
        "ORAEC-TF",
        str(APP_DIR),
        commit="local",
        release="",
        local="clone",
        backend="github",
        org="alexsosn",
        repo="ORAEC-TF",
    )
    app = App(
        cfg,
        "ORAEC-TF",
        str(APP_DIR),
        commit="local",
        release="",
        local="clone",
        backend="github",
        _browse=False,
        api=api,
        silent="deep",
    )
    assert app.api
    first_sentence = api.F.otype.s("sentence")[0]
    html = app.pretty(first_sentence, _asString=True)
    assert isinstance(html, str)
    assert "nṯr" in html
    assert "𓀀" not in html  # Default is transliteration.
    as_hiero = app.pretty(first_sentence, _asString=True, fmt="text-hiero")
    assert "𓀀" in as_hiero
    assert "𓀀[⯑]�" in as_hiero
    assert "ḫpr" not in as_hiero
    empty_sentence = api.F.otype.s("sentence")[1]
    # No accidental empty technical anchor glyph or invented source token.
    empty_html = app.pretty(empty_sentence, _asString=True)
    assert "is_anchor" not in empty_html


def test_app_provenance_never_claims_bundled_corpus_files() -> None:
    cfg = findAppConfig(
        "ORAEC-TF",
        str(APP_DIR),
        commit="local",
        release="",
        local="clone",
        backend="github",
        straight=True,
    )
    assert cfg["apiVersion"] == 3
    assert cfg["dataDisplay"]["textFormat"] == "text-translit"
    assert cfg["typeDisplay"]["word"]["exclude"] == {"is_anchor": 1}
    assert cfg["provenanceSpec"]["org"] == "alexsosn"
    assert cfg["provenanceSpec"]["repo"] == "ORAEC-TF"
    assert "webBase" not in cfg["provenanceSpec"]
