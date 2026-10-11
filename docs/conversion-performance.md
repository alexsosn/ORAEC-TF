# Profiling pinned ORAEC Text-Fabric conversion

Issue [#64](https://github.com/alexsosn/ORAEC-TF/issues/64) tracks conversion throughput, latency and memory without weakening source-to-graph conservation. The profile is an **opt-in, provenance-only** diagnostic; default CLI JSON and TF output are unchanged.

For a verified local source checkout:

```bash
mkdir -p build
oraec-tf convert upstream/corpus_raw_data \
  --output build/profiled-tf \
  --upstream-commit b83a0ee5fae27a40d4c0a2a9a8c9c2973d45e9cd \
  --profile > build/phase-profile.json
```

The ordinary JSON conversion summary gains a `profile` property only when the flag is passed. Its `environment` identifies the Python, Text-Fabric, tf-build versions and platform for comparisons; it records nonnegative `total_wall_seconds`, `total_cpu_seconds`, and an ordered `phases` array. Each phase contains `name`, `wall_seconds`, `cpu_seconds`, and `process_peak_rss_kib_at_end`. Peak RSS is **process-lifetime high-water RSS at each phase's end**, not an exclusive per-phase allocation. Linux `ru_maxrss` is measured in KiB; unsupported platforms return `null`, never a guessed number.

Phases:
- `source_identity`: verify the canonical pinned clean local Git source.
- `source_semantics`: independently validate the complete raw source before any output mutation.
- `writer_and_ir`: parse text, metadata and mapping IR and write the whole native TF graph; this phase includes internal serialization and is not yet split further.
- `uncached_tf_validation`: tf-build isolates and exhaustively reloads all actual `.tf` features without trusting existing binary caches.
- `corpus_counts_reload`: independent Text-Fabric reload and exact text/sentence/token/anchor count reconciliation.
- `source_tf_counts_probe`: experimental, strict streaming node-feature census of `otype.tf` and `token_id.tf`, compared *after* complete tf-build and Fabric reload validation. It cannot authorize publication or replace either loader; profile mode fails closed on mismatch.
- `atomic_publish`: no-clobber completed native TF output publication.

A full CI run additionally performs an **independent raw JSON/TSV-to-TF graph conservation audit** and standard advanced-app smoke *after conversion*. Those external stages have their own GitHub Actions timing; conversion phase totals do not pretend to include them.

The [pinned-source validation workflow](../.github/workflows/writer-validation.yml) retains the existing validated output and now writes this profile alongside count/provenance data. It uploads **no corpus text, source JSON, TF feature bodies, generated caches, or semantic sidecars**. A profile is observational evidence, not a speedup claim or a validation substitute.

## Controlled optimization gate

Record timings, peak RSS, pinned source/revision, Python, TF and tf-build versions, and runner model on comparable runs. Identify an actual measured hotspot. An optimization PR must use RED tests, compare before/after on the same snapshot/runner configuration, preserve identical semantic graph hashes, pass both independent conservation and installed-app gates, and undergo exact-head adversarial review. Do not remove the uncached source-only validation or source-count reload solely because they look redundant; their trust and semantic contracts differ.
