"""Experimental fail-closed source-only Text-Fabric node census (issue #64).

This reader is *not* a TF replacement or a release validation shortcut.
The opt-in profiler compares it with the existing real Fabric result after
tf-build has already exhaustively loaded every raw .tf feature. It reads only
the documented @node text feature format, never binary caches or source JSON.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

from .text_codec import NODE_TYPES

_INT = re.compile(r"[1-9][0-9]*\Z")
_ALLOWED_TYPES = NODE_TYPES | {"cr_occurrence"}


class ProbeError(ValueError):
    """A source .tf census is missing, malformed, or ambiguous."""


def _span(spec: str, next_implicit: int) -> tuple[tuple[tuple[int, int], ...], int]:
    """Decode ordered node specs (including implicit nodes and inclusive ranges)."""
    if spec == "":
        return ((next_implicit, next_implicit),), next_implicit + 1
    spans: list[tuple[int, int]] = []
    previous = 0
    for item in spec.split(","):
        parts = item.split("-")
        if not 1 <= len(parts) <= 2 or any(_INT.fullmatch(p) is None for p in parts):
            raise ProbeError(f"invalid source .tf node specification: {spec!r}")
        start = int(parts[0])
        stop = start if len(parts) == 1 else int(parts[1])
        if stop < start or start <= previous:
            raise ProbeError(f"overlapping or reversed node specification: {spec!r}")
        spans.append((start, stop))
        previous = stop
    return tuple(spans), max(stop for _start, stop in spans) + 1


def _rows(path: Path) -> Iterator[tuple[tuple[tuple[int, int], ...], str]]:
    """Read only two particular TF node features with strict fail-closed syntax."""
    if path.is_symlink() or not path.is_file():
        raise ProbeError(f"missing or symlinked source feature: {path.name}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        first = handle.readline().rstrip("\n")
        if first != "@node":
            raise ProbeError(f"{path.name}: not a native node feature")
        valid_type = False
        for line in handle:
            if "\r" in line:
                raise ProbeError(f"{path.name}: literal unescaped CR")
            stripped = line.rstrip("\n")
            if not stripped:
                break
            if not stripped.startswith("@"):
                raise ProbeError(f"{path.name}: invalid feature header")
            if stripped == "@valueType=str":
                valid_type = True
        else:
            raise ProbeError(f"{path.name}: missing feature header separator")
        if not valid_type:
            raise ProbeError(f"{path.name}: expected string node feature")
        previous = 0
        next_implicit = 1
        had_rows = False
        for line in handle:
            if "\r" in line:
                raise ProbeError(f"{path.name}: raw CR outside TF escaping contract")
            fields = line.rstrip("\n").split("\t")
            if len(fields) == 1:
                spec, value = "", fields[0]
            elif len(fields) == 2 and fields[0]:
                spec, value = fields
            else:
                raise ProbeError(f"{path.name}: unexpected node feature columns")
            spans, next_implicit = _span(spec, next_implicit)
            if spans[0][0] <= previous:
                raise ProbeError(f"{path.name}: duplicate or out-of-order node assignment")
            previous = spans[-1][1]
            had_rows = True
            yield spans, value
        if not had_rows:
            raise ProbeError(f"{path.name}: source feature contains no data")


def probe_tf_counts(directory: str | Path) -> dict[str, int]:
    """Count exact TF node identities without loading its millions of oslots.

    Intentionally strict: this is a measured candidate for a *future* fast
    reconciliation path, never a way to skip tf-build's complete source load.
    """
    root = Path(directory)
    otype = _rows(root / "otype.tf")
    tokens = _rows(root / "token_id.tf")
    counts: dict[str, int] = {kind: 0 for kind in _ALLOWED_TYPES}
    word_end = 0
    for spans, value in otype:
        if value not in _ALLOWED_TYPES:
            raise ProbeError(f"otype contains unknown native node type: {value!r}")
        size = sum(b - a + 1 for a, b in spans)
        counts[value] += size
        if value == "word":
            # Under TF's slot contract words occupy precisely nodes 1..N.
            if spans[0][0] != word_end + 1:
                raise ProbeError("otype word slots are not contiguous")
            for start, stop in spans:
                if start != word_end + 1:
                    raise ProbeError("otype word slot range contains a gap")
                word_end = stop
    if word_end < 1:
        raise ProbeError("otype contains no word slots")
    real_tokens = 0
    for spans, _value in tokens:
        for start, stop in spans:
            if start < 1 or stop > word_end:
                raise ProbeError("token_id assigned outside actual word slots")
            real_tokens += stop - start + 1
    if real_tokens > counts["word"]:
        raise ProbeError("token_id feature contains duplicate/missing word identities")
    return {
        "texts": counts["text"],
        "sentences": counts["sentence"],
        "tokens": real_tokens,
        "technical_anchors": counts["word"] - real_tokens,
        "slots": counts["word"],
        "cr_occurrences": counts["cr_occurrence"],
    }
