"""Run the ORAEC lineCount semantics analysis."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from oraec_tf.linecount import analyze_linecount_source, render_linecount_markdown
from oraec_tf.source import DEFAULT_SOURCE_REVISION, verify_source


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--json", dest="json_path", type=Path, required=True)
    parser.add_argument("--markdown", dest="markdown_path", type=Path, required=True)
    parser.add_argument("--expected-tokens", type=int)
    parser.add_argument("--expected-with-linecount", type=int)
    args = parser.parse_args()

    snapshot = verify_source(
        args.source,
        expected_revision=DEFAULT_SOURCE_REVISION,
    )
    report = analyze_linecount_source(snapshot.path)
    report["source"]["revision"] = snapshot.revision
    report["source"]["dirty"] = False

    args.json_path.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_path.parent.mkdir(parents=True, exist_ok=True)
    args.json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.markdown_path.write_text(
        render_linecount_markdown(report),
        encoding="utf-8",
    )

    failed = False
    if (
        args.expected_tokens is not None
        and report["counts"]["tokens"] != args.expected_tokens
    ):
        print(
            "token count mismatch: "
            f"expected {args.expected_tokens}, got {report['counts']['tokens']}"
        )
        failed = True
    if (
        args.expected_with_linecount is not None
        and report["counts"]["with_linecount"] != args.expected_with_linecount
    ):
        print(
            "lineCount coverage mismatch: "
            f"expected {args.expected_with_linecount}, "
            f"got {report['counts']['with_linecount']}"
        )
        failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
