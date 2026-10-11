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
- `source_tf_counts`: strict source-only streaming census of `otype.tf` and `token_id.tf`, compared to the independent upstream raw-corpus parser counts **after** tf-build has exhaustively loaded every real `.tf` feature without trusting compiled caches. This replaces only the *second* duplicate Fabric reload; a mismatch fails before atomic publish. The separate full raw-source-to-graph auditor remains mandatory in CI.
- `atomic_publish`: no-clobber completed native TF output publication.

A full CI run additionally performs an **independent raw JSON/TSV-to-TF graph conservation audit** and standard advanced-app smoke *after conversion*. Those external stages have their own GitHub Actions timing; conversion phase totals do not pretend to include them.

The [pinned-source validation workflow](../.github/workflows/writer-validation.yml) retains the existing validated output and now writes this profile alongside count/provenance data. It uploads **no corpus text, source JSON, TF feature bodies, generated caches, or semantic sidecars**. A profile is observational evidence, not a speedup claim or a validation substitute.

## Controlled optimization gate

Record timings, peak RSS, pinned source/revision, Python, TF and tf-build versions, and runner model on comparable runs. Identify an actual measured hotspot. An optimization PR must use RED tests, compare before/after on the same snapshot/runner configuration, preserve identical semantic graph hashes, pass both independent conservation and installed-app gates, and undergo exact-head adversarial review. Do not remove the uncached source-only validation or source-count reload solely because they look redundant; their trust and semantic contracts differ.

## Independent full source→TF conservation profiler (#74)

The **separate mandatory** raw JSON/TSV→TF auditor has an opt-in provenance-only timing report, unrelated to and not a replacement for conversion timing. The full writer CI invokes:

```bash
python scripts/validate_graph_source.py upstream/corpus_raw_data build/tf \
  --source-revision b83a0ee5fae27a40d4c0a2a9a8c9c2973d45e9cd \
  --converter-revision "$(git rev-parse HEAD)" --schema-version 3 \
  --report build/graph-conservation.json \
  --profile-report build/independent-audit-profile.json
```

The optional `independent-audit-profile.json` uses `oraec-independent-audit-profile-v1` and reports **in completion order**: `independent_fabric_warp_load` (actual upstream `load("")`, including TF base/warp setup), `independent_fabric_features_load` (actual upstream `load(all node+edge features, add=True)`), `independent_fabric_load` (inclusive full `Fabric.loadAll`, including feature exploration), `source_graph_audit` (inclusive of that load and all raw-source/TF semantic comparisons), and `feature_hashes` (raw+timestamp-neutral SHA-256 across every `*.tf`). Subphases are opt-in timing wrappers on the same Text-Fabric instance: no features are skipped and native arguments/return values are forwarded unchanged. To estimate time spent comparing the corpus after its independent load, subtract `independent_fabric_load.wall_seconds` from inclusive `source_graph_audit.wall_seconds`; wall clock variance means this is approximate. Peak RSS is a high-water mark, **not** the memory allocated by a particular phase. Original `graph-conservation.json` contents and stdout aggregate counts remain unchanged, and the profile never contains source strings, paths, feature values, or corpus payload. The profile measures costs; it does not enable skipping a single validation.

### Base warp precomputation and API attribution (#78)

Within the already nested `independent_fabric_warp_load` phase, the optional audit profiler records native `independent_fabric_warp_precompute` for Text-Fabric 13.1's original `_precompute()` and `independent_fabric_warp_api` for its original `_makeApi()`. Both are invoked with unchanged arguments and returned results, and the original method lookup is restored on success or failure. The remainder of the inclusive warp duration covers native warp feature reads, metadata discovery and scheduling; subtracting nested wall times is an estimate rather than a separate measurement. The feature-loading, source/graph-conservation and hashing phases remain unchanged. These measurements do not constitute an optimization or relax validation.

### Individual native TF computed features (#80)

When independent auditing is opt-in profiled, the native `_precompute()` call is further split into per-Text-Fabric-computed-feature `Data.load` timings for the fixed Text-Fabric 13.1.0 internal feature inventory: `levels`, `order`, `rank`, `levUp`, `levDown`, `characters`, `boundary`, `sections`, `structure`. Only computed features genuinely invoked by upstream Text-Fabric receive a timing entry; conditional features may be absent, and one feature can have multiple entries when Text-Fabric rechecks dependencies. Treat each entry as a native invocation, not an exclusive algorithm runtime: a parent computed-feature load can contain a nested dependency load. For an informative ranking, report significant calls individually or aggregate with explicit awareness of nesting. The profile records only these allowlisted internal code names, wall/CPU clocks and process high-water RSS; it never contains corpus feature text or private source paths. Individual timers are **included** in the outer native precompute timer and must not be double counted. These opt-in per-instance wrappers forward genuine `Data.load` calls unchanged and restore method lookup on errors. The complete source-only tf-build validation and independent source/TF semantic conservation still run separately. This is attribution, not a benchmarked speedup.
