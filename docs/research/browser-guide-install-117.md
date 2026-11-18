# Research: browser guide install contract (#117)

2026-11-18, base main `765b8ffae165b8b74ce470df8dd01152bba34a67`.

- `docs/app-browser.md` documents a clone-only path with `python -m pip install -e '.[dev]'`, which does not include the separately pinned published `tf-build` wheel. The package's `pyproject.toml` requires `tf-build==0.1.0rc1`; `requirements/tf-build.txt` provides its specific GitHub release wheel plus SHA256.
- Actual repository CI (`.github/workflows/ci.yml`, Python 3.11/3.12/3.13) installs with `python -m pip install -r requirements/tf-build.txt -e '.[dev]'`. `README.md` gives the same command. Using that exact invocation in the browser guide removes the unverified assumption of PyPI hosting.
- The first guide section additionally says offline dependency-resolving wheel installation remains blocked under #59. But merged PR #97 and `docs/installed-distribution.md` demonstrate Linux and Windows verified hash-locked wheelhouse installation with dependency resolution. #59 was closed. This is separate from unshipped **ORAEC-TF** v0.1.0rc1, which is still not published (GitHub Releases returned `[]` on 2026-11-18).
- The existing code provides `oraec-tf app-path`, and installed app tests prove the wheel includes the standard app `config.yaml`. Current guide shell browser examples are unchanged.

No source data or output semantics are involved. Do not imply a GitHub ORAEC release exists or that the entire corpus can be bundled or redistributed.
