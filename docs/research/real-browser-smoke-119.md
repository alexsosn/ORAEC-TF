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
