"""RED-first regression tests for bounded mandatory TF node-feature reads (#72)."""

from __future__ import annotations

from pathlib import Path
from types import TracebackType
from typing import IO, Any, cast

import pytest

from oraec_tf import tf_count_probe
from oraec_tf.tf_count_probe import ProbeError, probe_tf_counts


def _features(root: Path, newline: str = "\n") -> None:
    files = {
        "otype.tf": [
            "@node", "@valueType=str", "", "1-3\tword", "4\tsentence", "5\ttext", "",
        ],
        "token_id.tf": [
            "@node", "@valueType=str", "", "1\toraec1-1-1", "2\toraec1-1-2", "",
        ],
    }
    for name, lines in files.items():
        (root / name).write_bytes(newline.join(lines).encode("utf-8"))


class _GuardedReader:
    """Wrap the real text file, failing on any unbounded line read/iteration."""

    def __init__(self, stream: IO[Any], sizes: list[int]) -> None:
        self.stream = stream
        self.sizes = sizes
        self.header_size = 0
        self.in_header = True

    def __enter__(self) -> _GuardedReader:
        self.stream.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.stream.__exit__(exc_type, exc, traceback)

    def __iter__(self) -> Any:
        raise AssertionError("unbounded file iteration in count probe")

    def readline(self, size: int = -1) -> str:
        assert size > 0, "unbounded readline in count probe"
        expected = (
            tf_count_probe.HEADER_LIMIT - self.header_size + 1
            if self.in_header else tf_count_probe.ROW_LIMIT + 1
        )
        assert size == expected, "readline ignored remaining header/row budget"
        value = cast(str, self.stream.readline(size))
        self.sizes.append(size)
        if self.in_header:
            self.header_size += len(value)
            if value in ("\n", "\r\n"):
                self.in_header = False
        return value


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_real_node_feature_streams_have_only_bounded_reads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, newline: str,
) -> None:
    _features(tmp_path, newline)
    expected = probe_tf_counts(tmp_path)
    assert expected == {
        "texts": 1, "sentences": 1, "tokens": 2,
        "technical_anchors": 1, "slots": 3, "cr_occurrences": 0,
    }
    original = Path.open
    seen: list[int] = []

    def guarded_open(path: Path, *args: Any, **kwargs: Any) -> _GuardedReader:
        assert path.name in {"otype.tf", "token_id.tf"}
        return _GuardedReader(original(path, *args, **kwargs), seen)

    monkeypatch.setattr(Path, "open", guarded_open)
    assert probe_tf_counts(tmp_path) == expected
    assert len(seen) >= 12


@pytest.mark.parametrize("attack", ["marker", "metadata", "body"])
def test_malicious_unterminated_line_is_capped_before_parsing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, attack: str,
) -> None:
    _features(tmp_path)
    monkeypatch.setattr(tf_count_probe, "HEADER_LIMIT", 128)
    monkeypatch.setattr(tf_count_probe, "ROW_LIMIT", 128)
    path = tmp_path / "otype.tf"
    if attack == "marker":
        raw = b"@node" + b"x" * 130
    elif attack == "metadata":
        raw = b"@node\n@description=" + b"x" * 130
    else:
        raw = b"@node\n@valueType=str\n\n1\t" + b"x" * 130
    path.write_bytes(raw)
    original = Path.open
    seen: list[int] = []

    def guarded_open(file: Path, *args: Any, **kwargs: Any) -> _GuardedReader:
        return _GuardedReader(original(file, *args, **kwargs), seen)

    monkeypatch.setattr(Path, "open", guarded_open)
    with pytest.raises(ProbeError, match="oversized"):
        probe_tf_counts(tmp_path)
    assert seen and all(0 < size <= 129 for size in seen)


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_header_exact_character_budget_is_accepted_then_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, newline: str,
) -> None:
    _features(tmp_path, newline)
    header = newline.join(["@node", "@valueType=str", "", ""])
    monkeypatch.setattr(tf_count_probe, "HEADER_LIMIT", len(header))
    assert probe_tf_counts(tmp_path)["tokens"] == 2
    monkeypatch.setattr(tf_count_probe, "HEADER_LIMIT", len(header) - 1)
    with pytest.raises(ProbeError, match="oversized"):
        probe_tf_counts(tmp_path)
