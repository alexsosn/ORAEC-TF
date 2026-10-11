# Research: independent source-to-graph audit profiling (#74)

2026-10-11. Parent performance issue #64. Baseline exact-source CI runs: PR #68 [38146650124] audit ~14:41:24–14:46:16 UTC (292s), PR #71 [38151317684] audit ~15:40:55–15:44:05 UTC (190s). Both passed **full independent** 13,026-text, 815,026-token, 3-anchor, 2,930-CR audits. These are separate GitHub-hosted runner measurements, not a controlled speedup benchmark.

Implementation inspected on merged main `59cebf35`:
- `scripts/validate_graph_source.py` calls `audit_graph_with_provenance(... require_complete_source=True)`, writes authoritative JSON count+fingerprint report and prints only aggregate counts.
- `src/oraec_tf/audit_graph.py::audit_basic_graph` privately loads **all** TF graph features with `Fabric(...).loadAll()`, independently verifies raw JSON values/token nodes/hierarchy/mappings/CR information. This **must not be removed** or replaced by converter's parser/count probe.
- `audit_graph_with_provenance` then hashes raw and semantic SHA-256 of **all** generated `*.tf` features via `hash_tf_feature`; these hashes must stay identical. Its SHA output is original provenance, not profiler output.
- `src/oraec_tf/conversion_profile.py::PhaseRecorder` already collects nonnegative wall time/CPU time, process high-water RSS in KiB only on Linux, python/platform/TF and tf-build versions, and phase names. It intentionally stores **no** token strings, source paths, or artifact bodies.
- `.github/workflows/writer-validation.yml` runs the full independent audit and uploads a provenance-only counts archive.

The smallest observable decomposition reuses an optional recorder and captures `independent_fabric_load` **nested** in `source_graph_audit`, plus `feature_hashes`. `source_graph_audit` includes the fabric loading time, so exclusive semantic check duration is only estimated by subtracting its nested measurement; document inclusive semantics clearly. Avoid indenting/refactoring the existing 300-line independently verified audit logic simply to add timing. Emit a **separate opt-in profile JSON**; keep the primary report byte-for-byte untouched so existing SHA/revision semantics never change. Profiling is observational and cannot cause a clean audit to pass if it would otherwise fail.
