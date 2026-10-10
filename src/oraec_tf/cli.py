"""Command-line entry point for ORAEC-TF."""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from collections.abc import Sequence
from pathlib import Path

from tf.fabric import Fabric

from .parser import (
    iter_texts,
    parse_corpus_metadata,
    parse_hierarchy,
    parse_mapping_tables,
)
from .parser_validation import validate_corpus_source
from .source import (
    DEFAULT_SOURCE_REVISION,
    SOURCE_REPOSITORY,
    fetch_source,
    verify_source,
)
from .writer import write_tf


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="oraec-tf",
        description="ORAEC to Text-Fabric research and conversion tools",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("source-info", help="Print the default supported upstream source")

    fetch = subparsers.add_parser("fetch", help="Fetch a pinned ORAEC source checkout")
    fetch.add_argument("destination", help="Empty/nonexistent destination directory")
    fetch.add_argument(
        "--revision",
        default=DEFAULT_SOURCE_REVISION,
        help="Exact immutable 40-hex Git commit to checkout",
    )

    verify = subparsers.add_parser(
        "verify-source",
        help="Verify a clean local ORAEC checkout at an immutable commit",
    )
    verify.add_argument("source", help="Local ORAEC Git checkout")
    verify.add_argument(
        "--revision",
        default=DEFAULT_SOURCE_REVISION,
        help="Expected immutable 40-hex Git commit",
    )

    convert = subparsers.add_parser(
        "convert", help="Convert a verified local pinned ORAEC checkout to TF"
    )
    convert.add_argument("source", help="Clean local ORAEC Git checkout")
    convert.add_argument("--output", required=True, help="Empty/nonexistent TF output")
    convert.add_argument(
        "--upstream-commit", required=True,
        help="Immutable source commit (must match the frozen supported schema)",
    )

    return parser


def _convert(source: str, destination: str, revision: str) -> dict[str, object]:
    if revision.lower() != DEFAULT_SOURCE_REVISION:
        raise ValueError("unsupported upstream revision for frozen TF schema")
    snapshot = verify_source(source, expected_revision=DEFAULT_SOURCE_REVISION)
    target = Path(destination)
    resolved_target = target.resolve()
    if target.is_symlink() or resolved_target == snapshot.path or (
        snapshot.path in resolved_target.parents
    ):
        raise ValueError("output must not be a symlink or be inside the source checkout")
    if target.exists() and (not target.is_dir() or any(target.iterdir())):
        raise ValueError("output must be an empty directory or not exist")

    # Validate the source before any output publication.
    report = validate_corpus_source(snapshot.path)
    target.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(
        tempfile.mkdtemp(
            prefix=f".{target.name}.oraec-tf-",
            dir=target.parent,
        )
    )
    existed_as_empty_dir = target.exists()
    try:
        write_tf(
            iter_texts(snapshot.path),
            stage,
            source_revision=snapshot.revision,
            corpus_metadata=parse_corpus_metadata(snapshot.path),
            mapping_tables=parse_mapping_tables(snapshot.path),
            hierarchy_rows=parse_hierarchy(snapshot.path),
        )

        # Reload the staging build, never a publicly visible partial target.
        api = Fabric(locations=str(stage), silent="deep").load(
            "oraec_id sentence_index token_id", silent="deep"
        )
        if not api:
            raise ValueError("generated Text-Fabric corpus did not load")
        word_count = len(api.F.otype.s("word"))
        text_count = len(api.F.otype.s("text"))
        sentence_count = len(api.F.otype.s("sentence"))
        real_words = sum(
            api.F.token_id.v(w) is not None for w in api.F.otype.s("word")
        )
        expected = report["counts"]
        if (
            text_count != expected["texts"]
            or sentence_count != expected["sentences"]
            or real_words != expected["tokens"]
            or word_count != real_words + expected["empty_token_sentences"]
        ):
            raise ValueError("generated TF node counts diverge from parsed source")

        # Rename within the same parent/file system only after all checks pass.
        if existed_as_empty_dir:
            target.rmdir()
        stage.replace(target)
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        if existed_as_empty_dir and not target.exists():
            target.mkdir()
        raise

    return {
        "output": str(target.resolve()),
        "revision": snapshot.revision,
        "counts": {
            "texts": text_count,
            "sentences": sentence_count,
            "tokens": real_words,
            "technical_anchors": word_count - real_words,
            "slots": word_count,
        },
    }

def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "source-info":
        print(
            json.dumps(
                {
                    "repository": SOURCE_REPOSITORY,
                    "revision": DEFAULT_SOURCE_REVISION,
                },
                sort_keys=True,
            )
        )
        return 0

    if args.command == "fetch":
        snapshot = fetch_source(args.destination, revision=args.revision)
        print(json.dumps({"path": str(snapshot.path), "revision": snapshot.revision}))
        return 0

    if args.command == "verify-source":
        snapshot = verify_source(
            args.source,
            expected_revision=args.revision,
        )
        print(json.dumps({"path": str(snapshot.path), "revision": snapshot.revision}))
        return 0

    if args.command == "convert":
        result = _convert(args.source, args.output, args.upstream_commit)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0

    raise AssertionError(f"unhandled command: {args.command}")
