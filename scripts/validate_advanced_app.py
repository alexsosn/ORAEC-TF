"""Smoke-test the standard ORAEC advanced app using an existing local TF graph.

This program NEVER fetches source or corpus data. It runs on the same
ephemeral TF directory produced by oraec-tf convert. The opt-in graphical
browser smoke serves that same in-memory graph on loopback only.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from flask import Flask
from tf.advanced.app import App
from tf.advanced.find import findAppConfig
from tf.fabric import Fabric

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "app"



def _run_graphical_browser_smoke(
    webapp: Flask, *, text_id: str, glyph: str,
) -> dict[str, object]:
    """Drive TF's actual JavaScript UI on loopback; never report source strings.

    This optional test dependency is deliberately absent from the ORAEC wheel.
    No screenshots, HTML, raw source or generated corpus are persisted.
    """
    from importlib import import_module
    from threading import Thread

    from werkzeug.serving import make_server

    try:
        sync_playwright = import_module("playwright.sync_api").sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "graphical browser smoke requires optional Playwright and its Chromium browser"
        ) from exc

    server = make_server("127.0.0.1", 0, webapp, threaded=True)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                errors: list[str] = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(
                    f"http://127.0.0.1:{server.server_port}/",
                    wait_until="load", timeout=45000,
                )
                if "ORAEC-TF" not in page.title():
                    raise ValueError("graphical TF browser did not open the ORAEC app")

                # Real button click runs the upstream tf3.0.js Ajax /query
                # handler. Neither a direct HTTP client nor DOM injection counts.
                # Detect an upstream JS initialization failure *before*
                # waiting for an Ajax response that will never be issued.
                if errors:
                    raise ValueError(
                        f"Text-Fabric page initialization raised {len(errors)} "
                        f"uncaught JavaScript error(s): {errors[0][:220]}"
                    )
                page.locator("#query").fill(f"text oraec_id={text_id}")
                query_responses: list[int] = []
                page.on(
                    "response",
                    lambda response: query_responses.append(response.status)
                    if response.url.endswith("/query") else None,
                )
                page.locator("#queryGo").click()
                try:
                    page.wait_for_function(
                        'document.querySelector("#nresults .nresults")'
                        '?.textContent?.trim() === "1"',
                        timeout=12000,
                    )
                except Exception as exc:
                    raise ValueError(
                        "real browser query failed: "
                        f"query_http_statuses={query_responses}, "
                        f"uncaught_js_errors={len(errors)}, "
                        f"mode={page.locator('#mode').input_value()}, "
                        f"result_count={page.locator('#nresults .nresults').inner_text()!r}"
                    ) from exc
                if not page.locator("#queryTable").inner_text().strip():
                    raise ValueError("real browser did not render its one query result")

                # ORAEC deliberately has no fabricated external webBase,
                # so result references need not be clickable. Use TF's
                # real passage navigator: switch mode, filter the attested
                # text ID, and click its *exact* section link.
                from re import compile as regex_compile
                from re import escape as regex_escape

                page.locator("#modepassage").click()
                page.locator("#passages .s0nav").first.wait_for(timeout=45000)
                page.locator("#s0filter").fill(text_id)
                passage_link = page.locator("#passages .s0nav").filter(
                    has_text=regex_compile(f"^{regex_escape(text_id)}$")
                )
                if passage_link.count() != 1:
                    raise ValueError("passage navigator lacks exact source text ID")
                passage_link.click()
                page.wait_for_function(
                    '() => Boolean(document.querySelector("#passageTable")'
                    '?.innerText?.trim())',
                    timeout=45000,
                )
                if not page.locator("#passageTable").is_visible():
                    raise ValueError("passage navigation did not reveal passage text")
                if page.locator("#passageTable details.pretty").count() == 0:
                    raise ValueError(
                        "passage did not render sentence rows: "
                        "check browseContentPretty/browser section display"
                    )

                # TF 13.1.0 tf3.0.js::subLinks calls getTable(..., "passages"),
                # but switchMode only recognizes "passage" (singular). This
                # leaves the hidden mode invalid after clicking a section;
                # a subsequent text-format form reload may hide the passage.
                # Recover through the *visible researcher controls*, rather
                # than mutating the hidden input or patching third-party JS.
                mode_after_link = page.locator("#mode").input_value()
                if mode_after_link == "passages":
                    page.locator("#moderesults").click()
                    page.locator("#modepassage").click()
                if page.locator("#mode").input_value() != "passage":
                    raise ValueError("passage mode cannot be restored via browser controls")

                # Real controls from Text-Fabric v13.1.0: selecting the radio
                # triggers form submission and then reloads the Ajax passage.
                # Options live in a sidebar hidden until its actual tab is
                # clicked; do not force-click hidden controls.
                page.locator('#sidebar div[status="options"] a').click()
                page.locator("details#options summary").click()
                format_radio = page.locator('input[name="textFormat"][value="text-hiero"]')
                format_radio.check()
                try:
                    page.wait_for_function(
                        '(attested) => Boolean(document.querySelector("#passageTable")'
                        '?.innerText?.includes(attested))',
                        arg=glyph, timeout=15000,
                    )
                except Exception as exc:
                    passage = page.locator("#passageTable")
                    raise ValueError(
                        "real browser hieroglyph format failed: "
                        f"mode={page.locator('#mode').input_value()}, "
                        f"radio_checked={format_radio.is_checked()}, "
                        f"passage_visible={passage.is_visible()}, "
                        f"passage_dom_chars={len(passage.text_content() or '')}, "
                        f"passage_visible_chars={len(passage.inner_text())}, "
                        f"sentence_rows={page.locator('#passageTable details.pretty').count()}, "
                        f"sec0_matches_target={page.locator('#sec0').input_value() == text_id}, "
                        f"uncaught_js_errors={len(errors)}"
                    ) from exc
                if not page.locator("#passageTable").is_visible():
                    raise ValueError("hieroglyphic passage is not visible")
                if errors:
                    raise ValueError(
                        f"uncaught JavaScript errors in graphical browser: {len(errors)}"
                    )

                return {
                    "browser": "chromium",
                    "browser_version": browser.version,
                    "query_results": 1,
                    "passage_visible": True,
                    "text_format": "text-hiero",
                    "hiero_rendered": True,
                    "passage_mode_recovery_used": mode_after_link == "passages",
                    "uncaught_js_errors": 0,
                }
            finally:
                browser.close()
    finally:
        server.shutdown()
        worker.join(timeout=10)
        server.server_close()

def verify_local_advanced_app(
    tf_dir: Path, *, app_dir: Path | None = None, gui_browser: bool = False,
) -> dict[str, object]:
    if not tf_dir.is_dir():
        raise ValueError(f"missing local TF output: {tf_dir}")
    if not (tf_dir / "otype.tf").is_file():
        raise ValueError("generated TF warp missing: otype.tf")

    api = Fabric(locations=str(tf_dir), silent="deep").loadAll(silent="deep")
    if not api:
        raise ValueError("generated TF cannot load in Fabric")

    selected_app = APP_DIR if app_dir is None else app_dir
    cfg = findAppConfig(
        "ORAEC-TF", str(selected_app),
        commit="local", release="", local="clone", backend="github",
        org="alexsosn", repo="ORAEC-TF",
    )
    app = App(
        cfg, "ORAEC-TF", str(selected_app),
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
        cfg, "ORAEC-TF", str(selected_app),
        commit="local", release="", local="clone", backend="github",
        _browse=True, api=api, silent="deep",
    )
    if not browser_app.api:
        raise ValueError("Text-Fabric browser App failed to initialize")
    # Passing an already loaded Fabric API intentionally skips getModulesData(),
    # which normally initializes App.provenance to []. There is no independently
    # published TF dataset/module to cite: only this local generated graph.
    browser_app.provenance = []
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
        result = client.post(
            "/query",
            data={
                "query": query, "jobName": "oraec-smoke",
                # The browser's highlighting code requires a valid node type
                # even for its ordinary uncondensed query result.
                "condenseType": "text",
            },
        )
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
    summary: dict[str, object] = {
        "ok": True,
        "app": "standard Text-Fabric advanced app",
        "text_id": text_id,
        "text_count": len(texts),
        "sentence_count": len(api.F.otype.s("sentence")),
        "formats": ["text-orig-full", "text-translit", "text-hiero"],
        "browser_http": browser_http,
    }
    if gui_browser:
        # Choose only an actually attested Egyptian hieroglyph in the FIRST
        # sentence of a real text so a normal passage view must include it.
        # The target is derived from TF, not a guessed or copied corpus string.
        target: tuple[str, str] | None = None
        for word, source_hiero in api.F.hiero.items():
            if not isinstance(source_hiero, str):
                continue
            glyph = next(
                (c for c in source_hiero if "\U00013000" <= c <= "\U0001342F"),
                None,
            )
            if glyph is None:
                continue
            parents = api.L.u(word, otype="sentence")
            if not parents or api.F.sentence_index.v(parents[0]) != 1:
                continue
            text_parents = api.L.u(word, otype="text")
            if text_parents:
                attested_text_id = api.F.oraec_id.v(text_parents[0])
                if isinstance(attested_text_id, str):
                    # Source glyphs on excluded/technical words must not be
                    # expected in the visible browser passage. Verify the
                    # actual standard advanced renderer before choosing it.
                    if glyph not in browser_app.pretty(
                        parents[0], _asString=True, fmt="text-hiero"
                    ):
                        continue
                    target = (attested_text_id, glyph)
                    break
        if target is None:
            raise ValueError("no first-sentence source hieroglyph for browser smoke")
        # Establish an independent server-side baseline for the SAME
        # source-attested hieroglyph. The GUI must then prove that the
        # researcher controls expose this already renderable passage.
        with webapp.test_client() as client:
            response = client.post(
                "/passage",
                data={
                    "sec0": target[0],
                    "jobName": "oraec-smoke",
                    "textFormat": "text-hiero",
                },
            )
            passage = response.get_json(silent=True)
            if (
                response.status_code != 200
                or not isinstance(passage, dict)
                or not isinstance(passage.get("table"), str)
                or target[1] not in passage["table"]
            ):
                raise ValueError(
                    "standard TF passage endpoint fails to render attested "
                    "first-sentence hieroglyph in text-hiero"
                )
        summary["browser_gui"] = _run_graphical_browser_smoke(
            webapp, text_id=target[0], glyph=target[1],
        )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("tf_dir", type=Path)
    parser.add_argument(
        "--app-dir", type=Path, default=None,
        help="Explicit Text-Fabric app path, e.g. installed oraec-tf app-path",
    )
    parser.add_argument(
        "--gui-browser", action="store_true",
        help="Also drive actual Chromium JavaScript query, passage and hieroglyph UI",
    )
    args = parser.parse_args()
    import json

    print(json.dumps(
        verify_local_advanced_app(
            args.tf_dir, app_dir=args.app_dir, gui_browser=args.gui_browser,
        ), sort_keys=True,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
