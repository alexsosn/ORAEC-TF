# Research — Text-Fabric browser HTTP smoke (#93)

Verified actual Text-Fabric v13.1.0 upstream code at annotation/text-fabric tag v13.1.0:
- `tf.browser.web.Web(kernel)` stores App context and `factory(web)` constructs the genuine Flask browser app.
- `tf.browser.kernel.makeTfKernel(app, appName)` adapts an already loaded real standard TF App to browser routing. It is not a mocked response.
- Browser routes: `GET /` returns the actual HTML page; `POST /query` accepts form `query` and returns JSON keys `table`, `nResults`, `status`, `messages`, `features`; `/passage` returns passage JSON.
- `tf.browser.servelib.getFormData()` uses request.form, with defaults for batch, position, textFormat and optional settings. Query should be a real TF search `text oraec_id=...` from the generated local corpus.
- `scripts/validate_advanced_app.py` currently invokes App(_browse=False) and pretty text; it does not call web.factory or execute HTTP handlers. CI describes this as browser smoke and does not truly test the browser.
- Real output corpus is already built in full pinned source writer CI before this script runs, with 13,026 texts, original independent source conservation and immutable upstream source SHA.

Flask `test_client` invokes the exact application routing and query composition without an OS port. This is genuine browser HTTP request handling but not a headless Chromium/Playwright GUI test. Scope requires only HTTP+HTML and JSON route correctness, not automatic JS click testing or opening externally accessible network listeners. User data never leaves CI's ephemeral file system. Use exact source ids supplied by `api.F.oraec_id` and reject missing/no-result/5xx queries.
