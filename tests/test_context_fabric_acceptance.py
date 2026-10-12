"""CI check: native TF, raw Context-Fabric and compiled .cfm graph equivalence."""

from __future__ import annotations

import hashlib
import importlib
import runpy
from pathlib import Path
from typing import Any

import pytest
from tf.fabric import Fabric as NativeFabric

from oraec_tf.writer import write_tf

# Normal unit matrices omit Python 3.13-only cfabric; the dedicated job installs it.
pytest.importorskip("cfabric.core")


def snapshot(
    api: Any,
    types: tuple[str, ...],
    features: tuple[str, ...],
    parent_type: str,
    slot_type: str,
    query: str,
    edges: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Capture real graph semantics, not only .tf/.cfm file existence."""
    type_nodes = {kind: tuple(api.F.otype.s(kind)) for kind in types}
    nodes = sorted({n for members in type_nodes.values() for n in members})
    parents = type_nodes[parent_type]
    assert parents, f"missing {parent_type} parent"
    assert type_nodes[slot_type], f"missing {slot_type} slots"
    result: dict[str, Any] = {
        "slot_type": api.F.otype.slotType,
        "types": type_nodes,
        "values": {
            feature: tuple((n, getattr(api.F, feature).v(n)) for n in nodes)
            for feature in features
        },
        "descendants": tuple(
            (n, tuple(api.L.d(n, otype=slot_type))) for n in parents
        ),
        "query": tuple(tuple(row) for row in api.S.search(query, silent="deep")),
        "edges": {
            feature: tuple(
                (n, tuple(sorted(getattr(api.E, feature).f(n)))) for n in nodes
            )
            for feature in edges
        },
    }
    assert result["query"], f"representative search returned no results: {query}"
    assert any(slots for _, slots in result["descendants"])
    return result


def verify(
    output: Path,
    types: tuple[str, ...],
    features: tuple[str, ...],
    parent_type: str,
    slot_type: str,
    query: str,
    edges: tuple[str, ...] = (),
) -> None:
    assert (output / "otype.tf").is_file()
    assert (output / "oslots.tf").is_file()
    assert (output / "otext.tf").is_file()
    native = NativeFabric(locations=str(output), silent="deep").loadAll(silent="deep")
    assert native is not None and native is not False
    baseline = snapshot(native, types, features, parent_type, slot_type, query, edges)
    assert baseline["slot_type"] == slot_type
    assert all(
        any(value is not None for _, value in baseline["values"][feature])
        for feature in features
    ), "fixture lacks values for a required feature"

    cf_fabric = importlib.import_module("cfabric.core").Fabric
    raw_fabric = cf_fabric(locations=str(output), silent="deep")
    raw_api = raw_fabric.loadAll(silent="deep")
    assert raw_api is not None and raw_api is not False
    assert not getattr(raw_fabric, "_loaded_from_cfm", False)
    assert snapshot(raw_api, types, features, parent_type, slot_type, query, edges) == baseline, (
        "Context-Fabric raw .tf API differs from native Text-Fabric"
    )

    tf_names = sorted(p.name for p in output.glob("*.tf"))
    before = {name: hashlib.sha256((output / name).read_bytes()).hexdigest() for name in tf_names}
    assert raw_fabric.compile(silent="deep"), "Context-Fabric .cfm compilation failed"
    assert list((output / ".cfm").glob("*/meta.json")), "compiled .cfm manifest missing"
    assert before == {
        name: hashlib.sha256((output / name).read_bytes()).hexdigest() for name in tf_names
    }, "compilation modified native TF source features"

    compiled_fabric = cf_fabric(locations=str(output), silent="deep")
    compiled_api = compiled_fabric.loadAll(silent="deep")
    assert compiled_api is not None and compiled_api is not False
    assert getattr(compiled_fabric, "_loaded_from_cfm", False), (
        "fresh loader silently fell back to raw .tf"
    )
    assert snapshot(
        compiled_api, types, features, parent_type, slot_type, query, edges
    ) == baseline, "compiled Context-Fabric graph differs from native Text-Fabric"


def test_native_to_context_fabric_raw_and_compiled(tmp_path: Path) -> None:
    fixture = runpy.run_path(str(Path(__file__).with_name("test_writer.py")))
    output = tmp_path / "oraec"
    write_tf(fixture["_texts"](), output, source_revision=fixture["REVISION"])
    verify(
        output,
        types=("word", "sentence", "text", "author"),
        features=("oraec_id", "title", "token_id", "written_form", "is_anchor", "license"),
        parent_type="text",
        slot_type="word",
        query="text oraec_id=oraec1",
        edges=("author",),
    )
