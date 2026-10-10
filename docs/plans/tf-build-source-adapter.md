# Plan: incremental ORAEC pinned source migration

Issue #52 (child of tf-build#53).

1. Preserve exact `SourceSnapshot(path, revision)` dataclass, `SourceAcquisitionError`, ORAEC's 40-hex revision validation, root-only verification and source fetch/verify CLI JSON.
2. RED-first: replace fake origin-remote test with real local repository acquisition: assert actual detached full revision, clean tree, no persisted origin and absent `FETCH_HEAD`; test that a destination created immediately before atomic publish remains unchanged and staging is cleaned. Keep early invalid revision, nonempty/dangling symlinks, failures and dirty/untracked tests.
3. Add exact-commit tf-build dependency, not branch dependency. CI must prove the pinned package installs and tests pass on 3.11–3.13; describe network-at-install limitation.
4. Implement `fetch_source` and `verify_source` as narrow adapters calling `tf_build.source`. ORAEC root/sha checks remain local; translate expected errors to `SourceAcquisitionError`. Keep existing `resolve_revision` compatibility if external code imports it.
5. Do NOT touch converter/writer or schema PR #51. For publication migration create an independent follow-up after proof of stable source installation.
6. Run Ruff, strict mypy, pytest and appropriate real-source CI on exact PR head. Logically independent adversarial review must inspect the actual emitted Git checkout and behavioral differences before merge.

7. RED-first workflow contract: assert full pinned-source Agora workflow paths include `src/oraec_tf/source.py`, `pyproject.toml`, and `tests/test_source.py`, because every such change affects the source acquisition invoked by Agora. Add path filters without changing the pinned source, native schema, or run steps. Ready-state check must run for **both** writer and Agora integration on the exact head.
