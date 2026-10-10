"""Independent streaming checks for typed ORAEC parser conservation.

This layer consumes typed IR, never serialized Text-Fabric, and is deliberately
separate from the schema preflight and TF writer.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .ir import MappingTableIR
from .parser import (
    TEXT_FILE_RE,
    ParseError,
    iter_texts,
    parse_corpus_metadata,
    parse_hierarchy,
    parse_mapping_tables,
)


class CorpusValidationError(ValueError):
    """A source identity or typed IR conservation invariant failed."""


def _check_mapping(
    table: MappingTableIR,
    *,
    texts: set[str],
    lemmas: set[str],
    authors: set[str],
    cv_domains: dict[str, set[str]],
) -> None:
    if not table.release_included:
        # Explicitly unlicensed/pending sources never enter the release graph.
        return

    for row in table.rows:
        key = row.source
        if table.target_system == "trismegistos":
            if key not in texts:
                raise CorpusValidationError(
                    f"unresolved trismegistos source text {key!r}"
                )
        elif table.target_system == "vega":
            if key not in lemmas:
                raise CorpusValidationError(f"unresolved vega lemma {key!r}")
        elif table.target_system == "wikidata":
            matches = int(key in authors) + len(cv_domains.get(key, set()))
            if matches != 1:
                raise CorpusValidationError(
                    f"wikidata key {key!r} has {matches} native source identities"
                )
        else:
            raise CorpusValidationError(
                f"unsupported included mapping family: {table.filename}"
            )


def validate_corpus_source(root: str | Path) -> dict[str, Any]:
    """Parse and independently validate the complete local source snapshot."""
    source = Path(root)
    if not source.is_dir():
        raise CorpusValidationError(f"source directory does not exist: {source}")

    text_numbers: list[int] = []
    for path in source.iterdir():
        match = TEXT_FILE_RE.fullmatch(path.name)
        if match is not None and path.is_file():
            text_numbers.append(int(match.group("number")))
    if not text_numbers or sorted(text_numbers) != list(range(1, len(text_numbers) + 1)):
        raise CorpusValidationError("ORAEC text filename number range is not continuous")

    try:
        metadata = parse_corpus_metadata(source)
        texts: set[str] = set()
        lemmas: dict[str, str] = {}
        author_names: set[str] = set(metadata.corpus_authors)
        cv_domains: dict[str, set[str]] = {}
        cv_labels: dict[tuple[str, str], str] = {}
        sentence_count = 0
        token_count = 0
        empty_sentence_count = 0

        for record in iter_texts(source):
            if record.oraec_id in texts:
                raise CorpusValidationError(
                    f"duplicate ORAEC text identity {record.oraec_id}"
                )
            texts.add(record.oraec_id)
            author_names.add(record.credits.author)
            sentence_count += len(record.sentences)
            for values in (
                record.dates,
                record.original_places,
                record.object_types,
                record.locations,
                record.materials,
            ):
                for cv in values:
                    cv_domains.setdefault(cv.cv_id, set()).add(cv.kind)
                    identity = (cv.kind, cv.cv_id)
                    prior = cv_labels.setdefault(identity, cv.label)
                    if prior != cv.label:
                        raise CorpusValidationError(
                            f"controlled vocabulary label mismatch for {identity}"
                        )
            for sentence in record.sentences:
                if not sentence.tokens:
                    empty_sentence_count += 1
                token_count += len(sentence.tokens)
                for token in sentence.tokens:
                    if token.lemma_id is not None:
                        if token.lemma_form is None:
                            raise CorpusValidationError(
                                f"missing lemma form for {token.lemma_id}"
                            )
                        prior = lemmas.setdefault(token.lemma_id, token.lemma_form)
                        if prior != token.lemma_form:
                            raise CorpusValidationError(
                                f"lemma {token.lemma_id!r} has conflicting forms"
                            )

        if len(texts) != len(text_numbers):
            raise CorpusValidationError("text identity count differs from source files")

        hierarchy = parse_hierarchy(source)
        hierarchy_ids = {row.oraec_id for row in hierarchy}
        if hierarchy_ids != texts or len(hierarchy) != len(texts):
            raise CorpusValidationError(
                "hierarchy text identities do not match parsed ORAEC texts"
            )

        tables = parse_mapping_tables(source)
        for table in tables:
            _check_mapping(
                table,
                texts=texts,
                lemmas=set(lemmas),
                authors=author_names,
                cv_domains=cv_domains,
            )

        return {
            "ok": True,
            "counts": {
                "texts": len(texts),
                "sentences": sentence_count,
                "tokens": token_count,
                "lemmas": len(lemmas),
                "empty_token_sentences": empty_sentence_count,
                "corpus_authors": len(metadata.corpus_authors),
                "hierarchy_rows": len(hierarchy),
                "included_mapping_rows": sum(
                    len(table.rows) for table in tables if table.release_included
                ),
                "excluded_mapping_rows": sum(
                    len(table.rows) for table in tables if not table.release_included
                ),
            },
            "excluded_mapping_files": [
                table.filename for table in tables if not table.release_included
            ],
        }
    except ParseError as exc:
        raise CorpusValidationError(str(exc)) from exc
