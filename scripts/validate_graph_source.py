"""CLI gate for independent raw-source → Text-Fabric conservation checks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from oraec_tf.audit_graph import audit_graph_with_provenance
from oraec_tf.conversion_profile import PhaseRecorder


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("tf_dir", type=Path)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--converter-revision", required=True)
    parser.add_argument("--schema-version", type=int, required=True)
    parser.add_argument(
        "--include-karnak", action="store_true",
        help="Audit both local opt-in Karnak mapping TSVs independently",
    )
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument(
        "--profile-report", type=Path, default=None,
        help="Optional provenance-only independent-audit phase timings JSON",
    )
    args = parser.parse_args()
    if args.profile_report is not None and (
        args.profile_report.resolve() == args.report.resolve()
    ):
        parser.error("--profile-report must differ from --report")
    recorder = PhaseRecorder(enabled=args.profile_report is not None)

    report = audit_graph_with_provenance(
        args.source,
        args.tf_dir,
        source_revision=args.source_revision,
        converter_revision=args.converter_revision,
        schema_version=args.schema_version,
        require_complete_source=True,
        profile_recorder=recorder, include_karnak=args.include_karnak,
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    if args.profile_report is not None:
        profile = recorder.report()
        profile["format"] = "oraec-independent-audit-profile-v1"
        profile["phase_relationship"] = (
            "source_graph_audit includes independent_fabric_load"
        )
        args.profile_report.parent.mkdir(parents=True, exist_ok=True)
        args.profile_report.write_text(
            json.dumps(profile, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(
        {
            "ok": True,
            "counts": report["counts"],
            "native_cr_occurrences": report["native_cr_occurrences"],
        },
        sort_keys=True,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
