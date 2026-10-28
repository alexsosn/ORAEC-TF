# Plan: enforce software-only archive inventory (#100)

1. Add **RED-first** archive tests using deliberately malicious synthetic wheel/sdist members: raw ORAEC `oraec1.json`, mapping TSV, TF `otype.tf`, compiled `.cfr/.tfx`, unknown package resource, symlink, traversal. Demand explicit preservation of `oraec_tf/schema_core.json` and `oraec_tf/tf_app/config.yaml` in a valid wheel, and `schema/core.json` in a valid source archive.
2. Implement a small, standard-library-only `scripts/audit_software_release.py` with pure `audit_wheel` and `audit_sdist` functions and an optional CLI. Normalize tar top-level distribution prefix; reject unsafe paths/types; restrict wheel package payload to Python source, canonical schema, packaged app, and standard dist-info; restrict sdist to software/code/test/docs/requirements directories and known release input files. Use explicit paths rather than blanket JSON and text extension bans. Reject unexpected raw/cached corpora anywhere, including under alternative directories.
3. Extend `tests/test_writer_wheel.py` to call the same audit on *real* setuptools/pip build artifacts already produced by the tests, not just synthetic archives. Avoid extra full-corpus pipelines and external dependencies.
4. Exact final head: Ruff/mypy/pytest 3.11–3.13, real Ubuntu/Windows installed-wheel tests, pinned-source conservation/browser and Agora where invoked; independently re-inspect actual tar/zip contents and attempt adversarial synthetic bypasses.
5. Merge only on successful exact-head tests and logically independent review. Keep #12 open until versioned release assets and published consumer E2E are qualified; no corpus bytes uploaded.

No change to parser/writer/schema, Python supported versions, or pinned data snapshot.
