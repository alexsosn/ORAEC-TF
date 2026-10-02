"""Reproducible corpus-wide audit helpers for a local ORAEC source checkout."""

from __future__ import annotations

import csv
import json
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

TEXT_FILE_RE = re.compile(r"^oraec(?P<number>\d+)\.json$")
TOKEN_ID_RE = re.compile(r"^oraec\d+-\d+-\d+$")
GRAMMAR_FIELDS = (
    "pos",
    "name",
    "number",
    "voice",
    "genus",
    "pronoun",
    "numerus",
    "epitheton",
    "morphology",
    "inflection",
    "adjective",
    "particle",
    "adverb",
    "verbalClass",
    "status",
)
CONTROLLED_VOCABULARIES = ("date", "origplace", "objecttype", "location", "material")
TABLE_FILES = (
    "mapping_oraec_trismegistos.csv",
    "mapping_oraec_wikidata.tsv",
    "mapping_oraec_lemmata_vega.tsv",
    "mapping_oraec_karnak.tsv",
    "mapping_oraec_lemmata_karnak.tsv",
    "oraec_hierarchical_path.tsv",
)


def _value_type(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, str):
        return "str"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "dict"
    return type(value).__name__


def _is_empty(value: object) -> bool:
    return value is None or value == "" or value == [] or value == {}


def _observe_fields(stats: dict[str, dict[str, Any]], obj: dict[str, Any]) -> None:
    for key, value in obj.items():
        item = stats.setdefault(
            key,
            {
                "present": 0,
                "empty": 0,
                "types": Counter(),
                "scalar_values": set(),
                "container_sizes": Counter(),
            },
        )
        item["present"] += 1
        value_type = _value_type(value)
        item["types"][value_type] += 1
        if _is_empty(value):
            item["empty"] += 1
        if value_type in {"str", "int", "float", "bool", "null"}:
            item["scalar_values"].add(
                json.dumps(value, ensure_ascii=False, sort_keys=True)
            )
        elif isinstance(value, (list, dict)):
            item["container_sizes"][len(value)] += 1


def _finalize_field_stats(
    stats: dict[str, dict[str, Any]],
    population: int,
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for key, item in sorted(stats.items()):
        scalar_values = sorted(item["scalar_values"])
        result[key] = {
            "present": item["present"],
            "missing": population - item["present"],
            "empty": item["empty"],
            "types": dict(sorted(item["types"].items())),
            "distinct_scalar_values": len(scalar_values),
            "scalar_value_sample": scalar_values[:20],
            "container_size_distribution": {
                str(size): count
                for size, count in sorted(item["container_sizes"].items())
            },
        }
    return result


def _iter_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if ".git" in path.parts:
            continue
        if path.is_file():
            files.append(path)
    return sorted(files)


def _iter_directories(root: Path) -> list[Path]:
    directories: list[Path] = []
    for path in root.rglob("*"):
        if ".git" in path.parts:
            continue
        if path.is_dir():
            directories.append(path)
    return sorted(directories)


def _git_identity(root: Path) -> dict[str, Any]:
    git_dir = root / ".git"
    if not git_dir.exists():
        return {"revision": None, "dirty": None}

    try:
        revision = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ["git", "-C", str(root), "status", "--porcelain"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        )
    except (OSError, subprocess.CalledProcessError):
        return {"revision": None, "dirty": None}

    return {"revision": revision or None, "dirty": dirty}


def _parse_license_table(readme: Path) -> dict[str, Any]:
    exact: dict[str, str] = {}
    folders: dict[str, str] = {}
    text_range_license: str | None = None

    if not readme.exists():
        return {
            "exact": exact,
            "folders": folders,
            "text_range_license": text_range_license,
        }

    for line in readme.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 2:
            continue
        source_spec, license_name = cells[0], cells[1]
        if source_spec.lower() in {"file", "---"} or set(source_spec) == {"-"}:
            continue

        folder_match = re.fullmatch(r"all files in FOLDER\s+(.+)", source_spec)
        if folder_match:
            folders[folder_match.group(1).strip().strip("/")] = license_name
            continue

        if re.fullmatch(r"oraec\d+\.json\s*\.\.\s*oraec\d+\.json", source_spec):
            text_range_license = license_name
            continue

        exact[source_spec] = license_name

    return {
        "exact": exact,
        "folders": folders,
        "text_range_license": text_range_license,
    }


def _license_for(path: str, specs: dict[str, Any]) -> str | None:
    exact = specs["exact"]
    if path in exact:
        return str(exact[path])

    if TEXT_FILE_RE.fullmatch(path) and specs["text_range_license"]:
        return str(specs["text_range_license"])

    first = path.split("/", 1)[0]
    folders = specs["folders"]
    if first in folders:
        return str(folders[first])

    return None


def _table_summary(path: Path) -> dict[str, Any]:
    delimiter = "," if path.suffix.lower() == ".csv" else "\t"
    rows: list[list[str]] = []

    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle, delimiter=delimiter)
        for row in reader:
            if row and any(cell != "" for cell in row):
                rows.append(row)

    header: list[str] | None = None
    if path.name == "mapping_oraec_trismegistos.csv" and rows:
        if rows[0] and rows[0][0].strip().casefold() == "oraec":
            header = rows.pop(0)

    column_counts = Counter(len(row) for row in rows)
    first_counts = Counter(row[0] for row in rows if row)
    second_counts = Counter(row[1] for row in rows if len(row) > 1)

    return {
        "header": header,
        "rows": len(rows),
        "column_counts": {str(k): v for k, v in sorted(column_counts.items())},
        "first_column_distinct": len(first_counts),
        "first_column_duplicate_values": sum(
            1 for count in first_counts.values() if count > 1
        ),
        "first_column_max_multiplicity": max(first_counts.values(), default=0),
        "second_column_distinct": len(second_counts),
        "second_column_duplicate_values": sum(
            1 for count in second_counts.values() if count > 1
        ),
        "second_column_max_multiplicity": max(second_counts.values(), default=0),
        "sample_rows": rows[:5],
    }


def _controlled_vocab_summary(
    ids_to_labels: dict[str, dict[str, set[str]]],
    occurrences: Counter[str],
    missing_ids: Counter[str],
    malformed: Counter[str],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for field in CONTROLLED_VOCABULARIES:
        mapping = ids_to_labels[field]
        collisions = {
            key: sorted(labels)
            for key, labels in sorted(mapping.items())
            if len(labels) > 1
        }
        result[field] = {
            "occurrences": occurrences[field],
            "distinct_ids": len(mapping),
            "missing_id_count": missing_ids[field],
            "malformed_item_count": malformed[field],
            "ids_with_multiple_labels_count": len(collisions),
            "ids_with_multiple_labels": collisions,
        }
    return result


def audit_source(root: str | Path) -> dict[str, Any]:
    """Audit a local ORAEC source tree without changing it."""
    source = Path(root).resolve()
    if not source.is_dir():
        raise ValueError(f"source directory does not exist: {source}")

    all_files = _iter_files(source)
    all_directories = _iter_directories(source)
    rel_files = [path.relative_to(source).as_posix() for path in all_files]
    rel_directories = [
        path.relative_to(source).as_posix() for path in all_directories
    ]
    text_paths = [
        path
        for path in all_files
        if path.parent == source and TEXT_FILE_RE.fullmatch(path.name)
    ]
    text_numbers = sorted(
        int(match.group("number"))
        for path in text_paths
        if (match := TEXT_FILE_RE.fullmatch(path.name)) is not None
    )
    text_number_min = min(text_numbers, default=None)
    text_number_max = max(text_numbers, default=None)
    missing_text_numbers = (
        sorted(set(range(text_number_min, text_number_max + 1)) - set(text_numbers))
        if text_number_min is not None and text_number_max is not None
        else []
    )
    non_text_files = [
        rel
        for rel in rel_files
        if not TEXT_FILE_RE.fullmatch(rel) and rel != "README.md"
    ]

    field_stats: dict[str, dict[str, dict[str, Any]]] = {
        "record": {},
        "sentence": {},
        "token": {},
        "credits": {},
    }
    counts: Counter[str] = Counter()
    counts["texts"] = 0
    counts["sentences"] = 0
    counts["tokens"] = 0
    field_populations: Counter[str] = Counter()

    text_ids: set[str] = set()
    duplicate_text_ids: list[str] = []
    invalid_record_ids: list[dict[str, str]] = []
    token_ids: set[str] = set()
    duplicate_token_ids: list[str] = []
    malformed_token_ids: list[str] = []
    invalid_token_ids: list[dict[str, str]] = []
    token_position_mismatches: list[dict[str, str]] = []
    top_level_key_mismatches: list[dict[str, str]] = []
    record_id_mismatches: list[dict[str, str]] = []
    malformed_json: list[dict[str, str]] = []
    unexpected_shapes: list[dict[str, str]] = []
    empty_token_sentences: list[dict[str, Any]] = []

    line_values: Counter[str] = Counter()
    line_leading_whitespace_count = 0
    line_trailing_whitespace_count = 0
    line_blank_count = 0
    hiero_values: Counter[str] = Counter()
    hiero_placeholder_count = 0
    hiero_replacement_count = 0
    grammar_values: dict[str, set[str]] = {field: set() for field in GRAMMAR_FIELDS}
    lemma_forms: dict[str, set[str]] = defaultdict(set)
    lemma_ids: set[str] = set()

    controlled_ids: dict[str, dict[str, set[str]]] = {
        field: defaultdict(set) for field in CONTROLLED_VOCABULARIES
    }
    controlled_occurrences: Counter[str] = Counter()
    controlled_missing_ids: Counter[str] = Counter()
    controlled_malformed: Counter[str] = Counter()

    idno_texts = 0
    idno_total = 0
    idno_texts_with_duplicates = 0
    idno_distinct: set[str] = set()

    credits_licenses: Counter[str] = Counter()
    credits_authors: Counter[str] = Counter()
    credits_sources: Counter[str] = Counter()

    sentence_translation_present = 0
    sentence_translation_empty = 0
    cotext_translation_present = 0
    bibliography_present = 0
    bibliography_empty = 0

    def text_number(path: Path) -> int:
        match = TEXT_FILE_RE.fullmatch(path.name)
        assert match is not None
        return int(match.group("number"))

    for path in sorted(text_paths, key=text_number):
        expected_id = path.stem
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            malformed_json.append({"path": path.name, "error": str(exc)})
            continue

        if not isinstance(payload, dict) or len(payload) != 1:
            unexpected_shapes.append(
                {"path": path.name, "reason": "top-level JSON must be a one-record object"}
            )
            continue

        top_key = next(iter(payload))
        record = payload[top_key]
        if top_key != expected_id:
            top_level_key_mismatches.append(
                {"path": path.name, "expected": expected_id, "actual": str(top_key)}
            )
        if not isinstance(record, dict):
            unexpected_shapes.append(
                {"path": path.name, "reason": "record value must be an object"}
            )
            continue

        counts["texts"] += 1
        field_populations["record"] += 1
        _observe_fields(field_stats["record"], record)

        record_id = record.get("oraecid")
        if record_id != expected_id:
            record_id_mismatches.append(
                {
                    "path": path.name,
                    "expected": expected_id,
                    "actual": "" if record_id is None else str(record_id),
                }
            )
        if isinstance(record_id, str):
            if record_id in text_ids:
                duplicate_text_ids.append(record_id)
            text_ids.add(record_id)
        else:
            invalid_record_ids.append(
                {
                    "path": path.name,
                    "expected": expected_id,
                    "actual_type": type(record_id).__name__,
                    "actual": repr(record_id),
                }
            )

        bibliography = record.get("bibliography")
        if bibliography is not None:
            bibliography_present += 1
            if _is_empty(bibliography):
                bibliography_empty += 1

        idno = record.get("idno")
        if isinstance(idno, list):
            idno_texts += 1
            values = [str(value) for value in idno]
            idno_total += len(values)
            idno_distinct.update(values)
            if len(values) != len(set(values)):
                idno_texts_with_duplicates += 1

        for field in CONTROLLED_VOCABULARIES:
            raw_values = record.get(field)
            if raw_values is None:
                continue
            if not isinstance(raw_values, list):
                controlled_malformed[field] += 1
                continue
            for item in raw_values:
                controlled_occurrences[field] += 1
                if not isinstance(item, dict):
                    controlled_malformed[field] += 1
                    continue
                identifier = item.get("id")
                label = item.get(field)
                if not isinstance(identifier, str) or not identifier:
                    controlled_missing_ids[field] += 1
                    continue
                if isinstance(label, str):
                    controlled_ids[field][identifier].add(label)

        credits = record.get("credits")
        if isinstance(credits, dict):
            field_populations["credits"] += 1
            _observe_fields(field_stats["credits"], credits)
            license_name = credits.get("license")
            if isinstance(license_name, str):
                credits_licenses[license_name] += 1
            author = credits.get("author")
            if isinstance(author, str):
                credits_authors[author] += 1
            sources = credits.get("source")
            if isinstance(sources, list):
                for source_url in sources:
                    if isinstance(source_url, str):
                        credits_sources[source_url] += 1

        sentences = record.get("sentences")
        if not isinstance(sentences, list):
            unexpected_shapes.append(
                {"path": path.name, "reason": "sentences must be a list"}
            )
            continue

        for sentence_number, sentence in enumerate(sentences, start=1):
            counts["sentences"] += 1
            if not isinstance(sentence, dict):
                unexpected_shapes.append(
                    {
                        "path": path.name,
                        "reason": f"sentence {sentence_number} must be an object",
                    }
                )
                continue
            field_populations["sentence"] += 1
            _observe_fields(field_stats["sentence"], sentence)

            if "translation" in sentence:
                sentence_translation_present += 1
                if _is_empty(sentence["translation"]):
                    sentence_translation_empty += 1

            tokens = sentence.get("token")
            if not isinstance(tokens, list):
                unexpected_shapes.append(
                    {
                        "path": path.name,
                        "reason": f"sentence {sentence_number} token must be a list",
                    }
                )
                continue

            if not tokens:
                empty_token_sentences.append(
                    {
                        "text": expected_id,
                        "sentence": sentence_number,
                        "translation": sentence.get("translation"),
                    }
                )

            for token_number, token in enumerate(tokens, start=1):
                counts["tokens"] += 1
                if not isinstance(token, dict):
                    unexpected_shapes.append(
                        {
                            "path": path.name,
                            "reason": (
                                f"sentence {sentence_number} token {token_number} "
                                "must be an object"
                            ),
                        }
                    )
                    continue
                field_populations["token"] += 1
                _observe_fields(field_stats["token"], token)

                token_id = token.get("token")
                expected_token_id = f"{expected_id}-{sentence_number}-{token_number}"
                if isinstance(token_id, str):
                    if token_id in token_ids:
                        duplicate_token_ids.append(token_id)
                    token_ids.add(token_id)
                    if not TOKEN_ID_RE.fullmatch(token_id):
                        malformed_token_ids.append(token_id)
                    elif token_id != expected_token_id:
                        token_position_mismatches.append(
                            {"expected": expected_token_id, "actual": token_id}
                        )
                else:
                    invalid_token_ids.append(
                        {
                            "expected": expected_token_id,
                            "actual_type": type(token_id).__name__,
                            "actual": repr(token_id),
                        }
                    )

                line_count = token.get("lineCount")
                if isinstance(line_count, str):
                    line_values[line_count] += 1
                    if line_count[:1].isspace():
                        line_leading_whitespace_count += 1
                    if line_count[-1:].isspace():
                        line_trailing_whitespace_count += 1
                    if not line_count.strip():
                        line_blank_count += 1

                hiero = token.get("hiero")
                if isinstance(hiero, str):
                    hiero_values[hiero] += 1
                    if hiero == "[⯑]":
                        hiero_placeholder_count += 1
                    if "�" in hiero:
                        hiero_replacement_count += 1

                if "cotext_translation" in token:
                    cotext_translation_present += 1

                lemma_id = token.get("lemmaID")
                if isinstance(lemma_id, (str, int)):
                    lemma_key = str(lemma_id)
                    lemma_ids.add(lemma_key)
                    lemma_form = token.get("lemma_form")
                    if isinstance(lemma_form, str):
                        lemma_forms[lemma_key].add(lemma_form)

                for field in GRAMMAR_FIELDS:
                    value = token.get(field)
                    if isinstance(value, (str, int, float, bool)):
                        grammar_values[field].add(str(value))

    tables: dict[str, Any] = {}
    for file_name in TABLE_FILES:
        table_path = source / file_name
        if table_path.exists():
            tables[file_name] = _table_summary(table_path)

    specs = _parse_license_table(source / "README.md")
    license_by_path: dict[str, str] = {}
    uncovered: list[str] = []
    for rel in rel_files:
        if rel == "README.md":
            continue
        license_name = _license_for(rel, specs)
        if license_name is None:
            uncovered.append(rel)
        else:
            license_by_path[rel] = license_name

    multiple_lemma_forms = {
        lemma_id: sorted(forms)
        for lemma_id, forms in sorted(lemma_forms.items())
        if len(forms) > 1
    }

    derived_files = {
        "collocation": [path for path in non_text_files if path.startswith("collocation/")],
        "statistics": [path for path in non_text_files if path.startswith("statistics/")],
    }

    return {
        "source": {
            "path": str(source),
            **_git_identity(source),
        },
        "inventory": {
            "file_count": len(rel_files),
            "directory_count": len(rel_directories),
            "directories": rel_directories,
            "text_file_count": len(text_paths),
            "text_number_min": text_number_min,
            "text_number_max": text_number_max,
            "missing_text_numbers": missing_text_numbers,
            "non_text_file_count": len(non_text_files),
            "non_text_files": non_text_files,
        },
        "counts": {
            "texts": counts["texts"],
            "sentences": counts["sentences"],
            "tokens": counts["tokens"],
        },
        "fields": {
            level: _finalize_field_stats(stats, field_populations[level])
            for level, stats in field_stats.items()
        },
        "text_ids": {
            "distinct": len(text_ids),
            "duplicate_count": len(duplicate_text_ids),
            "missing_or_non_string_count": len(invalid_record_ids),
        },
        "token_ids": {
            "distinct": len(token_ids),
            "duplicate_count": len(duplicate_token_ids),
            "missing_or_non_string_count": len(invalid_token_ids),
            "malformed_count": len(malformed_token_ids),
            "position_mismatch_count": len(token_position_mismatches),
        },
        "sentences": {
            "empty_token_count": len(empty_token_sentences),
        },
        "line_count": {
            "present": sum(line_values.values()),
            "distinct": len(line_values),
            "leading_whitespace_count": line_leading_whitespace_count,
            "trailing_whitespace_count": line_trailing_whitespace_count,
            "blank_count": line_blank_count,
            "values": dict(sorted(line_values.items())),
        },
        "hieroglyphs": {
            "present": sum(hiero_values.values()),
            "distinct": len(hiero_values),
            "placeholder_count": hiero_placeholder_count,
            "replacement_character_value_count": hiero_replacement_count,
        },
        "translations": {
            "sentence_present": sentence_translation_present,
            "sentence_empty": sentence_translation_empty,
            "cotext_present": cotext_translation_present,
        },
        "lemmas": {
            "distinct_ids": len(lemma_ids),
            "id_to_multiple_forms_count": len(multiple_lemma_forms),
            "id_to_multiple_forms": multiple_lemma_forms,
        },
        "grammar": {
            field: sorted(values) for field, values in grammar_values.items()
        },
        "controlled_vocabulary": _controlled_vocab_summary(
            controlled_ids,
            controlled_occurrences,
            controlled_missing_ids,
            controlled_malformed,
        ),
        "idno": {
            "texts_with_values": idno_texts,
            "total_values": idno_total,
            "distinct_values": len(idno_distinct),
            "texts_with_duplicate_values": idno_texts_with_duplicates,
        },
        "bibliography": {
            "present": bibliography_present,
            "empty": bibliography_empty,
        },
        "credits": {
            "licenses": dict(sorted(credits_licenses.items())),
            "authors_distinct": len(credits_authors),
            "sources_distinct": len(credits_sources),
            "source_urls": dict(sorted(credits_sources.items())),
        },
        "tables": tables,
        "derived_files": derived_files,
        "license": {
            "declared_exact": specs["exact"],
            "declared_folders": specs["folders"],
            "text_range_license": specs["text_range_license"],
            "covered_path_count": len(license_by_path),
            "uncovered_path_count": len(uncovered),
            "uncovered_paths": sorted(uncovered),
        },
        "anomalies": {
            "malformed_json": malformed_json,
            "unexpected_shapes": unexpected_shapes,
            "top_level_key_mismatches": top_level_key_mismatches,
            "record_id_mismatches": record_id_mismatches,
            "duplicate_text_ids": sorted(duplicate_text_ids),
            "invalid_record_ids": invalid_record_ids,
            "duplicate_token_ids": sorted(duplicate_token_ids),
            "invalid_token_ids": invalid_token_ids,
            "malformed_token_ids": sorted(malformed_token_ids),
            "token_position_mismatches": token_position_mismatches,
            "empty_token_sentences": empty_token_sentences,
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    """Render a compact human-readable summary of an audit report."""
    inventory = report["inventory"]
    counts = report["counts"]
    token_ids = report["token_ids"]
    license_info = report["license"]
    lines = [
        "# ORAEC source audit",
        "",
        f"- Source revision: `{report['source']['revision']}`",
        f"- Source dirty: `{report['source']['dirty']}`",
        f"- Text files: **{inventory['text_file_count']}**",
        f"- Texts parsed: **{counts['texts']}**",
        f"- Sentences: **{counts['sentences']}**",
        f"- Tokens: **{counts['tokens']}**",
        f"- Distinct token IDs: **{token_ids['distinct']}**",
        f"- Duplicate token IDs: **{token_ids['duplicate_count']}**",
        f"- Malformed token IDs: **{token_ids['malformed_count']}**",
        f"- Token position mismatches: **{token_ids['position_mismatch_count']}**",
        f"- Licence-uncovered paths: **{license_info['uncovered_path_count']}**",
        "",
        "## Licence-uncovered paths",
        "",
    ]
    uncovered = license_info["uncovered_paths"]
    if uncovered:
        lines.extend(f"- `{path}`" for path in uncovered)
    else:
        lines.append("- None")

    lines.extend(["", "## Mapping tables", ""])
    for name, summary in sorted(report["tables"].items()):
        lines.append(
            f"- `{name}`: {summary['rows']} rows; "
            f"{summary['first_column_duplicate_values']} repeated first-column values; "
            f"max first-column multiplicity {summary['first_column_max_multiplicity']}"
        )

    lines.extend(["", "## Grammar vocabularies", ""])
    for feature, values in sorted(report["grammar"].items()):
        lines.append(f"- `{feature}`: {len(values)} values")

    lines.append("")
    return "\n".join(lines)
