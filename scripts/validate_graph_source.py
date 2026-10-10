"""CLI gate for independent raw-source → Text-Fabric conservation checks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from oraec_tf.audit_graph import audit_graph_with_provenance


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("tf_dir", type=Path)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--converter-revision", required=True)
    parser.add_argument("--schema-version", type=int, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    report = audit_graph_with_provenance(
        args.source,
        args.tf_dir,
        source_revision=args.source_revision,
        converter_revision=args.converter_revision,
        schema_version=args.schema_version,
        require_complete_source=True,
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"ok": True, "counts": report["counts"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
