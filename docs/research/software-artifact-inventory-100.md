# Actual wheel/sdist software-boundary research (#100)

2026-10-28. Parent #12.

Current code-grounded findings:

- `tests/test_writer_wheel.py` builds a real wheel with pip and sdist with setuptools, checks the frozen schema and rebuilds from the sdist. It does **not** check the full archive member list.
- `tests/test_installed_tf_app.py` verifies the packaged app by checking expected contents and the absence of two example files in one source directory, not the built wheel and sdist inventories.
- `tests/test_release_data_boundary.py` checks upstream licensing/docs and schema exclusions; it does not examine release archive contents.
- `MANIFEST.in` adds the canonical schema and requirements, while `setup.py` copies `schema/core.json` to `oraec_tf/schema_core.json` at build time and `pyproject.toml` includes `oraec_tf/tf_app/config.yaml`. These JSON/YAML files are software resources and must not be falsely flagged as corpus data.
- Current packaging tests demonstrate a clean *importable* wheel but leave a safety gap: generated `.tf` (plus `.tfx`/`.cfr`), raw ORAEC `oraecN.json`, `mapping_*.tsv`, or unexpected package resources might be shipped without breaking those tests. The software-only release forbids these payloads.

**Design boundary:** verify the actual archive inventory of **both** wheel and sdist after building, with a limited explicit software-file policy. Validate member path normalization and type to prevent traversal and symlink tricks. Explicitly allow canonical schema JSON, Agora descriptor JSON and TF app YAML, while rejecting corpus/raw/cache resources. A test which merely checks one filename or relies on a clean checkout is not an adversarial archive audit.

No upstream corpus files or generated TF examples are needed; synthesize hostile archive entries for negative tests. Keep changes in a reusable standalone audit script plus existing distribution tests; do not add any runtime dependencies or change package data itself.
