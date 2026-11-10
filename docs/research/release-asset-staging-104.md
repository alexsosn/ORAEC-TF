# Research: audited software-only ORAEC RC distribution (#104)

2026-11-10. Parent release gate #12. The GitHub Releases API returned no releases for `alexsosn/ORAEC-TF`. Main head after PR #103 is `07c9245724e656fde61b4fc9d8b2d4b67db978b2`; package metadata and `__version__` are `0.1.0rc1`.

Evidence from actual project code and workflows:

- `setup.py` copies canonical `schema/core.json` into wheel resources, while `pyproject.toml` includes the standard app configuration. `tests/test_writer_wheel.py` already builds an actual pip wheel and setuptools sdist, rebuilds a wheel from the sdist, and checks canonical schema bytes.
- `scripts/audit_software_release.py` has explicit wheel and sdist member allowlists and rejects raw ORAEC files, TF/CF caches, traversal, symlinks and nonregular tar members. The real Ubuntu/Windows wheelhouse CI and PR #101 independently audited the actual artifact inventories.
- `.github/workflows/release-rehearsal.yml` now proves the installed `0.1.0rc1` wheel can acquire the immutable 13,026-text source, convert it, independently conserve graph semantics and serve real Flask test-client browser requests. Its source files and generated TF live in runner temp; only small diagnostics are uploaded.
- `.github/workflows/writer-validation.yml` and `.github/workflows/agora-materializer.yml` support manual dispatch of exact `main` and perform full pinned-source checks. `.github/workflows/ci.yml` runs on pushes to `main`.
- `tf-build/.github/workflows/release.yml` publishes an existing immutable version tag, validates tag/version/main ancestry, checks successful CI on exactly the tagged commit and refuses an existing release; publishes wheel, sdist and SHA256 manifest. ORAEC needs the same minimal release discipline but with its archive/member audit and complete-source prerequisites.
- Connector currently exposes read/review/merge and branch operations, but no creation of annotated tags or GitHub Releases. Therefore a manual existing-tag workflow is a precise, auditable publication path; staging and unit tests can run in PR CI without publishing anything.

**Decision:** add one standalone standard-library release-artifact verifier and release workflow. Its PR path performs actual software wheel/sdist builds + sdist-rebuild payload comparison, version and archive checks and a source-free JSON SHA256 manifest; publishing stays gated by manual dispatch on `main`, an existing immutable `v0.1.0rc1` tag at HEAD, successful exact tagged SHA CI / native source audit / installed full E2E / Agora, and no existing release. Do not create/move the tag automatically. Do not upload any corpus data.
