from __future__ import annotations

import json
from pathlib import Path

from oraec_tf.linecount import analyze_linecount_source


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _fixture(tmp_path: Path) -> Path:
    root = tmp_path / "source"
    root.mkdir()

    _write_json(
        root / "oraec1.json",
        {
            "oraec1": {
                "oraecid": "oraec1",
                "sentences": [
                    {
                        "translation": "",
                        "token": [
                            {"token": "oraec1-1-1", "written_form": "a", "lineCount": " [1]"},
                            {"token": "oraec1-1-2", "written_form": "b", "lineCount": " [1]"},
                            {"token": "oraec1-1-3", "written_form": "c", "lineCount": "[2]"},
                        ],
                    },
                    {
                        "translation": "",
                        "token": [
                            {"token": "oraec1-2-1", "written_form": "d", "lineCount": "[2]"},
                            {"token": "oraec1-2-2", "written_form": "e", "lineCount": " [1]"},
                        ],
                    },
                    {
                        "translation": "",
                        "token": [
                            {"token": "oraec1-3-1", "written_form": "f"},
                            {"token": "oraec1-3-2", "written_form": "g", "lineCount": "folio A"},
                            {"token": "oraec1-3-3", "written_form": "h"},
                        ],
                    },
                ],
                "credits": {"license": "cc-by-sa-4.0", "author": "A", "source": []},
            }
        },
    )

    _write_json(
        root / "oraec2.json",
        {
            "oraec2": {
                "oraecid": "oraec2",
                "sentences": [
                    {
                        "translation": "",
                        "token": [
                            {"token": "oraec2-1-1", "written_form": "x", "lineCount": "[1]"}
                        ],
                    },
                    {
                        "translation": "",
                        "token": [
                            {"token": "oraec2-2-1", "written_form": "y", "lineCount": "   "}
                        ],
                    }
                ],
                "credits": {"license": "cc-by-sa-4.0", "author": "B", "source": []},
            }
        },
    )
    return root


def test_linecount_analysis_distinguishes_exact_and_normalized_labels(
    tmp_path: Path,
) -> None:
    report = analyze_linecount_source(_fixture(tmp_path))

    assert report["counts"]["tokens"] == 10
    assert report["counts"]["with_linecount"] == 8
    assert report["labels"]["exact_distinct"] == 5
    assert report["labels"]["normalized_distinct"] == 4
    assert report["labels"]["trim_changed_occurrences"] == 3
    assert report["labels"]["normalization_collision_count"] == 1
    assert report["labels"]["normalization_collisions"]["[1]"] == [" [1]", "[1]"]


def test_linecount_analysis_measures_runs_and_sentence_crossings(tmp_path: Path) -> None:
    report = analyze_linecount_source(_fixture(tmp_path))

    assert report["runs"]["exact_count"] == 6
    assert report["runs"]["normalized_count"] == 6
    assert report["runs"]["exact_cross_sentence_count"] == 1
    assert report["runs"]["normalized_cross_sentence_count"] == 1
    assert report["runs"]["texts_with_exact_noncontiguous_reuse"] == 1
    assert report["runs"]["texts_with_normalized_noncontiguous_reuse"] == 1
    assert report["sentences"]["with_multiple_exact_runs"] == 2


def test_linecount_analysis_measures_missingness_transitions_and_label_scope(
    tmp_path: Path,
) -> None:
    report = analyze_linecount_source(_fixture(tmp_path))

    assert report["transitions"]["missing_to_present"] == 1
    assert report["transitions"]["present_to_missing"] == 1

    assert report["scope"]["exact_labels_shared_across_texts"] == 1
    assert report["scope"]["max_texts_per_exact_label"] == 2

    assert report["shapes"]["blank"]["occurrences"] == 1
    assert report["shapes"]["bracketed_integer"]["occurrences"] == 6
    assert report["shapes"]["descriptive"]["occurrences"] == 1


def test_linecount_analysis_keeps_representative_contexts(tmp_path: Path) -> None:
    report = analyze_linecount_source(_fixture(tmp_path))

    context = report["examples"]["normalization_collisions"][0]
    assert context["normalized"] == "[1]"
    assert context["exact_values"] == [" [1]", "[1]"]

    crossing = report["examples"]["cross_sentence_runs"][0]
    assert crossing["text"] == "oraec1"
    assert crossing["label"] == "[2]"
    assert crossing["sentences"] == [1, 2]
