"""Run the reproducible ORAEC source audit and write report files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from oraec_tf.audit import audit_source, render_markdown


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--json", dest="json_path", type=Path, required=True)
    parser.add_argument("--markdown", dest="markdown_path", type=Path, required=True)
    parser.add_argument("--expected-revision")
    parser.add_argument("--expected-text-files", type=int)
    args = parser.parse_args()

    report = audit_source(args.source)

    args.json_path.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_path.parent.mkdir(parents=True, exist_ok=True)
    args.json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.markdown_path.write_text(render_markdown(report), encoding="utf-8")

    failed = False
    if args.expected_revision is not None:
        revision = report["source"]["revision"]
        if revision != args.expected_revision:
            print(
                f"source revision mismatch: expected {args.expected_revision}, got {revision}"
            )
            failed = True

    if args.expected_text_files is not None:
        count = report["inventory"]["text_file_count"]
        if count != args.expected_text_files:
            print(
                f"text file count mismatch: expected {args.expected_text_files}, got {count}"
            )
            failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
