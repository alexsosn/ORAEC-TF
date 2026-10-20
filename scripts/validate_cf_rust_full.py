"""Complete ORAEC native TF vs Rust Context-Fabric 0.6.0rc1 feature parity.

Called only in a dedicated Python >=3.13 acceptance workflow, after the
original independently audited pinned-source native Text-Fabric conversion.
Emits hashes, counts and timings only, never source text/corpus data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from importlib.metadata import version
from pathlib import Path
from typing import Any

from oraec_tf.cf_rust_parity import compare_native_and_rust

EXPECTED_VERSION = "0.6.0rc1"
EXPECTED_NODE_COUNT = 998775
EXPECTED_SLOTS = 815029
EXPECTED_TEXTS = 13026
EXPECTED_SENTENCES = 101796
EXPECTED_CR_OCCURRENCES = 2930
EXPECTED_NODE_EDGE_FEATURES = 62


def full_parity(tf_dir: Path, schema_path: Path) -> dict[str, Any]:
    from cfabric import Fabric as RustFabric  # type: ignore[import-not-found]
    from tf.fabric import Fabric as NativeFabric

    if version("context-fabric") != EXPECTED_VERSION:
        raise ValueError("context-fabric version not pinned to the tested Rust RC")
    schema: dict[str, Any] = json.loads(schema_path.read_text(encoding="utf-8"))
    schema_nodes = {
        name
        for spec in schema["nodeTypes"].values()
        for name in spec["features"]
    }
    schema_edges = set(schema["edgeFeatures"])
    files = sorted(
        path for path in tf_dir.glob("*.tf") if path.is_file()
    )
    inventory = {path.stem for path in files}
    if len(inventory) != EXPECTED_NODE_EDGE_FEATURES + 3:
        raise ValueError(f"full source inventory changed: {len(inventory)}")
    required = {"otype", "oslots", "otext"}
    if not required <= inventory:
        raise ValueError("missing standard Text-Fabric warp/config")
    feature_names = inventory - required
    if feature_names - (schema_nodes | schema_edges):
        raise ValueError("unmodeled TF feature in full corpus")
    node_features = feature_names & schema_nodes
    edge_features = feature_names & schema_edges
    if node_features & edge_features:
        raise ValueError("ambiguous feature type in frozen schema")
    if len(node_features) + len(edge_features) != EXPECTED_NODE_EDGE_FEATURES:
        raise ValueError("native feature inventory mismatch")
    original_hashes = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in files
    }

    t0 = time.perf_counter()
    native = NativeFabric(locations=str(tf_dir), silent="deep").loadAll(silent="deep")
    native_seconds = time.perf_counter() - t0
    if not native:
        raise ValueError("Text-Fabric could not read original ORAEC features")
    t1 = time.perf_counter()
    compiled = RustFabric(locations=str(tf_dir), silent="deep").loadAll(silent="deep")
    compile_plus_first_seconds = time.perf_counter() - t1
    if not compiled:
        raise ValueError("Rust Context-Fabric failed full load")
    if not list((tf_dir / ".cfr" / "4").glob("*")):
        raise ValueError("Rust cache .cfr/4 absent after first load")
    assert original_hashes == {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in files
    }, "Rust cache compile mutated raw Text-Fabric source features"
    t2 = time.perf_counter()
    reloaded = RustFabric(locations=str(tf_dir), silent="deep").loadAll(silent="deep")
    warm_rust_seconds = time.perf_counter() - t2
    if not reloaded:
        raise ValueError("Rust Context-Fabric could not reload from compiled cache")

    for api in (native, compiled, reloaded):
        if api.F.otype.maxNode != EXPECTED_NODE_COUNT:
            raise ValueError("incompatible ORAEC node population")
        if api.F.otype.maxSlot != EXPECTED_SLOTS:
            raise ValueError("incompatible ORAEC slot population")
        if len(api.F.otype.s("text")) != EXPECTED_TEXTS:
            raise ValueError("missing ORAEC texts")
        if len(api.F.otype.s("sentence")) != EXPECTED_SENTENCES:
            raise ValueError("missing ORAEC sentences")
        if len(api.F.otype.s("cr_occurrence")) != EXPECTED_CR_OCCURRENCES:
            raise ValueError("native CR occurrences were not conserved")

    t3 = time.perf_counter()
    feature_hashes = compare_native_and_rust(
        native, reloaded,
        node_features=node_features,
        edge_features=edge_features,
    )
    full_value_comparison_seconds = time.perf_counter() - t3
    if len(feature_hashes) != EXPECTED_NODE_EDGE_FEATURES:
        raise ValueError("incomplete node/edge value parity proof")

    # Compare warp and slots for every original node. The two APIs may use
    # different internal storage but must expose the same TF node identities.
    for n in range(1, EXPECTED_NODE_COUNT + 1):
        if native.F.otype.v(n) != reloaded.F.otype.v(n):
            raise ValueError(f"otype changed at TF node {n}")
        if n > EXPECTED_SLOTS and tuple(native.E.oslots.s(n)) != tuple(
            reloaded.E.oslots.s(n)
        ):
            raise ValueError(f"oslots changed at TF node {n}")

    query = "text oraec_id=oraec1"
    native_rows = {tuple(x) for x in native.S.search(query, silent="deep")}
    rust_rows = {tuple(x) for x in reloaded.S.search(query, silent="deep")}
    if not native_rows or native_rows != rust_rows:
        raise ValueError("researcher ORAEC text search results diverged")
    cache_size = sum(
        p.stat().st_size for p in (tf_dir / ".cfr" / "4").rglob("*") if p.is_file()
    )
    return {
        "ok": True,
        "backend": EXPECTED_VERSION,
        "node_count": EXPECTED_NODE_COUNT,
        "slots": EXPECTED_SLOTS,
        "texts": EXPECTED_TEXTS,
        "sentences": EXPECTED_SENTENCES,
        "cr_occurrences": EXPECTED_CR_OCCURRENCES,
        "features": feature_hashes,
        "native_load_seconds": native_seconds,
        "rust_compile_and_first_load_seconds": compile_plus_first_seconds,
        "rust_cached_load_seconds": warm_rust_seconds,
        "feature_comparison_seconds": full_value_comparison_seconds,
        "compiled_cache_bytes": cache_size,
        "search_result_count": len(native_rows),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("tf_dir", type=Path)
    parser.add_argument("--schema", type=Path, default=Path("schema/core.json"))
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    result = full_parity(args.tf_dir, args.schema)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "ok": result["ok"], "backend": result["backend"],
        "count": len(result["features"]),
        "cache_bytes": result["compiled_cache_bytes"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
