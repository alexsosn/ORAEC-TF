"""Strict source parser producing the typed ORAEC intermediate representation."""

from __future__ import annotations

import csv
import html
import json
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from .ir import (
    ControlledValueIR,
    CorpusMetadataIR,
    CreditsIR,
    HierarchyComponentIR,
    HierarchyRowIR,
    MappingRowIR,
    MappingTableIR,
    SentenceIR,
    TextIR,
    TokenIR,
)

TEXT_FILE_RE = re.compile(r"^oraec(?P<number>\d+)\.json$")
README_TEXT_FAMILY_RE = re.compile(
    r"oraec\d+\.json\s*\.\.\s*oraec\d+\.json"
)
ANCHOR_RE = re.compile(r'<a\s+href="([^"]+)">([^<]*)</a>')

RECORD_KEYS = {
    "bibliography",
    "condition",
    "credits",
    "date",
    "idno",
    "location",
    "material",
    "objecttype",
    "oraecid",
    "origplace",
    "sentences",
    "title",
}
REQUIRED_RECORD_KEYS = {"credits", "oraecid", "sentences", "title"}
SENTENCE_KEYS = {"token", "translation"}
CREDITS_KEYS = {"author", "license", "source"}
TOKEN_KEYS = {
    "adjective",
    "adverb",
    "cotext_translation",
    "epitheton",
    "genus",
    "hiero",
    "inflection",
    "lemmaID",
    "lemma_form",
    "lineCount",
    "morphology",
    "name",
    "number",
    "numerus",
    "particle",
    "pos",
    "pronoun",
    "status",
    "token",
    "verbalClass",
    "voice",
    "written_form",
}
REQUIRED_TOKEN_KEYS = {"token", "written_form"}
CV_KINDS = ("date", "origplace", "objecttype", "location", "material")
CV_CARDINALITIES = {
    "date": (1, 2),
    "origplace": (1, 1),
    "objecttype": (1, 4),
    "location": (1, 1),
    "material": (1, 1),
}
CV_ATTRS = {
    "date": "dates",
    "origplace": "original_places",
    "objecttype": "object_types",
    "location": "locations",
    "material": "materials",
}
TOKEN_ATTRS = {
    "cotext_translation": "cotext_translation",
    "lineCount": "line_count",
    "hiero": "hiero",
    "pos": "pos",
    "name": "name_type",
    "number": "number_type",
    "voice": "voice",
    "genus": "genus",
    "pronoun": "pronoun_type",
    "numerus": "numerus",
    "epitheton": "epitheton",
    "morphology": "morphology",
    "inflection": "inflection",
    "adjective": "adjective_type",
    "particle": "particle_type",
    "adverb": "adverb_type",
    "verbalClass": "verbal_class",
    "status": "status",
}

MAPPING_SPECS = {
    "mapping_oraec_trismegistos.csv": (
        ",",
        "text.oraec_id",
        "trismegistos",
        True,
    ),
    "mapping_oraec_lemmata_vega.tsv": (
        "\t",
        "lex.lemma_id",
        "vega",
        True,
    ),
    "mapping_oraec_wikidata.tsv": (
        "\t",
        "author.author_name OR cv.cv_id",
        "wikidata",
        True,
    ),
    "mapping_oraec_karnak.tsv": (
        "\t",
        "text.oraec_id",
        "karnak",
        False,
    ),
    "mapping_oraec_lemmata_karnak.tsv": (
        "\t",
        "lex.lemma_id",
        "karnak",
        False,
    ),
}


class ParseError(ValueError):
    """Raised when source data cannot be represented by the frozen contract."""


def _expect_dict(value: object, *, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ParseError(f"{field} must be an object")
    return value


def _expect_list(value: object, *, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise ParseError(f"{field} must be a list")
    return value


def _expect_str(value: object, *, field: str) -> str:
    if not isinstance(value, str):
        raise ParseError(f"{field} must be a string")
    return value


def _optional_str(record: dict[str, Any], key: str, *, field: str) -> str | None:
    if key not in record:
        return None
    return _expect_str(record[key], field=field)


def _reject_unknown(
    obj: dict[str, Any],
    allowed: set[str],
    *,
    field: str,
    required: set[str] | None = None,
) -> None:
    unknown = sorted(set(obj) - allowed)
    if unknown:
        raise ParseError(f"{field} has unknown keys: {unknown}")
    if required is not None:
        missing = sorted(required - set(obj))
        if missing:
            raise ParseError(f"{field} is missing required keys: {missing}")


def _parse_cv_items(
    record: dict[str, Any],
    kind: str,
    *,
    text_id: str,
) -> tuple[ControlledValueIR, ...]:
    if kind not in record:
        return ()
    items = _expect_list(record[kind], field=f"{text_id}.{kind}")
    minimum, maximum = CV_CARDINALITIES[kind]
    if not minimum <= len(items) <= maximum:
        raise ParseError(f"{text_id}.{kind} cardinality must be {minimum}..{maximum}")
    seen_ids: set[str] = set()
    result: list[ControlledValueIR] = []
    for index, raw in enumerate(items, start=1):
        item = _expect_dict(raw, field=f"{text_id}.{kind}[{index}]")
        _reject_unknown(
            item,
            {"id", kind},
            field=f"{text_id}.{kind}[{index}]",
            required={"id", kind},
        )
        cv_id = _expect_str(item["id"], field=f"{text_id}.{kind}[{index}].id")
        if cv_id in seen_ids:
            raise ParseError(f"{text_id}.{kind} has duplicate ID {cv_id!r}")
        seen_ids.add(cv_id)
        result.append(
            ControlledValueIR(
                kind=kind,
                cv_id=cv_id,
                label=_expect_str(
                    item[kind],
                    field=f"{text_id}.{kind}[{index}].{kind}",
                ),
            )
        )
    return tuple(result)


def _parse_credits(raw: object, *, text_id: str) -> CreditsIR:
    credits = _expect_dict(raw, field=f"{text_id}.credits")
    _reject_unknown(
        credits,
        CREDITS_KEYS,
        field=f"{text_id}.credits",
        required=CREDITS_KEYS,
    )
    raw_sources = _expect_list(
        credits["source"],
        field=f"{text_id}.credits.source",
    )
    sources = tuple(
        _expect_str(value, field=f"{text_id}.credits.source[{index}]")
        for index, value in enumerate(raw_sources, start=1)
    )
    if len(sources) != 2:
        raise ParseError(f"{text_id}.credits.source cardinality must be 2")
    if len(set(sources)) != len(sources):
        raise ParseError(f"{text_id}.credits.source has duplicate URLs")
    return CreditsIR(
        license=_expect_str(credits["license"], field=f"{text_id}.credits.license"),
        author=_expect_str(credits["author"], field=f"{text_id}.credits.author"),
        sources=sources,
    )


def _parse_token(
    raw: object,
    *,
    text_id: str,
    sentence_index: int,
    token_index: int,
) -> TokenIR:
    token = _expect_dict(
        raw,
        field=f"{text_id}.sentences[{sentence_index}].token[{token_index}]",
    )
    field = f"{text_id}.sentences[{sentence_index}].token[{token_index}]"
    _reject_unknown(
        token,
        TOKEN_KEYS,
        field=field,
        required=REQUIRED_TOKEN_KEYS,
    )

    token_id = _expect_str(token["token"], field=f"{field}.token")
    expected_id = f"{text_id}-{sentence_index}-{token_index}"
    if token_id != expected_id:
        raise ParseError(
            f"token position identity mismatch: expected {expected_id}, got {token_id}"
        )

    has_lemma_id = "lemmaID" in token
    has_lemma_form = "lemma_form" in token
    if has_lemma_id != has_lemma_form:
        raise ParseError(
            f"{field}: lemmaID and lemma_form must be present together"
        )

    lemma_id = (
        _expect_str(token["lemmaID"], field=f"{field}.lemmaID")
        if has_lemma_id
        else None
    )
    lemma_form = (
        _expect_str(token["lemma_form"], field=f"{field}.lemma_form")
        if has_lemma_form
        else None
    )

    optional: dict[str, str | None] = {}
    for source_key, target_key in TOKEN_ATTRS.items():
        optional[target_key] = _optional_str(
            token,
            source_key,
            field=f"{field}.{source_key}",
        )

    return TokenIR(
        token_id=token_id,
        written_form=_expect_str(
            token["written_form"],
            field=f"{field}.written_form",
        ),
        lemma_id=lemma_id,
        lemma_form=lemma_form,
        **optional,
    )


def _parse_sentence(
    raw: object,
    *,
    text_id: str,
    sentence_index: int,
) -> SentenceIR:
    sentence = _expect_dict(
        raw,
        field=f"{text_id}.sentences[{sentence_index}]",
    )
    field = f"{text_id}.sentences[{sentence_index}]"
    _reject_unknown(
        sentence,
        SENTENCE_KEYS,
        field=field,
        required=SENTENCE_KEYS,
    )
    raw_tokens = _expect_list(sentence["token"], field=f"{field}.token")
    tokens = tuple(
        _parse_token(
            token,
            text_id=text_id,
            sentence_index=sentence_index,
            token_index=token_index,
        )
        for token_index, token in enumerate(raw_tokens, start=1)
    )
    return SentenceIR(
        index=sentence_index,
        translation=_expect_str(
            sentence["translation"],
            field=f"{field}.translation",
        ),
        tokens=tokens,
    )


def parse_text(path: str | Path) -> TextIR:
    """Parse one root ORAEC JSON record into exact typed source semantics."""
    source_path = Path(path)
    match = TEXT_FILE_RE.fullmatch(source_path.name)
    if match is None:
        raise ParseError(f"unsupported ORAEC text filename: {source_path.name}")
    text_id = source_path.stem

    try:
        payload = json.loads(source_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ParseError(f"cannot parse {source_path}: {exc}") from exc

    top = _expect_dict(payload, field=source_path.name)
    if list(top) != [text_id]:
        raise ParseError(
            f"{source_path.name}: top-level identity must be exactly {text_id}"
        )

    record = _expect_dict(top[text_id], field=text_id)
    _reject_unknown(
        record,
        RECORD_KEYS,
        field=text_id,
        required=REQUIRED_RECORD_KEYS,
    )
    oraec_id = _expect_str(record["oraecid"], field=f"{text_id}.oraecid")
    if oraec_id != text_id:
        raise ParseError(
            f"record identity mismatch: filename {text_id}, oraecid {oraec_id}"
        )

    raw_sentences = _expect_list(
        record["sentences"],
        field=f"{text_id}.sentences",
    )
    sentences = tuple(
        _parse_sentence(
            sentence,
            text_id=text_id,
            sentence_index=index,
        )
        for index, sentence in enumerate(raw_sentences, start=1)
    )

    cv_values = {
        CV_ATTRS[kind]: _parse_cv_items(record, kind, text_id=text_id)
        for kind in CV_KINDS
    }

    if "idno" in record:
        raw_idnos = _expect_list(record["idno"], field=f"{text_id}.idno")
        if len(raw_idnos) != 2:
            raise ParseError(f"{text_id}.idno cardinality must be 2")
        idnos = tuple(
            _expect_str(value, field=f"{text_id}.idno[{index}]")
            for index, value in enumerate(raw_idnos, start=1)
        )
    else:
        idnos = ()

    return TextIR(
        oraec_id=oraec_id,
        title=_expect_str(record["title"], field=f"{text_id}.title"),
        sentences=sentences,
        credits=_parse_credits(record["credits"], text_id=text_id),
        bibliography=_optional_str(
            record,
            "bibliography",
            field=f"{text_id}.bibliography",
        ),
        condition=_optional_str(
            record,
            "condition",
            field=f"{text_id}.condition",
        ),
        idnos=idnos,
        **cv_values,
    )


def iter_texts(root: str | Path) -> Iterator[TextIR]:
    """Yield parsed ORAEC texts in deterministic numeric file order."""
    source = Path(root)
    if not source.is_dir():
        raise ParseError(f"source directory does not exist: {source}")

    paths: list[tuple[int, Path]] = []
    for path in source.iterdir():
        if not path.is_file():
            continue
        match = TEXT_FILE_RE.fullmatch(path.name)
        if match is None:
            continue
        paths.append((int(match.group("number")), path))

    for _number, path in sorted(paths):
        yield parse_text(path)


def parse_corpus_metadata(root: str | Path) -> CorpusMetadataIR:
    """Parse ordered corpus-level author identities from the upstream README."""
    path = Path(root) / "README.md"
    if not path.is_file():
        raise ParseError("README.md is required for corpus metadata")

    rows: list[list[str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) >= 3 and README_TEXT_FAMILY_RE.fullmatch(cells[0]):
            rows.append(cells)

    if len(rows) != 1:
        raise ParseError(
            "README.md must contain exactly one ORAEC JSON-family author row"
        )

    authors = tuple(
        author.strip()
        for author in rows[0][2].split(",")
        if author.strip()
    )
    duplicates = sorted(
        author for author in set(authors) if authors.count(author) > 1
    )
    if duplicates:
        raise ParseError(f"duplicate corpus author identities: {duplicates}")
    if not authors:
        raise ParseError("README corpus author list must not be empty")

    return CorpusMetadataIR(corpus_authors=authors)


def _parse_tla_url(url: str, *, field: str) -> tuple[str, str]:
    prefixes = {
        "object": "https://thesaurus-linguae-aegyptiae.de/object/",
        "text": "https://thesaurus-linguae-aegyptiae.de/text/",
    }
    for kind, prefix in prefixes.items():
        if url.startswith(prefix):
            tla_id = url[len(prefix) :]
            if tla_id and "/" not in tla_id:
                return kind, tla_id
    raise ParseError(f"{field}: unsupported TLA hierarchy URL {url!r}")


def parse_hierarchy(root: str | Path) -> tuple[HierarchyRowIR, ...]:
    """Parse the exact paired label/link hierarchy serialization."""
    path = Path(root) / "oraec_hierarchical_path.tsv"
    if not path.is_file():
        raise ParseError("oraec_hierarchical_path.tsv is required")

    result: list[HierarchyRowIR] = []
    seen_texts: set[str] = set()

    with path.open(encoding="utf-8", newline="") as handle:
        for row_index, row in enumerate(csv.reader(handle, delimiter="\t"), start=1):
            if len(row) != 3:
                raise ParseError(
                    f"hierarchy row {row_index} must have exactly 3 columns"
                )
            text_id, path_text, linked_text = row
            if text_id in seen_texts:
                raise ParseError(f"duplicate hierarchy text identity: {text_id}")
            seen_texts.add(text_id)

            labels = path_text.split("→")
            matches = list(ANCHOR_RE.finditer(linked_text))
            cursor = 0
            links: list[tuple[str, str]] = []
            for position, match in enumerate(matches):
                expected_separator = "" if position == 0 else "→"
                if linked_text[cursor:match.start()] != expected_separator:
                    raise ParseError(
                        f"hierarchy linked path has unparsed bytes for {text_id}"
                    )
                links.append((match.group(1), html.unescape(match.group(2))))
                cursor = match.end()
            if cursor != len(linked_text):
                raise ParseError(
                    f"hierarchy linked path has unparsed bytes for {text_id}"
                )
            if len(labels) != len(links):
                raise ParseError(
                    f"hierarchy component mismatch for {text_id}: "
                    f"{len(labels)} labels, {len(links)} links"
                )

            components: list[HierarchyComponentIR] = []
            for depth, (label, (url, linked_label)) in enumerate(
                zip(labels, links, strict=True),
                start=1,
            ):
                if label != linked_label:
                    raise ParseError(
                        f"hierarchy component label mismatch for {text_id} "
                        f"at depth {depth}"
                    )
                kind, tla_id = _parse_tla_url(
                    url,
                    field=f"hierarchy {text_id} depth {depth}",
                )
                components.append(
                    HierarchyComponentIR(
                        label=label,
                        tla_url=url,
                        tla_kind=kind,
                        tla_id=tla_id,
                    )
                )

            result.append(
                HierarchyRowIR(
                    oraec_id=text_id,
                    components=tuple(components),
                )
            )

    return tuple(result)


def _read_mapping_rows(
    path: Path,
    *,
    delimiter: str,
    skip_tm_header: bool,
) -> tuple[MappingRowIR, ...]:
    if not path.is_file():
        raise ParseError(f"required mapping file is missing: {path.name}")

    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle, delimiter=delimiter))

    if skip_tm_header and rows and rows[0] == ["ORAEC", "Trismegistos Text"]:
        rows = rows[1:]

    result: list[MappingRowIR] = []
    seen: set[tuple[str, str]] = set()
    for index, row in enumerate(rows, start=1):
        if len(row) != 2:
            raise ParseError(
                f"mapping row {index} in {path.name} must have exactly 2 columns"
            )
        pair = (row[0], row[1])
        if pair in seen:
            raise ParseError(
                f"duplicate mapping row in {path.name}: {pair[0]!r}, {pair[1]!r}"
            )
        seen.add(pair)
        result.append(MappingRowIR(source=pair[0], target=pair[1]))

    return tuple(result)


def parse_mapping_tables(root: str | Path) -> tuple[MappingTableIR, ...]:
    """Parse every audited mapping family, retaining release gating explicitly."""
    source = Path(root)
    result: list[MappingTableIR] = []

    for filename, (
        delimiter,
        source_domain,
        target_system,
        release_included,
    ) in MAPPING_SPECS.items():
        rows = _read_mapping_rows(
            source / filename,
            delimiter=delimiter,
            skip_tm_header=filename == "mapping_oraec_trismegistos.csv",
        )
        result.append(
            MappingTableIR(
                filename=filename,
                source_domain=source_domain,
                target_system=target_system,
                release_included=release_included,
                rows=rows,
            )
        )

    return tuple(result)
