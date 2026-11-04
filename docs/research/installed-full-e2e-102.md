# Installed-wheel full researcher E2E: source/code evidence (#102)

2026-11-04. Parent release gate #12. This is a **software-only** release rehearsal, not publication of a dataset.

## Evidence from current ORAEC source

- `.github/workflows/writer-validation.yml` uses `pip install -e '.[dev]'`, then the real `oraec-tf fetch` / `verify-source` / `convert` path on frozen `b83a0ee5fae27a40d4c0a2a9a8c9c2973d45e9cd`. Its independent source-graph audit and genuine Text-Fabric Flask homepage, query and passage checks run on the full 13,026-text graph. Thus full-corpus correctness is proven, but with editable Python.
- `.github/workflows/installed-wheelhouse.yml` downloads the published hash-verified `tf-build==0.1.0rc1` wheel and runtime hash lock, builds a noneditable `oraec_tf-0.1.0rc1` wheel, validates software-only wheel inventory, and installs to `$RUNNER_TEMP/offline-venv` using normal pip resolution, no Git, no index. It checks the installed package and standard TF app on a small *synthetic* graph, not the full ORAEC source.
- `scripts/smoke_installed_distribution.py` checks installed import paths relative to `sys.prefix`, checks public `app-path`, and confirms packaged `config.yaml` parity. It deliberately does not acquire the source: its offline smoke intentionally hides Git.
- `scripts/validate_advanced_app.py` contains the real HTTP smoke (homepage, `/query`, `/passage`) but selects the repository-root `app/` unconditionally. For user-wheel E2E it should accept the installed app path explicitly, with repository behavior as the default.
- `scripts/validate_graph_source.py` performs an independent complete source→graph audit, yet is a repository helper. Running it with the **installed venv interpreter** (`python -I`) ensures imported ORAEC code is from the wheel, not an editable import.
- Default conversion excludes both Karnak crosswalks, which remain local-only opt-in and not release corpus data.

## Decision

Add one release-only rehearsal (manually dispatchable and exercised on its issue branch) composing the existing verified primitives: local full acquisition, wheel-installed default CLI conversion, independently check the complete graph and representative browser actions using the installed app. No new TF container/cache, no new runtime dependency, no data artifact. Store generated ORAEC source/TF in runner temp only and upload source-free count/provenance JSON. Preserve the existing two-platform offline installation tests and normal full-corpus validation. Allow the rehearsal to be expensive without running on unrelated PRs.
