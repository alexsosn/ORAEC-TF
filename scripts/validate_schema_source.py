"""Validate the frozen schema against a verified ORAEC source checkout."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from oraec_tf.schema_preflight import audit_schema_source
from oraec_tf.source import DEFAULT_SOURCE_REVISION, verify_source


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--json", dest="json_path", type=Path, required=True)
    args = parser.parse_args()

    snapshot = verify_source(
        args.source,
        expected_revision=DEFAULT_SOURCE_REVISION,
    )
    report = audit_schema_source(snapshot.path)
    report["source"] = {
        "path": str(snapshot.path),
        "revision": snapshot.revision,
        "dirty": False,
    }

    args.json_path.parent.mkdir(parents=True, exist_ok=True)
    args.json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    if report["ok"]:
        print(
            "schema preflight passed: "
            f"{report['counts']['texts']} texts, "
            f"{report['counts']['lemmas']} lemmas, "
            f"{report['counts']['external_rows']} external rows"
        )
        return 0

    print("schema preflight failed")
    print(json.dumps(report["anomalies"], ensure_ascii=False, indent=2, sort_keys=True))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
