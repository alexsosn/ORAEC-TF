"""Deterministic researcher feature docs from the frozen native TF schema.

This module reads the *software* schema only. It neither fetches the upstream
corpus nor produces semantic sidecars. CI compares its output byte for byte
against docs/feature-reference.md to prevent silent drift.
"""

from __future__ import annotations

from typing import Any


def _cell(value: object) -> str:
    if value is None:
        return "—"
    if isinstance(value, (tuple, list)):
        value = ", ".join(str(part) for part in value)
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_feature_reference(schema: dict[str, Any]) -> str:
    """Render a stable, complete TF node/edge-feature reference as Markdown."""
    version = schema["schemaVersion"]
    nodes = schema["nodeTypes"]
    edges = schema["edgeFeatures"]
    lines: list[str] = [
        "# ORAEC-TF native Text-Fabric feature reference",
        "",
        f"Schema version: {version}",
        "",
        "Source: `schema/core.json` (the authoritative frozen schema).",
        "This document is generated; do not edit it independently.",
        "",
        "## Native graph model",
        "",
        f"Slot type: `{schema['slotType']}`.",
        f"Node types: {len(nodes)}. Node features: "
        f"{sum(len(spec['features']) for spec in nodes.values())}. "
        f"Edge features: {len(edges)}.",
        "",
        "Each feature records its source/derived provenance and value type.",
        "No external web endpoint is inferred from a node identifier.",
        "",
        "## Node features",
        "",
    ]
    for kind, spec in nodes.items():
        lines.extend([
            f"### `{kind}`",
            "",
            f"Source identity: {_cell(spec.get('sourceIdentity'))}.",
            f"Slot mapping: {_cell(spec.get('oslots'))}.",
            "",
            "|Feature|Origin|Value type|Source field(s)|Description|",
            "|---|---|---|---|---|",
        ])
        for name, info in spec["features"].items():
            origin = "Source" if info.get("origin") == "source" else "Derived"
            source_fields = info.get("sourceField", info.get("sourceFields"))
            if source_fields is None:
                source_fields = info.get("derivedFrom")
            lines.append(
                f"|`{_cell(name)}`|{origin}|{_cell(info.get('valueType'))}|"
                f"{_cell(source_fields)}|{_cell(info.get('description'))}|"
            )
        lines.append("")

    lines.extend([
        "## Edge features",
        "",
        "|Feature|Origin|From → to|Value type|Value meaning|Description|",
        "|---|---|---|---|---|---|",
    ])
    for name, info in edges.items():
        origin = "Source" if info.get("origin") == "source" else "Derived"
        endpoints = f"{_cell(info.get('from'))} → {_cell(info.get('to'))}"
        lines.append(
            f"|`{_cell(name)}`|{origin}|{endpoints}|"
            f"{_cell(info.get('valueType'))}|"
            f"{_cell(info.get('valueSemantics'))}|{_cell(info.get('description'))}|"
        )

    lines.extend([
        "",
        "## Interpretation and limitations",
        "",
        "- Linguistic fields, lineCount, and hieroglyphic Unicode are preserved",
        "  from source annotations; technical anchor slots are derived.",
        "- The source `lineCount` is a token annotation, not a constructed",
        "  line-node hierarchy. Never infer line identity from its string.",
        "- Schema v2 source U+000D (CR) is reconstructed losslessly from the",
        "  native value feature and its `<node_type>_cr_offsets` feature.",
        "  Direct feature values containing CR in source are TF-safe transport",
        "  strings, not exact raw strings until reconstructed (ADR 0006).",
        "- Per-text authorship is represented by source credit relations.",
        "  README corpus-level contributors do not create invented text credits.",
        "- Hierarchy nodes represent exact linked path prefixes, including",
        "  potentially empty source labels.",
        "- Licensed Trismegistos, Wikidata and Vega mappings are native TF",
        "  relations. Karnak mapping TSVs remain excluded pending licensing.",
        "- The source corpus and generated TF feature data are acquired or",
        "  built separately, not committed to this software repository.",
        "",
    ])
    return "\n".join(lines)
