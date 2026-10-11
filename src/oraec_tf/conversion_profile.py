"""Opt-in, provenance-only phase measurements for the ORAEC conversion pipeline.

No corpus bytes, token strings, paths, or source excerpts are recorded.
Wall and CPU clocks measure phases independently; process RSS is a high-water
mark since process start, NOT a phase-local allocation delta.
"""

from __future__ import annotations

import sys
from collections.abc import Iterator
from contextlib import contextmanager
from importlib.metadata import version
from time import perf_counter, process_time
from typing import Any


def _peak_rss_kib() -> int | None:
    """Return process high-water RSS in KiB only where kernel units are known."""
    if not sys.platform.startswith("linux"):
        return None
    try:
        import resource
        return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    except (ImportError, OSError, ValueError):
        return None


class PhaseRecorder:
    """Track named conversion phases without serializing research semantics."""

    def __init__(self, enabled: bool = False) -> None:
        self.enabled = enabled
        self._start_wall = perf_counter()
        self._start_cpu = process_time()
        self.phases: list[dict[str, Any]] = []

    @contextmanager
    def phase(self, name: str) -> Iterator[None]:
        if not self.enabled:
            yield
            return
        begin_wall = perf_counter()
        begin_cpu = process_time()
        try:
            yield
        finally:
            self.phases.append({
                "name": name,
                "wall_seconds": max(0.0, perf_counter() - begin_wall),
                "cpu_seconds": max(0.0, process_time() - begin_cpu),
                "process_peak_rss_kib_at_end": _peak_rss_kib(),
            })

    def report(self) -> dict[str, Any]:
        return {
            "format": "oraec-convert-phases-v1",
            "environment": {
                "python": ".".join(str(v) for v in sys.version_info[:3]),
                "platform": sys.platform,
                "text_fabric_version": version("text-fabric"),
                "tf_build_version": version("tf-build"),
            },
            "total_wall_seconds": max(0.0, perf_counter() - self._start_wall),
            "total_cpu_seconds": max(0.0, process_time() - self._start_cpu),
            "process_peak_rss_kib_at_end": _peak_rss_kib(),
            "phases": list(self.phases),
        }
