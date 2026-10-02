"""Command-line entry point for ORAEC-TF."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from .source import DEFAULT_SOURCE_REVISION, SOURCE_REPOSITORY, fetch_source


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
        help="Exact Git revision to checkout",
    )

    return parser


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

    raise AssertionError(f"unhandled command: {args.command}")
