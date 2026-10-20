# Plan — browser HTTP user-facing acceptance (#93)

1. Research TF 13.1 upstream browser factory, Web kernel, Flask request parsing and current smoke. Record in research.
2. RED first: add a test on the synthetic ORAEC app asserting that `verify_local_advanced_app` reports real browser home response 200, POST query positive results for the attested first text, and 200 for a passage navigation. Enforce no network listener or source data copying.
3. GREEN: instantiate genuine `tf.browser.web.factory(Web(makeTfKernel(app, 'ORAEC-TF')))` with the already loaded standard App, make real `test_client` requests, parse real JSON and reject HTML 500 / empty search, preserve Unicode pretty/text rendering and prior report keys.
4. Add docs explaining existing advanced-app rendering vs Flask HTTP smoke vs unsupported GUI clicks. In full pinned writer CI, existing smoke script must execute the new routes on the very same independently verified generated TF graph.
5. Test Python 3.11–3.13, standard complete 13,026-text writer and Agora smoke, wheelhouse, exact head. Independent adversarial review explicitly check actual handler paths/results in logs, no mocked `serveQuery` and no accidental source release; merge only if all green.
