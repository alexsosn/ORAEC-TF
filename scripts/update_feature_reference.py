"""Rebuild/check the researcher feature reference from frozen schema/core.json."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from oraec_tf.feature_reference import render_feature_reference

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schema/core.json"
OUTPUT = ROOT / "docs/feature-reference.md"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check", action="store_true",
        help="fail if docs/feature-reference.md differs from frozen schema",
    )
    args = parser.parse_args()
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    rendered = render_feature_reference(schema)
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != rendered:
            parser.error("feature-reference.md is stale; regenerate it")
        print("Feature reference is synchronized with schema/core.json")
        return 0
    OUTPUT.write_text(rendered, encoding="utf-8")
    print(f"Updated {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
