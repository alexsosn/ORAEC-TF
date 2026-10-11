# Plan: ORAEC conversion staging through tf-build

Issue #54, following already merged source acquisition PR #53.

1. **RED-first** tests in `tests/test_cli.py` using the real small `TextIR` + `write_tf` + `Fabric` fixtures:
   - arrange a competing destination with a sentinel immediately before the publication operation; conversion must fail without replacing or deleting the sentinel and leave no staging directory;
   - corrupt a real `sentence_index.tf` integer body after compiling a newer Text-Fabric cache, restoring raw mtime; conversion must fail exhaustive source validation, publish nothing and clean staging;
   - preexisting empty target succeeds; a deliberate late writer failure restores a preexisting empty target; original source and output-inside-source invariants still pass.
2. Run fast CI on the RED test-only commit; require a behavioral failure (not a typo/import error), while draft full-source checks may be skipped.
3. Implement in ORAEC's `_convert` only:
   - preserve frozen-revision/source/target preflight and `validate_corpus_source` ordering;
   - remove an existing empty output directory after preflight and source validation, then construct `BuildWorkspace`; on exception restore it only if no other actor has created a replacement;
   - write into `workspace.path`; call shared raw-source-backed `validate_tf_artifact(level="all", require_otext=True)` and ORAEC's original real Fabric count conservation; publish through `workspace.publish()`;
   - never move ORAEC scholarly IR, ontology, native CR model or count check into tf-build.
4. Update README to describe atomic no-clobber promotion, source-backed exhaustive validation, and the preexisting-empty compatibility interval.
5. Exact-head fast Ruff/strict mypy/pytest on 3.11–3.13; then ready-state full pinned-source writer, independent conservation, advanced-app and Agora CI on **the same exact head**.
6. Perform a truly independent adversarial review based on source code, actual emitted features and pinned-source logs; re-run gates after any behavior-changing fix and only then squash-merge.

7. Independent CI gap: add RED-first check that the Agora pinned-source workflow's `pull_request.paths` includes both `src/oraec_tf/cli.py` and `tests/test_cli.py`. Patch only this path filter and rerun fast CI, then ready-state full native writer **and** Agora full pinned-source workflows on the exact new head. Treat missing/skipped Agora runs as failure of the merge gate.
