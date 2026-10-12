# Actual ORAEC corpus vs Context-Fabric .cfm — 2026-10-12 (#84)

## Evidence and immutability

[Successful exact-head benchmark workflow 38255959052](https://github.com/alexsosn/ORAEC-TF/actions/runs/38255959052); provenance-only downloadable GitHub Actions artifact **11750668606**, containing `context-fabric-benchmark.json`, `graph-conservation.json`, full native conversion and independent audit timings and standard advanced-app smoke. ORAEC PR #86 benchmark implementation head `9ed3a34bb7129cece56ad8eeb9e4a093f20150e0`; raw source exact revision `b83a0ee5fae27a40d4c0a2a9a8c9c2973d45e9cd`, Context-Fabric `dd54b73255d19f9ce230e7785d391106f4b94df2` (0.5.7), original unpatched Text-Fabric 13.1.0, Python **3.13.16** on GitHub Actions Linux. Same runner; each measured stage launched as a *fresh Python process*. Processes shared Linux page cache, so these are **warm-cache**, not cold-boot measurements.

Before compiled experimentation, complete immutable ORAEC raw source converted and checked by original `tf-build` source-only validator and separate independent raw-source→native TF graph audit. The known independent canonical SHA-256 commitment over all **65** timestamp-neutral TF feature digests equals `abd68a103f13407f48824cebb7516cb7187f98916f9d74f60d90b2d8cf622e5b`; total source TF output **105,254,838 bytes**. Exactly 13,026 texts, 101,796 sentences, 815,026 tokens + 3 technical anchors, 998,775 Text-Fabric nodes, 2,930 native CR occurrences. Standard advanced TF app passed. Context-Fabric compiled source inventory contains all **62** non-warp/config feature names and the benchmark explicitly confirms the mmap `.cfm` path, never silent `.tf` fallback.

## Measured timings and RSS

| Stage | Wall seconds | CPU seconds | Linux process peak RSS during stage | Notes |
|---|---:|---:|---:|---|
| Native Text-Fabric `Fabric.loadAll()` (warm `.tf` cache) | **4.4963** | 4.4959 | **2,977,676 KiB (2.840 GiB)** | Full features, one fresh process |
| Context-Fabric `Compiler(...).compile()` from raw `.tf` | **191.8183** | 191.7977 | **6,339,052 KiB (6.045 GiB)** | One-time; original slow Python `levUp` still computed |
| Context-Fabric first compiled `Fabric.loadAll()` | **5.0226** | 5.0447 | **718,060 KiB (0.685 GiB)** | Confirmed mmap CFM |
| Context-Fabric fresh-process compiled reload #2 | **5.0013** | 5.0211 | **717,808 KiB (0.685 GiB)** | Warm OS page cache |
| Context-Fabric fresh-process compiled reload #3 | **4.9675** | 4.9870 | **719,416 KiB (0.686 GiB)** | Warm OS page cache |

Compiled `.cfm` occupies **814,861,763 bytes (777.1 MiB)** across **235 files** versus 105.3 MB of source `.tf` files (**7.74x storage expansion**, not counting native hidden `.tf` pickle caches). Building the CFM snapshot is therefore significantly more expensive than simply loading an already warm native TF cache. Compared to warm native TF, Context-Fabric's full-feature repeated load is approximately **11% slower** on this ORAEC run, not faster; the meaningful benefit is **75.9% lower peak loading process RSS** (~4.15x less RAM). One native timing and three CFM timings do **not** establish statistical speed differences. Context-Fabric also offers mmap sharing across worker processes, not measured here.

The process peak memory after **exhaustively hashing the loaded node graph** was 3,028,928 KiB (native) versus 969,304 KiB (first CF); hashing itself allocates memory and is outside the `loadAll` timing.

## Semantic equivalence / limits

An independent streaming SHA-256 covering **every one of 998,775 nodes' otype, every non-slot ordered oslots sequence, and every ordered `levUp` embedding tuple** matches perfectly:

`c45f61ccea35500b23875843bd016a9f554cd0bc1f908f9abb7a3cb0b9b3349e`

CF retained 13,026 texts, 101,796 sentences, 2,930 native CR nodes; all 62 expected node/edge feature *names* were present in compiled metadata, and `_loaded_from_cfm` was true. **This establishes full structural equivalence, not byte-for-byte parity of all 62 user-defined non-warp feature *values***; that still requires its own exact comparison before production adoption. A .cfm cache is a compiled derivative and must not replace the independently validated raw-source and native TF truth.

## Interpretation / next action

Context-Fabric **already solves repeated heavy graph precomputation** by precompiling to CSR/mmap and significantly reduces loaded-memory cost, but **does not speed up initial `levUp` compilation** (its source still uses Text-Fabric's Python set intersections). For ORAEC-TF release readiness, retain the original pinned TF conversion and independent source validation; do not make `.cfm` mandatory. For multi-worker browsing or memory-constrained workloads, optional Context-Fabric cache is promising. The standalone [Text-Fabric fork PR #1](https://github.com/alexsosn/text-fabric/pull/1) remains a low-priority optional initial-compute optimization (one prior paired observation ~7.5% shorter), not a prerequisite for ORAEC or a magic 10x ORAEC startup speedup. Future adoption must test all 62 feature value/parity, source-to-cache freshness and concurrent-worker memory/latency.
