"""Issue #70 RED: enforce a bounded read at the actual fingerprint file boundary."""

from __future__ import annotations

from pathlib import Path
from types import TracebackType
from typing import IO, Any, cast

import pytest

from oraec_tf import tf_fingerprints
from oraec_tf.tf_fingerprints import FingerprintError, hash_tf_feature


class _GuardedBinaryReader:
    """Proxy the real feature bytes; reject every unbounded header read."""

    def __init__(self, stream: IO[Any], sizes: list[int]) -> None:
        self.stream = stream
        self.sizes = sizes
        self.consumed_header = 0

    def __enter__(self) -> _GuardedBinaryReader:
        self.stream.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.stream.__exit__(exc_type, exc, traceback)

    def readline(self, size: int = -1) -> bytes:
        self.sizes.append(size)
        assert 0 < size <= tf_fingerprints.HEADER_LIMIT + 1, (
            "unbounded header read or budget overshoot"
        )
        assert size == tf_fingerprints.HEADER_LIMIT - self.consumed_header + 1, (
            "header read does not respect remaining byte budget"
        )
        chunk = cast(bytes, self.stream.readline(size))
        self.consumed_header += len(chunk)
        return chunk

    def read(self, size: int = -1) -> bytes:
        assert 0 < size <= 1024 * 1024, "unbounded feature body read"
        return cast(bytes, self.stream.read(size))


@pytest.mark.parametrize("newline", [b"\n", b"\r\n"])
def test_authentic_header_reads_are_explicitly_bounded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, newline: bytes,
) -> None:
    path = tmp_path / "feature.tf"
    path.write_bytes(
        newline.join([
            b"@node", b"@valueType=str",
            b"@dateWritten=2026-10-11T08:00:00+00:00Z",
            b"", b"1\tword", b"",
        ])
    )
    expected = hash_tf_feature(path)
    original_open = Path.open
    observed: list[int] = []

    def guarded_open(file: Path, *args: Any, **kwargs: Any) -> _GuardedBinaryReader:
        assert file == path
        return _GuardedBinaryReader(original_open(file, *args, **kwargs), observed)

    monkeypatch.setattr(Path, "open", guarded_open)
    assert hash_tf_feature(path) == expected
    assert len(observed) == 4
    assert observed[0] == tf_fingerprints.HEADER_LIMIT + 1


@pytest.mark.parametrize("oversize_first_line", [False, True])
def test_unterminated_oversize_metadata_cannot_be_read_without_a_cap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, oversize_first_line: bool,
) -> None:
    path = tmp_path / "hostile.tf"
    prefix = b"" if oversize_first_line else b"@node\n@description="
    path.write_bytes(prefix + b"x" * (tf_fingerprints.HEADER_LIMIT + 1))
    original_open = Path.open
    observed: list[int] = []

    def guarded_open(file: Path, *args: Any, **kwargs: Any) -> _GuardedBinaryReader:
        assert file == path
        return _GuardedBinaryReader(original_open(file, *args, **kwargs), observed)

    monkeypatch.setattr(Path, "open", guarded_open)
    with pytest.raises(FingerprintError, match="oversized"):
        hash_tf_feature(path)
    assert len(observed) == (1 if oversize_first_line else 2)
    assert all(0 < size <= tf_fingerprints.HEADER_LIMIT + 1 for size in observed)


@pytest.mark.parametrize("newline", [b"\n", b"\r\n"])
def test_header_limit_accepts_exact_bytes_and_rejects_one_fewer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, newline: bytes,
) -> None:
    path = tmp_path / "boundary.tf"
    header = newline.join([
        b"@node", b"@dateWritten=2026-10-11T08:00:00+00:00Z", b"", b"",
    ])
    path.write_bytes(header + b"1\tword" + newline)
    monkeypatch.setattr(tf_fingerprints, "HEADER_LIMIT", len(header))
    assert len(hash_tf_feature(path)[1]) == 64
    monkeypatch.setattr(tf_fingerprints, "HEADER_LIMIT", len(header) - 1)
    with pytest.raises(FingerprintError, match="oversized"):
        hash_tf_feature(path)
