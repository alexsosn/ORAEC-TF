# Research — ORAEC-TF vs Rust Context-Fabric 0.6.0rc1 (#91)

Date: 2026-10-20. Parent feature parity issue #88, prior Python-CFM benchmark #84 and PR #86.

## Verified upstream contract

- PyPI `context-fabric==0.6.0rc1` released 2026-10-15; Rust core, Python >=3.13, pre-release with Linux/macOS/Windows wheels.
- Public API `from cfabric import Fabric` and `Fabric(locations=...).loadAll()`; first access compiles new `.cfr/4/` cache (or `$CFABRIC_CACHE` fallback) rather than 0.5.x `.cfm`.
- Rust API docs claim Text-Fabric F/E/C/L/N/T/S-compatible access, but deterministic search result order may differ; results should be compared as sets, preserving tuple atom ordering.
- PyPI docs state cache rebuilds when a `.tf` feature changes. Verify this with changed scalar values on a separate disposable real .tf fixture rather than trusting metadata.
- Existing `tests/test_context_fabric_acceptance.py` tests Python Context-Fabric 0.5.7, not Rust RC1.
- The earlier full ORAEC benchmark (#84/PR #86) measured Python CF 0.5.7: warm native Text-Fabric 4.50s / 2.84GiB RSS, CFM 5.0s / 0.685GiB RSS, initial compile ~192s / 6.05GiB. 62 feature names but not values were checked. None of these timings apply to Rust 0.6.

## ORAEC real-source acceptance

- Pinned upstream source `oraec/corpus_raw_data@b83a0ee5fae27a40d4c0a2a9a8c9c2973d45e9cd`, default schema v3: 13,026 texts; 101,796 sentences; 815,026 source tokens; 815,029 slots; 998,775 nodes; 2,930 native CR occurrences.
- 65 source .tf features (including otype/oslots/otext); audit values for all 62 node/edge features, and native edge values including source filenames.
- Current default and Agora exclude Karnak; explicit local option includes 31 text and 1,973 lemma edges (#85). Never publish those derived datasets without #17 rights review.
- Full source→native TF independent audit and researcher/browser smoke must precede Rust experiments. Do not modify the original converter or mandatory release gates.

## Threat model / design

- A compiled cache can preserve feature **names** while corrupting values, missingness, edge targets, edge values or source freshness. Reject these independently.
- Canonical comparison must be typed (distinguish None, empty string, integer vs numeric string); sort node IDs and edge targets, do not flatten one-to-many relations; stream to avoid full materialization.
- Search result sets can differ in order; preserve each result tuple's atom order. Verify representative F/E/L/T/S, CR restore and discontiguous lexical nodes.
- Separate Python >=3.13 Rust CI; no dependency or production backend migration for the 0.1.0 software release. Upload provenance and aggregate digests only; no raw source, .tf, or .cfr.
