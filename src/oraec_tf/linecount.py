"""Corpus-wide research helpers for ORAEC lineCount semantics."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

TEXT_FILE_RE = re.compile(r"^oraec(?P<number>\d+)\.json$")
BRACKETED_INTEGER_RE = re.compile(r"^\[\d+\]$")
INTEGER_RE = re.compile(r"^\d+$")


def _shape(label: str) -> str:
    normalized = label.strip()
    if normalized == "":
        return "blank"
    if BRACKETED_INTEGER_RE.fullmatch(normalized):
        return "bracketed_integer"
    if INTEGER_RE.fullmatch(normalized):
        return "integer"
    if (
        len(normalized) >= 2
        and normalized[0] in "[("
        and normalized[-1] in "])"
    ):
        return "bracketed"
    if any(ch.isdigit() for ch in normalized):
        return "contains_digit"
    return "descriptive"


def _text_paths(root: Path) -> list[Path]:
    paths = [
        path
        for path in root.iterdir()
        if path.is_file() and TEXT_FILE_RE.fullmatch(path.name)
    ]

    def number(path: Path) -> int:
        match = TEXT_FILE_RE.fullmatch(path.name)
        assert match is not None
        return int(match.group("number"))

    return sorted(paths, key=number)


def _make_runs(
    tokens: list[dict[str, Any]],
    *,
    normalized: bool,
) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for token in tokens:
        exact = token["lineCount"]
        label = None if exact is None else exact.strip() if normalized else exact

        if label is None:
            current = None
            continue

        if current is not None and current["label"] == label:
            current["end_sentence"] = token["sentence"]
            current["end_token"] = token["token_index"]
            current["sentences"].add(token["sentence"])
            current["token_count"] += 1
            continue

        current = {
            "label": label,
            "start_sentence": token["sentence"],
            "start_token": token["token_index"],
            "end_sentence": token["sentence"],
            "end_token": token["token_index"],
            "sentences": {token["sentence"]},
            "token_count": 1,
        }
        runs.append(current)

    return runs


def _example_context(
    text_id: str,
    sentence: int,
    token_index: int,
    written_form: str | None,
    label: str,
) -> dict[str, Any]:
    return {
        "text": text_id,
        "sentence": sentence,
        "token": token_index,
        "written_form": written_form,
        "lineCount": label,
    }


def analyze_linecount_source(
    root: str | Path,
    *,
    max_examples: int = 12,
) -> dict[str, Any]:
    """Measure how lineCount behaves across an ORAEC source checkout."""
    source = Path(root).resolve()
    if not source.is_dir():
        raise ValueError(f"source directory does not exist: {source}")

    text_paths = _text_paths(source)

    exact_counts: Counter[str] = Counter()
    normalized_counts: Counter[str] = Counter()
    shape_counts: Counter[str] = Counter()
    shape_examples: dict[str, list[dict[str, Any]]] = defaultdict(list)
    exact_texts: dict[str, set[str]] = defaultdict(set)
    normalized_texts: dict[str, set[str]] = defaultdict(set)
    normalized_to_exact: dict[str, set[str]] = defaultdict(set)

    token_count = 0
    with_linecount = 0
    trim_changed_occurrences = 0

    exact_run_count = 0
    normalized_run_count = 0
    exact_cross_sentence_count = 0
    normalized_cross_sentence_count = 0
    texts_with_exact_noncontiguous_reuse = 0
    texts_with_normalized_noncontiguous_reuse = 0
    exact_noncontiguous_labels = 0
    normalized_noncontiguous_labels = 0
    sentences_with_multiple_exact_runs = 0
    sentences_with_multiple_normalized_runs = 0

    within_missing_to_present = 0
    within_present_to_missing = 0
    cross_sentence_missing_to_present = 0
    cross_sentence_present_to_missing = 0

    cross_sentence_examples: list[dict[str, Any]] = []
    exact_reuse_examples: list[dict[str, Any]] = []
    normalized_reuse_examples: list[dict[str, Any]] = []

    for path in text_paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        text_id = path.stem
        record = payload[text_id]
        flattened: list[dict[str, Any]] = []
        sentence_tokens: list[list[dict[str, Any]]] = []

        for sentence_index, sentence in enumerate(record["sentences"], start=1):
            this_sentence: list[dict[str, Any]] = []
            for token_index, token in enumerate(sentence["token"], start=1):
                token_count += 1
                raw = token.get("lineCount")
                label = raw if isinstance(raw, str) else None
                item = {
                    "sentence": sentence_index,
                    "token_index": token_index,
                    "written_form": token.get("written_form"),
                    "lineCount": label,
                }
                flattened.append(item)
                this_sentence.append(item)

                if label is None:
                    continue

                with_linecount += 1
                normalized = label.strip()
                exact_counts[label] += 1
                normalized_counts[normalized] += 1
                exact_texts[label].add(text_id)
                normalized_texts[normalized].add(text_id)
                normalized_to_exact[normalized].add(label)

                if normalized != "" and normalized != label:
                    trim_changed_occurrences += 1

                shape = _shape(label)
                shape_counts[shape] += 1
                if len(shape_examples[shape]) < max_examples:
                    written = token.get("written_form")
                    shape_examples[shape].append(
                        _example_context(
                            text_id,
                            sentence_index,
                            token_index,
                            written if isinstance(written, str) else None,
                            label,
                        )
                    )

            sentence_tokens.append(this_sentence)

            exact_sentence_runs = _make_runs(this_sentence, normalized=False)
            normalized_sentence_runs = _make_runs(this_sentence, normalized=True)
            if len(exact_sentence_runs) > 1:
                sentences_with_multiple_exact_runs += 1
            if len(normalized_sentence_runs) > 1:
                sentences_with_multiple_normalized_runs += 1

            for left, right in zip(this_sentence, this_sentence[1:]):
                left_present = left["lineCount"] is not None
                right_present = right["lineCount"] is not None
                if not left_present and right_present:
                    within_missing_to_present += 1
                elif left_present and not right_present:
                    within_present_to_missing += 1

        for left_sentence, right_sentence in zip(sentence_tokens, sentence_tokens[1:]):
            if not left_sentence or not right_sentence:
                continue
            left_present = left_sentence[-1]["lineCount"] is not None
            right_present = right_sentence[0]["lineCount"] is not None
            if not left_present and right_present:
                cross_sentence_missing_to_present += 1
            elif left_present and not right_present:
                cross_sentence_present_to_missing += 1

        exact_runs = _make_runs(flattened, normalized=False)
        normalized_runs = _make_runs(flattened, normalized=True)
        exact_run_count += len(exact_runs)
        normalized_run_count += len(normalized_runs)

        exact_cross = [run for run in exact_runs if len(run["sentences"]) > 1]
        normalized_cross = [
            run for run in normalized_runs if len(run["sentences"]) > 1
        ]
        exact_cross_sentence_count += len(exact_cross)
        normalized_cross_sentence_count += len(normalized_cross)

        for run in exact_cross:
            if len(cross_sentence_examples) >= max_examples:
                break
            cross_sentence_examples.append(
                {
                    "text": text_id,
                    "label": run["label"],
                    "sentences": sorted(run["sentences"]),
                    "start": [run["start_sentence"], run["start_token"]],
                    "end": [run["end_sentence"], run["end_token"]],
                    "token_count": run["token_count"],
                }
            )

        exact_runs_by_label: dict[str, list[dict[str, Any]]] = defaultdict(list)
        normalized_runs_by_label: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for run in exact_runs:
            exact_runs_by_label[run["label"]].append(run)
        for run in normalized_runs:
            normalized_runs_by_label[run["label"]].append(run)

        exact_reused = {
            label: runs
            for label, runs in exact_runs_by_label.items()
            if len(runs) > 1
        }
        normalized_reused = {
            label: runs
            for label, runs in normalized_runs_by_label.items()
            if len(runs) > 1
        }
        if exact_reused:
            texts_with_exact_noncontiguous_reuse += 1
            exact_noncontiguous_labels += len(exact_reused)
        if normalized_reused:
            texts_with_normalized_noncontiguous_reuse += 1
            normalized_noncontiguous_labels += len(normalized_reused)

        for label, runs in exact_reused.items():
            if len(exact_reuse_examples) >= max_examples:
                break
            exact_reuse_examples.append(
                {
                    "text": text_id,
                    "label": label,
                    "run_count": len(runs),
                    "starts": [
                        [run["start_sentence"], run["start_token"]]
                        for run in runs[:8]
                    ],
                }
            )

        for label, runs in normalized_reused.items():
            if len(normalized_reuse_examples) >= max_examples:
                break
            normalized_reuse_examples.append(
                {
                    "text": text_id,
                    "label": label,
                    "run_count": len(runs),
                    "starts": [
                        [run["start_sentence"], run["start_token"]]
                        for run in runs[:8]
                    ],
                }
            )

    collisions = {
        normalized: sorted(values)
        for normalized, values in sorted(normalized_to_exact.items())
        if len(values) > 1
    }
    exact_shared = {
        label: sorted(texts)
        for label, texts in exact_texts.items()
        if len(texts) > 1
    }
    normalized_shared = {
        label: sorted(texts)
        for label, texts in normalized_texts.items()
        if len(texts) > 1
    }

    shape_names = (
        "blank",
        "bracketed_integer",
        "integer",
        "bracketed",
        "contains_digit",
        "descriptive",
    )
    shapes = {
        name: {
            "occurrences": shape_counts[name],
            "examples": shape_examples.get(name, []),
        }
        for name in shape_names
    }

    return {
        "source": {"path": str(source)},
        "counts": {
            "texts": len(text_paths),
            "tokens": token_count,
            "with_linecount": with_linecount,
            "without_linecount": token_count - with_linecount,
        },
        "labels": {
            "exact_distinct": len(exact_counts),
            "normalized_distinct": len(normalized_counts),
            "trim_changed_occurrences": trim_changed_occurrences,
            "normalization_collision_count": len(collisions),
            "normalization_collisions": collisions,
        },
        "runs": {
            "exact_count": exact_run_count,
            "normalized_count": normalized_run_count,
            "exact_cross_sentence_count": exact_cross_sentence_count,
            "normalized_cross_sentence_count": normalized_cross_sentence_count,
            "texts_with_exact_noncontiguous_reuse": (
                texts_with_exact_noncontiguous_reuse
            ),
            "texts_with_normalized_noncontiguous_reuse": (
                texts_with_normalized_noncontiguous_reuse
            ),
            "exact_noncontiguous_label_instances": exact_noncontiguous_labels,
            "normalized_noncontiguous_label_instances": (
                normalized_noncontiguous_labels
            ),
        },
        "sentences": {
            "with_multiple_exact_runs": sentences_with_multiple_exact_runs,
            "with_multiple_normalized_runs": sentences_with_multiple_normalized_runs,
        },
        "transitions": {
            "missing_to_present": within_missing_to_present,
            "present_to_missing": within_present_to_missing,
            "cross_sentence_missing_to_present": cross_sentence_missing_to_present,
            "cross_sentence_present_to_missing": cross_sentence_present_to_missing,
        },
        "scope": {
            "exact_labels_shared_across_texts": len(exact_shared),
            "normalized_labels_shared_across_texts": len(normalized_shared),
            "max_texts_per_exact_label": max(
                (len(texts) for texts in exact_texts.values()),
                default=0,
            ),
            "max_texts_per_normalized_label": max(
                (len(texts) for texts in normalized_texts.values()),
                default=0,
            ),
        },
        "shapes": shapes,
        "examples": {
            "normalization_collisions": [
                {"normalized": normalized, "exact_values": values}
                for normalized, values in list(collisions.items())[:max_examples]
            ],
            "cross_sentence_runs": cross_sentence_examples,
            "exact_noncontiguous_reuse": exact_reuse_examples,
            "normalized_noncontiguous_reuse": normalized_reuse_examples,
        },
    }


def render_linecount_markdown(report: dict[str, Any]) -> str:
    """Render a compact research summary."""
    counts = report["counts"]
    labels = report["labels"]
    runs = report["runs"]
    sentences = report["sentences"]
    transitions = report["transitions"]
    scope = report["scope"]

    lines = [
        "# ORAEC lineCount research",
        "",
        f"- Texts: **{counts['texts']}**",
        f"- Tokens: **{counts['tokens']}**",
        f"- Tokens with lineCount: **{counts['with_linecount']}**",
        f"- Exact labels: **{labels['exact_distinct']}**",
        f"- Trim-normalized labels: **{labels['normalized_distinct']}**",
        (
            "- Nonblank occurrences changed by trim: "
            f"**{labels['trim_changed_occurrences']}**"
        ),
        (
            "- Normalized labels produced by multiple exact spellings: "
            f"**{labels['normalization_collision_count']}**"
        ),
        f"- Exact contiguous runs: **{runs['exact_count']}**",
        f"- Runs crossing sentence boundaries: **{runs['exact_cross_sentence_count']}**",
        (
            "- Texts reusing an exact label non-contiguously: "
            f"**{runs['texts_with_exact_noncontiguous_reuse']}**"
        ),
        (
            "- Sentences with multiple exact runs: "
            f"**{sentences['with_multiple_exact_runs']}**"
        ),
        (
            "- Within-sentence missing→present transitions: "
            f"**{transitions['missing_to_present']}**"
        ),
        (
            "- Within-sentence present→missing transitions: "
            f"**{transitions['present_to_missing']}**"
        ),
        (
            "- Exact labels shared by multiple texts: "
            f"**{scope['exact_labels_shared_across_texts']}**"
        ),
        (
            "- Normalized labels shared by multiple texts: "
            f"**{scope['normalized_labels_shared_across_texts']}**"
        ),
        "",
        "## Shape classes",
        "",
    ]
    for name, data in report["shapes"].items():
        lines.append(f"- {name}: {data['occurrences']}")

    lines.extend(["", "## Cross-sentence run examples", ""])
    for example in report["examples"]["cross_sentence_runs"]:
        lines.append(
            f"- {example['text']} {example['label']!r}: "
            f"sentences {example['sentences']}"
        )

    lines.append("")
    return "\n".join(lines)
