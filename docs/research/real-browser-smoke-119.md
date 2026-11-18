# Research: real browser researcher journey (#119)

Base ORAEC main `421b414e9aab8e02e431b28cb70dc895727fb23b`, 2026-11-18.

Current `scripts/validate_advanced_app.py` creates the actual standard Text-Fabric 13.1 `tf.browser.web.factory(Web(makeTfKernel(...)))` from the same loaded native graph, but only calls Flask's `test_client`. It proves server handlers; it does **not** execute shipped `/browser/static/tf3.0.js` or graphical navigation. The wheel-installed full-source rehearsal `.github/workflows/release-rehearsal.yml` uses that script, so its browser assertion has the same limitation.

Inspected pinned upstream **annotation/text-fabric tag v13.1.0**, not inferred selectors:
- `tf/browser/templates/index.html`: `form#go`, editable `textarea#query[name=query]`, `button#queryGo`, `#nresults .nresults`, `#queryTable`, `#modepassage`, `#passageTable`, `details#options` with `input[name=textFormat]` radios generated via `tf/browser/wrap.py::wrapSelect`. Radio values derive from the locally generated graph's allowed formats, including `text-translit` and `text-hiero`.
- `tf/browser/static/tf3.0.js` attaches the search click listener in `$(window).on('load')`, sends real AJAX `POST /query`, writes results and count to the DOM, and loads passage content with `POST /passage`. A Flask test_client check cannot establish these behaviors.
- `tf/browser/web.py` exposes exactly that Flask app, and `tf/browser/start.py` starts a regular Werkzeug server. Reusing the current in-memory `webapp` over a **loopback ephemeral port** via Werkzeug avoids another expensive `Fabric.loadAll()` and avoids exposing a remote service.
- `app/config.yaml` defaults to `text-translit`, declares `browseNavLevel: 1` and supports `text-hiero`. For a stronger GUI formatting check, select an **attested** source word carrying a hieroglyphic string, get its exact text identity from Text-Fabric, and require both the format radio and script rendering on the selected text; never invent hieroglyphs.

Constraints: Playwright + Chromium are **test-only** (not a converter/wheel dependency); wheel-installed release rehearsal can opt into real GUI via an explicit CLI flag. Make errors, timeouts, absent controls, JavaScript failures, empty Ajax response and missing visible text fail closed. Terminate loopback server/browser in `finally`. Never upload screenshots, raw source, rendered text or corpus caches as artifacts. The existing full-corpus writer and source-conservation audits remain mandatory before GUI smoke.

Execution plan must be explicit because CI ordinary unit jobs intentionally do not download browser binaries. Synthetic author-created ORAEC fixture exercises the same script when Playwright is available; the release rehearsal branch `feature/real-browser-gui-119` will exercise the installed-wheel **full** corpus.

## Independent selector correction before CI

The pinned `tf/advanced/links.py::webLink` returns **plain text**, not a clickable `.pq` anchor, when `webBase`/`webUrl` are deliberately absent (as in the ORAEC app). Therefore a GUI smoke **must not depend on clicking a search-result permalink**. Text-Fabric's `tf3.0.js::modes`, `filterS0`, and `subLinks` instead expose the real passage navigator: click `#modepassage`, filter `#s0filter`, and click the exact `#passages .s0nav` entry. This preserves the verified no-invented-URL metadata policy and actually uses a researcher-facing navigation control.


## Actual pinned full-corpus Chromium failure and upstream mode mismatch

The installed-wheel full-graph graphical runs on [head c7a1db3](https://github.com/alexsosn/ORAEC-TF/actions/runs/44326047578) and [head 182e95a](https://github.com/alexsosn/ORAEC-TF/actions/runs/44354053639) reached the **last** Playwright assertion, after actual Ajax `POST /query`, passage-navigation `POST /passage`, selecting the `text-hiero` radio and the expected main-form `POST /` reload. They timed out waiting for the attested hieroglyph in `#passageTable`. This is **not** a search failure. Python CI, native writer, Context-Fabric and independently audited full source graph passed.

Direct upstream code inspection finds that Text-Fabric v13.1.0 `tf3.0.js::subLinks` calls `getTable(kind, subkind, "passages")` for `.s0nav`, while `switchMode` only handles `"passage"` (singular) and `"results"`; its unconditional `mode.val(m)` leaves an invalid hidden mode. After a radio-triggered full-page reload, this can prevent the normal passage-mode visibility restoration even though the AJAX request succeeds. The bounded GUI test now uses the *actual visible* Results → Passages mode controls to normalize the mode before selecting a format, and fails closed with counts/booleans for format/reload failures. This is a workaround for an upstream browser UI state mismatch, not a patch to Text-Fabric nor evidence that an untouched upstream passage link works across reloads.

## Renderer-specific root cause, regression gate and correction (2026-11-18)

On exact-head [run 44357420192](https://github.com/alexsosn/ORAEC-TF/actions/runs/44357420192), graphical Chromium still failed **after** the browser button-based mode recovery. Bounded failure data: `mode=passage`, `radio_checked=True`, `passage_visible=True`, `passage_dom_chars=18`, `passage_visible_chars=18`, and zero uncaught JavaScript errors. This rules out hidden mode and selector/visibility failures as the immediate cause of the missing hieroglyph.

Actual pinned Text-Fabric `tf/browser/kernel.py::passage` chooses `items=contentNode` when ORAEC config sets `browseContentPretty: true`. `tf/advanced/tables.py::composeP` then invokes `pretty(app, textNode)` instead of sentence rows. A text is a potentially big section, and `tf/advanced/unravel.py::_getBigType` can suppress descendants of big sections in a non-full display. The observed 18-character browser content is consistent with an enclosing-text heading rather than the first-sentence source text. The initial test incorrectly accepted any nonempty passage content, so it missed this.

ORAEC researcher navigation requires sentences: fix `app/config.yaml` to `browseContentPretty: false` while retaining `browseNavLevel: 1` (Text-Fabric then enumerates `L.d(text, otype="sentence")`, and `composeP` renders `_plainTextSFinal` sentence rows). RED-first `tests/test_advanced_app.py` commit `281bb259` asserts this. Graphical checks now require actual `#passageTable details.pretty` rows before format switching, and an independent `POST /passage` with `text-hiero` must contain the attested glyph before browser DOM automation. This is a native standard-TF config change, not a package data modification or JS patch.

The separate upstream `"passages"` vs `"passage"` mismatch remains genuine and tracked by #121, but the mode normalization alone **did not** resolve the observed glyph failure; do not attribute the missing rendered text to that state bug without further evidence.
