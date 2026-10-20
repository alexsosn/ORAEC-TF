"""Command-line entry point for ORAEC-TF."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from tf_build.validate import FeatureRequirement, validate_tf_artifact
from tf_build.workspace import BuildWorkspace

from .app_resources import installed_app_dir
from .conversion_profile import PhaseRecorder
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
from .tf_count_probe import probe_tf_counts
from .writer import write_tf


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="oraec-tf",
        description="ORAEC to Text-Fabric research and conversion tools",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("source-info", help="Print the default supported upstream source")
    subparsers.add_parser("app-path", help="Print the installed standard TF app directory")

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
        "--profile", action="store_true",
        help="Emit source-free per-phase timing metrics in the JSON summary",
    )
    convert.add_argument(
        "--include-karnak", action="store_true",
        help="Explicit local-only TF inclusion of two Karnak TSV mappings; "
             "redistribution rights unresolved. Never auto-enabled for Agora.",
    )
    convert.add_argument(
        "--upstream-commit", required=True,
        help="Immutable source commit (must match the frozen supported schema)",
    )

    return parser


def _convert(
    source: str, destination: str, revision: str, *, profile: bool = False,
    include_karnak: bool = False,
) -> dict[str, object]:
    recorder = PhaseRecorder(enabled=profile)
    if revision.lower() != DEFAULT_SOURCE_REVISION:
        raise ValueError("unsupported upstream revision for frozen TF schema")
    with recorder.phase("source_identity"):
        snapshot = verify_source(source, expected_revision=DEFAULT_SOURCE_REVISION)
    target = Path(destination)
    resolved_target = target.resolve()
    if target.is_symlink() or resolved_target == snapshot.path or (
        snapshot.path in resolved_target.parents
    ):
        raise ValueError("output must not be a symlink or be inside the source checkout")
    if target.exists() and (not target.is_dir() or any(target.iterdir())):
        raise ValueError("output must be an empty directory or not exist")

    # Validate the source before any caller-owned output mutation. A parent
    # symlink can change while that audit runs: pin the *canonical* destination
    # once it completes, and never again use the mutable alias for rmdir,
    # workspace creation, or exception cleanup.
    with recorder.phase("source_semantics"):
        report = (
            validate_corpus_source(snapshot.path, include_karnak=True)
            if include_karnak else validate_corpus_source(snapshot.path)
        )
    canonical_target = target.resolve()
    if target.is_symlink() or canonical_target == snapshot.path or (
        snapshot.path in canonical_target.parents
    ):
        raise ValueError("output must not be a symlink or be inside the source checkout")
    if canonical_target.exists() and (
        not canonical_target.is_dir() or any(canonical_target.iterdir())
    ):
        raise ValueError("output must be an empty directory or not exist")
    existed_as_empty_dir = canonical_target.is_dir()
    if existed_as_empty_dir:
        # BuildWorkspace is create-only; preserve the accepted empty-target
        # contract while avoiding a symlink-parent restoration race.
        canonical_target.rmdir()
    try:
        workspace = BuildWorkspace(canonical_target)
        with workspace:
            stage = workspace.path
            with recorder.phase("writer_and_ir"):
                write_tf(
                    iter_texts(snapshot.path),
                    stage,
                    source_revision=snapshot.revision,
                    corpus_metadata=parse_corpus_metadata(snapshot.path),
                    mapping_tables=(
                        parse_mapping_tables(snapshot.path, include_karnak=True)
                        if include_karnak else parse_mapping_tables(snapshot.path)
                    ),
                    hierarchy_rows=parse_hierarchy(snapshot.path),
                )

            # TF may silently load newer compiled .tfx instead of corrupted
            # shipped .tf bodies. Exhaustively reload a private source-only
            # view before claiming any build was validated or publishing it.
            with recorder.phase("uncached_tf_validation"):
                validate_tf_artifact(
                    stage,
                    level="all",
                    require_otext=True,
                    required_features=(
                        FeatureRequirement("oraec_id", kind="node", value_type="str"),
                        FeatureRequirement("sentence_index", kind="node", value_type="int"),
                        FeatureRequirement("token_id", kind="node", value_type="str"),
                    ),
                )

            # The exhaustive, isolated tf-build level="all" step above
            # already performed a real Text-Fabric load of every source
            # feature. Re-loading its warp into a second large Fabric here
            # consumed 233 seconds / ~1.7 GiB in the pinned-corpus profile.
            # Independently reconcile actual source .tf node identities with
            # the upstream parser's counts, without trusting compiled caches.
            with recorder.phase("source_tf_counts"):
                counted = probe_tf_counts(stage)
                expected = report["counts"]
                if (
                    counted["texts"] != expected["texts"]
                    or counted["sentences"] != expected["sentences"]
                    or counted["tokens"] != expected["tokens"]
                    or counted["technical_anchors"]
                    != expected["empty_token_sentences"]
                    or counted["slots"]
                    != expected["tokens"] + expected["empty_token_sentences"]
                ):
                    raise ValueError("generated TF node counts diverge from parsed source")
                text_count = counted["texts"]
                sentence_count = counted["sentences"]
                real_words = counted["tokens"]
                word_count = counted["slots"]
            with recorder.phase("atomic_publish"):
                workspace.publish()
    except Exception as error:
        # Restore the caller's formerly empty directory only if no competing
        # actor has created a replacement during staging or publication.
        if (
            existed_as_empty_dir
            and not canonical_target.exists()
            and not canonical_target.is_symlink()
        ):
            try:
                canonical_target.mkdir()
            except FileExistsError:
                pass
            except OSError as restore_error:
                error.add_note(
                    f"failed to restore empty output {canonical_target}: {restore_error}"
                )
        raise

    result: dict[str, object] = {
        "output": str(canonical_target),
        "revision": snapshot.revision,
        "counts": {
            "texts": text_count,
            "sentences": sentence_count,
            "tokens": real_words,
            "technical_anchors": word_count - real_words,
            "slots": word_count,
        },
    }
    if include_karnak:
        result["mapping_mode"] = "local-karnak-opt-in"
        result["karnak_mapping_redistribution_terms"] = "unresolved"
        result["karnak_mapping_files"] = [
            "mapping_oraec_karnak.tsv",
            "mapping_oraec_lemmata_karnak.tsv",
        ]
    if profile:
        result["profile"] = recorder.report()
    return result

def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "app-path":
        print(installed_app_dir())
        return 0

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
        result = _convert(
            args.source, args.output, args.upstream_commit,
            profile=args.profile, include_karnak=args.include_karnak,
        )
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0

    raise AssertionError(f"unhandled command: {args.command}")
