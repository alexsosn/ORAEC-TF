"""Streaming raw and timestamp-neutral hashes for authentic Text-Fabric features.

Only one *valid header* @dateWritten metadata line is excluded from the
semantic digest. Everything else (node identities, edge values, user metadata,
newlines, escaped source text) remains byte-for-byte in the canonical input.
The emitted .tf file is never changed. This is an artifact fingerprint, not
a replacement for source-to-graph semantic conservation.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from pathlib import Path

# Text-Fabric 13.1's UTC-aware utcnow().isoformat() appends "+00:00Z".
# Also support the historically naive ISO timestamp ending in a plain "Z".
STAMP = re.compile(
    rb"@dateWritten=(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\+00:00)?Z)\n\Z"
)
HEADER_LIMIT = 4 * 1024 * 1024


class FingerprintError(ValueError):
    """An untrusted or malformed Text-Fabric feature cannot be canonicalized."""


def hash_tf_feature(path: str | Path) -> tuple[str, str]:
    """Return (raw_sha256, semantic_sha256), preserving all non-clock bytes.

    Parse the real TF @node/@edge/@config header, not arbitrary occurrences of
    the timestamp-like text in the feature body. A missing, repeated, malformed,
    or non-UTC date field must never silently produce a semantic fingerprint.
    Read the feature body in blocks to bound memory for the complete corpus.
    """
    feature = Path(path)
    if feature.is_symlink() or not feature.is_file() or feature.suffix != ".tf":
        raise FingerprintError(f"missing, symlinked or non-TF feature: {feature}")
    raw = hashlib.sha256()
    canonical = hashlib.sha256()
    try:
        with feature.open("rb") as stream:
            first = stream.readline()
            if first not in (b"@node\n", b"@edge\n", b"@config\n"):
                raise FingerprintError(f"{feature.name}: unrecognized TF feature type")
            raw.update(first)
            canonical.update(first)
            seen_clock = False
            header_size = len(first)
            while True:
                line = stream.readline()
                header_size += len(line)
                if header_size > HEADER_LIMIT:
                    raise FingerprintError(f"{feature.name}: oversized or unterminated header")
                if line == b"":
                    raise FingerprintError(f"{feature.name}: missing header/body separator")
                raw.update(line)
                if line == b"\n":
                    if not seen_clock:
                        raise FingerprintError(f"{feature.name}: missing @dateWritten")
                    canonical.update(line)
                    break
                if (
                    not line.endswith(b"\n")
                    or b"\r" in line
                    or not line.startswith(b"@")
                ):
                    raise FingerprintError(f"{feature.name}: malformed TF metadata")
                try:
                    line.decode("utf-8")
                except UnicodeDecodeError as exc:
                    raise FingerprintError(f"{feature.name}: invalid UTF-8 metadata") from exc
                if line.startswith(b"@dateWritten"):
                    if seen_clock:
                        raise FingerprintError(f"{feature.name}: duplicate @dateWritten")
                    match = STAMP.fullmatch(line)
                    if match is None:
                        raise FingerprintError(f"{feature.name}: malformed @dateWritten")
                    clock = match.group(1).decode("ascii")
                    suffix = "+00:00Z" if clock.endswith("+00:00Z") else "Z"
                    try:
                        parsed = datetime.strptime(
                            clock[: -len(suffix)], "%Y-%m-%dT%H:%M:%S"
                        )
                    except ValueError as exc:
                        raise FingerprintError(f"{feature.name}: invalid UTC @dateWritten") from exc
                    if parsed.strftime("%Y-%m-%dT%H:%M:%S") + suffix != clock:
                        raise FingerprintError(f"{feature.name}: noncanonical @dateWritten")
                    seen_clock = True
                else:
                    canonical.update(line)
            while block := stream.read(1024 * 1024):
                raw.update(block)
                canonical.update(block)
    except OSError as exc:
        raise FingerprintError(f"{feature.name}: unreadable TF feature") from exc
    return raw.hexdigest(), canonical.hexdigest()
