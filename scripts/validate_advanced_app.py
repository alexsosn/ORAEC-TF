"""Smoke-test the standard ORAEC advanced app using an existing local TF graph.

This program NEVER fetches source or corpus data. It runs on the same
ephemeral TF directory produced by oraec-tf convert. No browser server needed.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from tf.advanced.app import App
from tf.advanced.find import findAppConfig
from tf.fabric import Fabric

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "app"


def verify_local_advanced_app(tf_dir: Path) -> dict[str, object]:
    if not tf_dir.is_dir():
        raise ValueError(f"missing local TF output: {tf_dir}")
    if not (tf_dir / "otype.tf").is_file():
        raise ValueError("generated TF warp missing: otype.tf")

    api = Fabric(locations=str(tf_dir), silent="deep").loadAll(silent="deep")
    if not api:
        raise ValueError("generated TF cannot load in Fabric")

    cfg = findAppConfig(
        "ORAEC-TF", str(APP_DIR),
        commit="local", release="", local="clone", backend="github",
        org="alexsosn", repo="ORAEC-TF",
    )
    app = App(
        cfg, "ORAEC-TF", str(APP_DIR),
        commit="local", release="", local="clone", backend="github",
        _browse=False, api=api, silent="deep",
    )
    if not app.api:
        raise ValueError("standard Text-Fabric App failed with local Fabric API")

    texts = api.F.otype.s("text")
    if not texts:
        raise ValueError("no native ORAEC text nodes")
    text_node = texts[0]
    sentence_nodes = api.L.d(text_node, otype="sentence")
    if not sentence_nodes:
        raise ValueError("first text has no sentences")
    sentence = sentence_nodes[0]
    text_id = api.F.oraec_id.v(text_node)
    if api.T.sectionFromNode(sentence)[0] != text_id:
        raise ValueError("advanced section navigation disagrees with text identity")
    for fmt in ("text-orig-full", "text-translit", "text-hiero"):
        rendered = api.T.text(sentence, fmt=fmt)
        if not isinstance(rendered, str):
            raise ValueError(f"Text-Fabric format {fmt} did not render a string")

    translit = app.pretty(sentence, _asString=True)
    hiero = app.pretty(sentence, _asString=True, fmt="text-hiero")
    if not isinstance(translit, str) or not isinstance(hiero, str):
        raise ValueError("Text-Fabric advanced app failed to render sentence HTML")

    # Exercise the *real* TF 13.1 Flask handlers without binding a public port.
    # Rendering App.pretty() alone does not prove that a researcher can use the
    # browser homepage, search API, or passage/navigation forms.
    from tf.browser.kernel import makeTfKernel
    from tf.browser.web import Web, factory

    # The existing app is notebook/Python-facing (_browse=False).
    # The real web header intentionally returns None outside browser mode.
    # Instantiate the same standard app in _browse=True mode, with the same
    # already loaded and independently verified TF API, not a mocked handler.
    browser_app = App(
        cfg, "ORAEC-TF", str(APP_DIR),
        commit="local", release="", local="clone", backend="github",
        _browse=True, api=api, silent="deep",
    )
    if not browser_app.api:
        raise ValueError("Text-Fabric browser App failed to initialize")
    kernel = makeTfKernel(browser_app, "ORAEC-TF")
    if not kernel:
        raise ValueError("Text-Fabric browser kernel initialization failed")
    webapp = factory(Web(kernel))
    webapp.testing = True
    query = f"text oraec_id={text_id}"
    with webapp.test_client() as client:
        home = client.get("/")
        if home.status_code != 200 or b"<html" not in home.data.lower():
            raise ValueError(
                f"Text-Fabric browser homepage HTTP failed: {home.status_code}"
            )
        result = client.post("/query", data={"query": query, "jobName": "oraec-smoke"})
        reply = result.get_json(silent=True)
        if (
            result.status_code != 200
            or not isinstance(reply, dict)
            or reply.get("status") is not True
            or not isinstance(reply.get("nResults"), int)
            or reply["nResults"] != 1
        ):
            raise ValueError(
                f"Text-Fabric browser query HTTP failed: "
                f"status={result.status_code}; "
                f"result={None if not isinstance(reply, dict) else reply.get('nResults')}"
            )
        passage = client.post(
            "/passage", data={"sec0": text_id, "jobName": "oraec-smoke"}
        )
        passage_reply = passage.get_json(silent=True)
        if (
            passage.status_code != 200
            or not isinstance(passage_reply, dict)
            or "table" not in passage_reply
        ):
            raise ValueError(
                f"Text-Fabric browser passage HTTP failed: {passage.status_code}"
            )
    browser_http = {
        "home_status": home.status_code,
        "query_status": result.status_code,
        "query_success": True,
        "query_results": reply["nResults"],
        "passage_status": passage.status_code,
        "text_id": text_id,
    }
    return {
        "ok": True,
        "app": "standard Text-Fabric advanced app",
        "text_id": text_id,
        "text_count": len(texts),
        "sentence_count": len(api.F.otype.s("sentence")),
        "formats": ["text-orig-full", "text-translit", "text-hiero"],
        "browser_http": browser_http,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("tf_dir", type=Path)
    args = parser.parse_args()
    import json

    print(json.dumps(verify_local_advanced_app(args.tf_dir), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
