"""Opt-in same-process Text-Fabric levUp prototype benchmark (research only).

Run after producing a pinned TF corpus:
python scripts/benchmark_levup_prototype.py build/tf --report levup-benchmark.json

Loads the genuine native Text-Fabric warp graph; does not modify corpus,
production APIs, or the independent source-conservation audit.
"""

from __future__ import annotations

import argparse
import gc
import json
import sys
import time
from pathlib import Path
from typing import Any

from tf.core import prepare
from tf.fabric import Fabric

from oraec_tf.experimental_levup import candidate_superset_levup


def _quiet(_: str) -> None:
    return None


def _rss_highwater_kib() -> int | None:
    """Process high-water RSS, not a per-phase memory allocation delta."""
    if not sys.platform.startswith("linux"):
        return None
    import resource

    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


def _timed(compute: Any) -> tuple[Any, dict[str, float | int | None]]:
    wall = time.perf_counter()
    cpu = time.process_time()
    result = compute()
    return result, {
        "wall_seconds": time.perf_counter() - wall,
        "cpu_seconds": time.process_time() - cpu,
        "process_peak_rss_kib_at_end": _rss_highwater_kib(),
    }


def benchmark(tf_path: Path) -> dict[str, Any]:
    """Use identical native warp data and original TF levUp as exact oracle."""
    fabric = Fabric(locations=str(tf_path), silent="deep")
    # Text-Fabric prepares the entire genuine graph, unchanged, before any
    # experimental computation is invoked.
    api = fabric.load("", silent="deep")
    if not api:
        raise RuntimeError("native Text-Fabric warp graph did not load")
    native_result = fabric.features["__levUp__"].data
    otype = fabric.features["otype"].data
    oslots = fabric.features["oslots"].data
    rank = fabric.features["__rank__"].data

    baseline, native_time = _timed(
        lambda: prepare.levUp(_quiet, _quiet, otype, oslots, rank),
    )
    if baseline != native_result:
        raise RuntimeError("native recalculation disagrees with loaded Text-Fabric")
    # The reference native result remains available in Fabric. Keeping the
    # separate timed native recomputation alive during the candidate step
    # artificially inflates process RSS and risks OOM on the full corpus.
    # Prove reference equality first, then release that redundant copy.
    checked = len(baseline)
    del baseline
    gc.collect()

    proposed, candidate_time = _timed(
        lambda: candidate_superset_levup(_quiet, _quiet, otype, oslots, rank),
    )
    if proposed != native_result:
        raise RuntimeError("candidate-superset levUp changes native TF embeddings")

    return {
        "format": "oraec-levup-research-prototype-v1",
        "equivalent_to_native": True,
        "nodes_checked": checked,
        "native_recomputation": native_time,
        "candidate_superset": candidate_time,
        "timing_caveat": (
            "single same-process order-dependent observation; native load "
            "runs first and may warm caches; RSS is process high-water mark, "
            "not phase allocation; no production speedup claim"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tf_path", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    result = benchmark(args.tf_path)
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.report:
        args.report.write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
