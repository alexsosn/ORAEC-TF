"""Full pinned ORAEC native Text-Fabric vs Context-Fabric .cfm benchmark.

All measured stages run in *fresh processes*. Only provenance hashes/counts,
timings, CFM storage size and peak process RSS are written; no corpus payload
is saved. This script is never invoked by production conversion or auditing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import subprocess
import sys
import time
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

def process_peak_rss_kib() -> int | None:
    """Linux process high-water RSS, not incremental phase allocation."""
    if not sys.platform.startswith("linux"):
        return None
    import resource

    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


EXPECTED_SOURCE_REVISION = "b83a0ee5fae27a40d4c0a2a9a8c9c2973d45e9cd"
EXPECTED_CONTEXT_FABRIC_REVISION = "dd54b73255d19f9ce230e7785d391106f4b94df2"
EXPECTED_COUNTS = {
    "texts": 13026, "sentences": 101796, "tokens": 815026,
    "technical_anchors": 3, "slots": 815029,
}
EXPECTED_NODES = 998775
EXPECTED_CR_OCCURRENCES = 2930


def digest_graph(
    *,
    max_slot: int,
    max_node: int,
    node_type: Callable[[int], str | None],
    node_slots: Callable[[int], Iterable[int]],
    node_parents: Callable[[int], Iterable[int]],
) -> str:
    """SHA256 of ALL ordered types, slot memberships, and levUp tuples.

    Length-prefix every sequence to disambiguate structure and retain parent
    ordering. Stable across native tuple and CF numpy/CSR-backed objects.
    """
    h = hashlib.sha256()
    h.update(struct.pack("<QQ", max_slot, max_node))
    for node in range(1, max_node + 1):
        typ = node_type(node)
        if typ is None:
            raise ValueError(f"missing otype at node {node}")
        encoded = str(typ).encode("utf-8")
        h.update(struct.pack("<Q", len(encoded)))
        h.update(encoded)
        if node > max_slot:
            slots = tuple(int(n) for n in node_slots(node))
            h.update(struct.pack("<Q", len(slots)))
            for n in slots:
                h.update(struct.pack("<Q", n))
        parents = tuple(int(n) for n in node_parents(node))
        h.update(struct.pack("<Q", len(parents)))
        for n in parents:
            h.update(struct.pack("<Q", n))
    return h.hexdigest()


def verify_compiled_metadata(meta: dict[str, Any], expected: set[str]) -> None:
    features = meta.get("features", {})
    actual = set(features.get("node", ())) | set(features.get("edge", ()))
    if actual != expected:
        raise ValueError(
            "compiled feature inventory mismatch: "
            f"missing={sorted(expected - actual)} extra={sorted(actual - expected)}"
        )


def verify_equivalence(native: dict[str, Any], compiled: dict[str, Any]) -> None:
    if not compiled.get("loaded_from_cfm"):
        raise ValueError("compiled data did not load from .cfm mmap")
    for field in (
        "fingerprint", "max_slot", "max_node", "feature_names",
        "texts", "sentences", "cr_occurrences",
    ):
        if native[field] != compiled[field]:
            raise ValueError(f"native-vs-CFM {field} mismatch")


def _source_features(tf_dir: Path) -> set[str]:
    result = {
        path.stem for path in tf_dir.glob("*.tf")
        if path.is_file() and not path.name.startswith(".")
        and path.stem not in {"otype", "oslots", "otext"}
        and not path.stem.startswith("otext@")
    }
    if len(result) < 50:
        raise ValueError(f"expected full ORAEC feature inventory, got {len(result)}")
    return result


def _measure_loaded_graph(
    tf_dir: Path, *, backend: str, fingerprint: bool
) -> dict[str, Any]:
    if backend == "native":
        from tf.fabric import Fabric
        fabric = Fabric(locations=str(tf_dir), silent="deep")
    elif backend == "cfm":
        from cfabric.core.fabric import Fabric
        fabric = Fabric(locations=str(tf_dir), silent="deep")
    else:
        raise ValueError(f"unsupported benchmark backend {backend}")
    t0 = time.perf_counter()
    c0 = time.process_time()
    api = fabric.loadAll(silent="deep")
    duration = time.perf_counter() - t0
    cpu = time.process_time() - c0
    if not api:
        raise RuntimeError(f"{backend} Fabric.loadAll failed")
    from_cfm = bool(getattr(fabric, "_loaded_from_cfm", False))
    if backend == "cfm" and not from_cfm:
        raise ValueError("compiled data did not load from .cfm mmap")
    if backend == "native" and from_cfm:
        raise ValueError("native baseline unexpectedly used a CFM cache")

    max_slot = int(api.F.otype.maxSlot)
    max_node = int(api.F.otype.maxNode)
    source_features = sorted(_source_features(tf_dir))
    if max_slot != EXPECTED_COUNTS["slots"] or max_node != EXPECTED_NODES:
        raise ValueError(f"unexpected node counts: {max_slot}, {max_node}")

    result: dict[str, Any] = {
        "backend": backend, "loaded_from_cfm": from_cfm,
        "max_slot": max_slot, "max_node": max_node,
        "feature_names": source_features,
        "load_wall_seconds": duration, "load_cpu_seconds": cpu,
        "load_process_peak_rss_kib": process_peak_rss_kib(),
    }
    if fingerprint:
        start = time.perf_counter()
        if backend == "native":
            get_parents = lambda n: api.C.levUp.data[n - 1]
        else:
            get_parents = lambda n: api.C.levUp[n]
        result["fingerprint"] = digest_graph(
            max_slot=max_slot,
            max_node=max_node,
            node_type=api.F.otype.v,
            node_slots=api.E.oslots.s,
            node_parents=get_parents,
        )
        result["fingerprint_wall_seconds"] = time.perf_counter() - start
        result["texts"] = len(api.F.otype.s("text"))
        result["sentences"] = len(api.F.otype.s("sentence"))
        result["cr_occurrences"] = len(api.F.otype.s("cr_occurrence"))
        if (
            result["texts"] != EXPECTED_COUNTS["texts"]
            or result["sentences"] != EXPECTED_COUNTS["sentences"]
            or result["cr_occurrences"] != EXPECTED_CR_OCCURRENCES
        ):
            raise ValueError("loaded graph counts differ from immutable ORAEC baseline")
    result["process_peak_rss_kib_after_validation"] = process_peak_rss_kib()
    return result


def _cfm_location(tf_dir: Path) -> Path:
    candidates = sorted((tf_dir / ".cfm").glob("*/meta.json"))
    if len(candidates) != 1:
        raise ValueError(f"expected exactly one compiled .cfm metadata file; {candidates}")
    return candidates[0].parent


def _compile(tf_dir: Path) -> dict[str, Any]:
    if (tf_dir / ".cfm").exists():
        raise ValueError("refuse compilation over an existing CFM cache")
    from cfabric.io.compiler import Compiler

    t0 = time.perf_counter()
    c0 = time.process_time()
    if not Compiler(str(tf_dir)).compile():
        raise RuntimeError("Context-Fabric source-to-CFM compilation failed")
    wall = time.perf_counter() - t0
    cpu = time.process_time() - c0
    location = _cfm_location(tf_dir)
    meta = json.loads((location / "meta.json").read_text(encoding="utf-8"))
    verify_compiled_metadata(meta, _source_features(tf_dir))
    files = [x for x in location.rglob("*") if x.is_file()]
    return {
        "compile_wall_seconds": wall, "compile_cpu_seconds": cpu,
        "compile_process_peak_rss_kib": process_peak_rss_kib(),
        "compiled_file_count": len(files),
        "compiled_bytes": sum(x.stat().st_size for x in files),
        "metadata_feature_count": len(_source_features(tf_dir)),
    }


def _child(tf_dir: Path, mode: str, output: Path) -> None:
    if mode == "native":
        result = _measure_loaded_graph(tf_dir, backend="native", fingerprint=True)
    elif mode == "compile":
        result = _compile(tf_dir)
    elif mode == "cfm_verified":
        result = _measure_loaded_graph(tf_dir, backend="cfm", fingerprint=True)
    elif mode == "cfm_reload":
        result = _measure_loaded_graph(tf_dir, backend="cfm", fingerprint=False)
    else:
        raise ValueError(mode)
    output.write_text(json.dumps(result, sort_keys=True) + "\n", encoding="utf-8")


def _stage(tf_dir: Path, stage: str, output: Path) -> dict[str, Any]:
    subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), str(tf_dir),
         "--stage", stage, "--output", str(output)],
        check=True,
    )
    return json.loads(output.read_text(encoding="utf-8"))


def run_benchmark(tf_dir: Path, output: Path) -> dict[str, Any]:
    if not (tf_dir / "otype.tf").is_file():
        raise ValueError("source must contain full native ORAEC .tf files")
    output.parent.mkdir(parents=True, exist_ok=True)
    scratch = output.parent / ".context-fabric-stage-report.json"
    try:
        native = _stage(tf_dir, "native", scratch)
        compiled = _stage(tf_dir, "compile", scratch)
        verified = _stage(tf_dir, "cfm_verified", scratch)
        verify_equivalence(native, verified)
        reloaded = [_stage(tf_dir, "cfm_reload", scratch) for _ in range(2)]
        if any(
            not result.get("loaded_from_cfm")
            or result["max_node"] != native["max_node"]
            or result["feature_names"] != native["feature_names"]
            for result in reloaded
        ):
            raise ValueError("repeated compiled load fell back or lost features")
    finally:
        scratch.unlink(missing_ok=True)
    result = {
        "format": "oraec-cfabric-comparison-v1",
        "source_revision": EXPECTED_SOURCE_REVISION,
        "context_fabric_revision": EXPECTED_CONTEXT_FABRIC_REVISION,
        "python_version": sys.version.split()[0],
        "os_page_cache_caveat": (
            "separate processes but shared warm Linux page cache; "
            "measure native loading, one-time compilation and repeated "
            "compiled loads separately; RSS is per-process high-water"
        ),
        "equivalent_to_native": True,
        "native": native, "compile": compiled,
        "cfm_first_verified_load": verified,
        "cfm_repeated_loads": reloaded,
    }
    output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tf_dir", type=Path)
    parser.add_argument("--stage", choices=("native", "compile", "cfm_verified", "cfm_reload"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.stage:
        _child(args.tf_dir.resolve(), args.stage, args.output.resolve())
    else:
        run_benchmark(args.tf_dir.resolve(), args.output.resolve())
    return 0


if __name__ == "__main__":
    sys.exit(main())
