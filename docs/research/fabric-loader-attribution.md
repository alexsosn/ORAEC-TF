# Research: dominating independent Fabric load cost (issue #76)

## Real pinned-source measurements, 2026-10-11

From successful PR #75 writer run [38157185959](https://github.com/alexsosn/ORAEC-TF/actions/runs/38157185959), artifact 11708967139 (actual JSON opened, not guessed from workflow times), Python 3.12.15, Text-Fabric 13.1.0, tf-build 0.1.0.dev0:

- Independent full `Fabric.loadAll()`: **257.900 s** wall, process peak **4,766,492 KiB**.
- Full independent `source_graph_audit` *including* that load: **314.967 s** wall, process peak **5,043,328 KiB**; difference ≈57.067 s for independent source-to-graph tests.
- All 65 TF file semantic and raw SHA-256: **0.161 s** wall.
- Total audit: **315.132 s** wall, process peak **5,043,328 KiB**.
- Converter's earlier `uncached_tf_validation`: **259.551 s** wall. Its own `source_tf_counts` is **0.866 s**; writer and IR ~65.63 s.

The independently audited graph is valid: 13,026 texts, 101,796 sentences, 815,026 actual source tokens, 3 anchors, 2,930 native CR occurrence nodes, 65 TF files hashed. This proves the independent full loader accounts for ~82% of audit elapsed time on that runner, not the effect of one specific feature/phase. No speedup can be claimed yet.

## Exact upstream Text-Fabric 13.1.0 source research

`annotation/text-fabric`, tag v13.1.0, `tf/core/fabric.py` around lines 537–551:

```python
api = self.load("", silent=silent)
allFeatures = self.explore(silent=silent, show=True)
loadableFeatures = allFeatures["nodes"] + allFeatures["edges"]
self.load(loadableFeatures, add=True, silent=silent)
return api
```

`FabricCore.load()` (lines 283ff) first assures `otype`, `oslots`, `otext`, Text-Fabric precomputed structures, then loads requested features. The **initial warp/computed structures** vs **additional node/edge features** could have different time and memory costs. Merely selecting fewer features is **not permitted** until a separate independent equivalence/security demonstration establishes no loss of full loaded-source validation.

ORAEC's `src/oraec_tf/audit_graph.py::audit_basic_graph` currently uses `Fabric(locations=str(output), silent="deep").loadAll(silent="deep")`, then performs independent JSON/TF comparisons. Full `tf-build.validate_tf_artifact(level="all")` runs earlier inside conversion. This creates two distinct graph-validation trust boundaries, and they MUST remain.

A next profiling ticket can instrument Text-Fabric's two **unmodified** `Fabric.load` calls during `loadAll` without replacing `loadAll` itself. An opt-in recorder could time those calls in order, but must be tested with real TF output and never mutate loader arguments/return values. Cache behavior, feature discovery, private load internals and artifacts must be verified. If instrumentation requires invasive monkeypatching, prefer a separately tracked experiment over risking the production gate.

## Research outcome

Prioritize isolating which of the **initial `load("")`/precompute** and **`load(nodes + edges, add=True)`** paths dominates, then measure improvements on comparable full pinned corpus builds. The 0.16s hash phase is irrelevant for speed. Preserve memory accounting's process-lifetime RSS semantics. Never commit source/corpus bytes or semantic sidecars to the repository.

## Actual TF feature inventory and compiled-cache trust

The same `graph-conservation.json` lists 65 `*.tf` files totaling **105,254,838 bytes (100.379 MiB)**, versus a **5,043,328 KiB (~4.81 GiB)** peak audit RSS. Largest raw source features are `cotext_translation.tf` 13.162 MiB, `oslots.tf` 12.123 MiB, `token_id.tf` 11.018 MiB, `translation.tf` 7.876 MiB, `pos.tf` 7.552 MiB and `line_count.tf` 6.652 MiB. Source bytes alone do not explain the roughly 50x memory expansion or which load stage allocates it.

Text-Fabric v13.1.0 `tf/core/data.py::Data.load` checks `.tf` and compiled binary mtimes and may choose compiled binary data; `_readDataBin` at lines 645ff uses `gzip.open` and `pickle.load`. This is an important source-trust and security boundary: **do not** claim that blindly trusting a precompiled `.tfx` cache is a safe speedup, even when it improves wall time. Require source-only validation of all authentic `.tf` and explicit cache integrity/isolation proofs before any optimization that would reuse compiled binaries between the converter and independent audit. The ~258s independent load being nearly as expensive as the ~260s uncached tf-build validation suggests repeated expensive graph loading, but does not prove cache provenance or a specific bottleneck without subphase evidence.
