# ADR 0006 — Lossless carriage returns in native Text-Fabric

Status: historical, superseded by ADR 0007 / schema version 3; retained as evidence of the TF 13.1 corruption mechanism  
Issue: #40  
Supported pinned source: b83a0ee5fae27a40d4c0a2a9a8c9c2973d45e9cd

## Source evidence and failure mechanism

The pinned `oraec6.json` bibliography contains **19 literal U+000D carriage
returns**, mostly in CRLF sequences. The first full independent source audit
failed on `oraec10`: its Mariette bibliography was attached to Text-Fabric
node for `oraec29`, offset by exactly 19 text nodes. The diagnostic full
writer CI run 38062529497 confirmed `source_match_elsewhere=["oraec29"]`.

In Text-Fabric 13.1, `tf.core.helpers.tfFromValue` escapes LF, TAB, and
backslash, but **not CR**. Both Text-Fabric source-file writing and reading
use Python text mode, which treats a literal CR as a line boundary. Consequently
a CR inside a source string can split a sparse TF feature row, shifting values
onto other nodes. Validation of node counts does not detect this failure.

## Decision

We **do not** silently normalize, discard, or replace source carriage returns.
We also do not use JSON/XML sidecars or modify any real word slots or node
identities.

Because Text-Fabric 13.1 has no CR escape that its standard `Fabric.load`
reader decodes back into a carriage return, we transport a source value with
literal U+000D as two *ordinary native TF node features*:

1. The original string feature, with **only U+000D characters removed**. The
   resulting source text remains Unicode, searchable, and directly displayable.
   Existing LF, whitespace, hieroglyphs, HTML entities and source spelling
   are untouched.
2. One sparse node-local `<node_type>_cr_offsets` feature. Its value is a
   sorted, delimiter-separated mapping `feature=offset,offset|feature=offset`,
   with zero-based Unicode codepoint offsets measured in the **original** raw
   strings, before removal of any CR. The grammar is unambiguous because
   feature names contain only ASCII lowercase letters, digits and underscores,
   and offsets are decimal integers. No JSON, XML or hidden sidecar is used.

One offset feature is declared for each frozen native node type. For nodes
without CR in their original strings the offset feature is **absent**. The
`oraec_tf.text_codec.restore_source_string(value, offset_feature, name)`
helper inserts each CR in ascending original-index order, yielding the exact
original Unicode string, including CRLF versus lone CR and repeated CRs.
Consumers doing literal source comparison **must reconstruct** rather than
treating the transport-only field value as the raw source.

For example, the exact raw string `"X\\r\\nY"` becomes the TF value
`"X\\nY"` plus `text_cr_offsets="bibliography=1"`. The two values recover
`"X\\r\\nY"` without ambiguity.

This is an explicit transport encoding, not semantic approximation: the
original character positions remain directly queryable within the native TF
graph. The decoder rejects duplicate/invalid/out-of-range offsets rather than
accepting fabricated raw content.

## Compatibility and verification

This **amends schema/core.json to schemaVersion 2**, preserving the original
ten node types, edge features, slot count and all source semantic identities.
Each `<node_type>_cr_offsets` node feature is derived and described in the
machine-readable schema. The application can choose to display the LF-only
value but research-grade source retrieval must decode exact CR positions.

The writer applies the codec to every node feature, not just bibliographies.
Unit tests cover mixed CRLF, LF, isolated CR, and repeated CR. The pinned-source
workflow and independent auditor must prove that no CR can shift a feature
value to another text; `oraec6`, `oraec10`, and exact record identity are
mandatory regression controls.

Longer-term, Text-Fabric upstream could add an actual escaped CR syntax in
both its writer and reader. Until that is released and required by ORAEC-TF,
this native two-feature encoding remains necessary.
