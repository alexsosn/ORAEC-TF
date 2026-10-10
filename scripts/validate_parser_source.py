"""Run strict ORAEC typed-parser conservation checks against local source."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from oraec_tf.parser_validation import validate_corpus_source


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--json", dest="json_path", type=Path, required=True)
    parser.add_argument("--expected-texts", type=int)
    parser.add_argument("--expected-sentences", type=int)
    parser.add_argument("--expected-tokens", type=int)
    parser.add_argument("--expected-lemmas", type=int)
    args = parser.parse_args()

    report = validate_corpus_source(args.source)
    args.json_path.parent.mkdir(parents=True, exist_ok=True)
    args.json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    expected = {
        "texts": args.expected_texts,
        "sentences": args.expected_sentences,
        "tokens": args.expected_tokens,
        "lemmas": args.expected_lemmas,
    }
    failures = [
        f"{key}: expected {value}, got {report['counts'][key]}"
        for key, value in expected.items()
        if value is not None and report["counts"][key] != value
    ]
    if failures:
        print("\n".join(failures))
        return 1
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
