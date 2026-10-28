# Plan: ORAEC 0.1.0rc1 software-only candidate (#98)

1. **RED first.** Add an independent candidate contract test that requires `0.1.0rc1` in built metadata source, Python package `__version__`, wheelhouse verifier, installed distribution smoke and README; demand correct version rejection in the real wheel METADATA verifier. Commit before implementation. Preserve the actual failing CI step as evidence.
2. **Minimal implementation.** Bump exactly the ORAEC package version; update the verifier and installed smoke expected version, synthetic fixture wheel versions and version assertions. Preserve dependency `tf-build==0.1.0rc1`, pinned upstream revision, all native TF graph semantics, schema and no-data packaging.
3. **Documentation.** Describe a tested but **not yet published** RC candidate; remove inaccurate suggestion that closed #59 still blocks software packaging; keep #12 as final release gate and #17 / Agora #224 explicitly separate.
4. **Verification.** All Python versions (3.11–3.13), Ruff/mypy/pytest, actual released dependency Windows/Linux offline-installed wheel jobs, whole-source writer/conservation/browser HTTP, Agora materializer and Rust feature parity on exactly the final PR head. No skipped draft full-corpus check counts.
5. **Logically independent review.** Re-read the final diff and actual workflow conclusions independently of implementation design. Attack wrong-version and missing-wheel failure, app import provenance, source/data leakage, stale public documentation and any workflow path that can silently skip. Do not approve/merge on in-progress CI.
6. **Finish.** Merge only if exact-head CI and review pass; #12 stays open pending final software-only tag/release/independent install of *published* artifacts.

Explicitly excluded: corpus schema changes, new graphical apps, upstream TF monkeypatching, Karnak hosting, generic release infrastructure.
