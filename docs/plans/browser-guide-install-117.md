# Plan: researcher browser install guide correction (#117)

## Scope and invariants
1. Keep existing clone, fetch, convert, standard browser steps in `docs/app-browser.md`. Change only the clone's `pip install` to match real CI and README's hash-pinned published `tf-build` wheel command.
2. Replace the obsolete #59 blocker assertion with an accurate short note: offline wheelhouse resolution **is already validated** for Linux and Windows, needs platform-specific acquisition, and ORAEC-TF's own release is still unpublished under #12. Link `installed-distribution.md`.
3. Do not alter code, dependencies, output schema, Karnak/data rights, or publication rules.

## RED-first tests
- Add `tests/test_browser_guide_install.py` before changing the guide. Parse the actual fenced Bash command in the clone workflow and assert `pip install -r requirements/tf-build.txt -e '.[dev]'`; cross-check package dependency metadata and published wheel requirement file. On base HEAD the command assertion fails.
- Assert the guide no longer claims #59 blocks dependency-resolving offline installation and still distinguishes the unpublished ORAEC candidate. On base HEAD the stale-text assertion fails.
- GREEN: correct exactly these documentation lines; use CI Python 3.11–3.13 to run full pytest, Ruff and mypy. This is documentation-only, not a new TF writer algorithm.

## Independent adversarial review
Separate audit of final PR diff and actual `ci.yml`, `pyproject.toml`, `requirements/tf-build.txt`, closed #59 evidence, and release state. Look for quoting errors, impossible installation command, unsupported offline promises, or accidental claim that the ORAEC release exists. All reviewed head checks must be green before merge.
