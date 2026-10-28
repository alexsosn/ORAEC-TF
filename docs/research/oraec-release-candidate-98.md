# ORAEC software release-candidate version research (#98)

2026-10-28. Parent release gate: #12. Scope is the Python **software candidate**, not publication of a TF corpus.

## Verified repository evidence

- Main is `637ed34be80e7aeffe1973a6deb359b8d78b351d` after PR #97. GitHub Releases API currently returns an empty array; no published ORAEC wheel or release can be claimed.
- `pyproject.toml [project].version` and `src/oraec_tf/__init__.py::__version__` are `0.1.0.dev0`. The installed-wheel verifier `scripts/validate_wheelhouse_install.py` and installed-smoke `scripts/smoke_installed_distribution.py` independently assume the same development version.
- `tests/test_released_dependency_install.py` constructs several synthetic `0.1.0.dev0` wheels; `tests/test_installed_distribution_contract.py` also assumes this version in its fixtures and source-assertions; `tests/test_readme_status.py` demands the old README marker. A metadata-only version bump will break wheelhouse acceptance and CI.
- PR #97 merged with a published, hash-checked `tf-build==0.1.0rc1` dependency and real Linux/Windows offline install tests, full source, browser, Agora and Rust checks. The README's introductory statement that #59 is still an offline dependency *blocker* is obsolete; #59 is closed.
- `MANIFEST.in` includes only schema and requirements inputs; `setup.py` copies the canonical schema into the wheel. Existing release-boundary tests enforce no ORAEC raw JSON/TSV or generated TF data. Software-only distribution remains the fixed scope.
- `.github/workflows/installed-wheelhouse.yml` builds the ORAEC wheel in CI and actually reads wheel METADATA, installs with `--no-index --require-hashes` and runs the packaged app/TF smoke. `.github/workflows/writer-validation.yml` audits the complete 13,026-text corpus; `.github/workflows/agora-materializer.yml` tests the local adapter.

## Decision

Freeze the **unpublished** ORAEC candidate as `0.1.0rc1`, leaving the tf-build dependency at its independently published `0.1.0rc1`. Synchronize all relevant source/installed/version tests. No release is asserted until exact-head full CI and independent review; no tag is created by this ticket.

## Threat model and exclusions

- A version mismatch can make the real wheel installation fail even when editable tests pass, or make a fake distribution appear valid. Require exact source/metadata/wheel assertions and a wrong-version negative test.
- A successful software installation does not grant permission to redistribute the CC BY-SA corpus or Karnak crosswalks. Do not add data or broaden Agora's default mapping mode.
- The release candidate must be tested on actual installed bytes; source-only greps are insufficient.
- Do not conflate valid RC metadata with a published GitHub Release or a final `0.1.0` tag.
