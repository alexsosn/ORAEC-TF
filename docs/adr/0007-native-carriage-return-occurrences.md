# ADR 0007 — Queryable native carriage-return occurrences (schema v3)

Status: proposed; not approved for release until full pinned-source validation  
Issue: #42  
Supersedes the packed-offset transport section of ADR 0006 without weakening its original-string conservation requirement.

## Source and upstream evidence

Text-Fabric 13.1 encodes backslash, U+000A and TAB in `tf.core.helpers.tfFromValue`, but **not U+000D**. A literal CR is split into a new physical input row by Python's universal-newline reader in `tf.core.data._readDataTf`, causing sparse feature-to-node misattribution. It is unsafe to insert a raw CR into a regular TF text scalar.

The pinned ORAEC snapshot includes literal CR in several node families, not just bibliography. Direct inspection of `oraec/corpus_raw_data@b83a0ee5fae27a40d4c0a2a9a8c9c2973d45e9cd` found 80 CR across 18 sentence translations in `oraec29`, 123 across 23 translations in `oraec100`, and 2 in bibliography plus 1 translation CR in `oraec34`. ADR 0006 records 19 CR in `oraec6` bibliography. These are **source code points**; normalize none away.

## Schema v3 decision to test

Retain each source-bearing string's existing TF feature as a CR-free **transport scalar**, preserving all other code points and missing/empty distinction. **Do not** add packed offsets, JSON, XML, sidecars or a second corpus object. Represent each literal CR by a native `cr_occurrence` node with:
- `cr_feature: str`: exact original feature name on the annotated owner node
- `cr_offset: int`: zero-based Unicode code-point index in the **original** string
- `cr_owner`: native, unvalued edge from this occurrence node to **exactly one** original TF owner
- `oslots`: exactly the original owner's word slot span (a technical TF 13.1 compatibility requirement, not new linguistic text)

The identity of an occurrence is (owner node, feature, original code-point offset), and each tuple must be unique. This works uniformly for all ten existing owner node types, from word to external_ref. Do not fabricate word slots or attach CR to an adjacent node.

Researcher queries can use ordinary TF feature/edge APIs to find and filter each CR and use `NativeCRIndex(api).restore(node, feature)` to recover the exact source scalar. **The raw `F.bibliography.v(node)` is *not* equal to raw source when CR occurred** under TF 13.1; the accessor is essential, and documentation must not misrepresent that. Native integer CR positions are independently queryable without parsing string-encoded lists.

The writer gathers CR occurrences across all node families, then adds TF occurrence nodes after the graph's ordinary nodes are linked. All non-CR features retain existing TF node identities, source order and graph relations. Metadata records the new v3 transport, and the frozen schema removes *all ten* `*_cr_offsets` features rather than leaving duplicate versions of the semantics.

## Independent validation and release gate

RED tests cover leading, trailing, repeated, isolated CR, CRLF, multiple source fields on one owner, U+000D next to astral hieroglyphs, missing/empty fields, all graph node types, duplicate offsets, forged/unknown owner/feature/offset, orphan occurrence, and fabricated CR on unrelated feature or slot span.

The auditor must **not** import the writer's codec. It independently builds a strict occurrence index from `F.cr_feature`, `F.cr_offset` and `E.cr_owner`, verifies each node's exact oslots, uniqueness and target, and reconstructs string codepoints when comparing to raw JSON/TSV. Only metadata/provenance reports may be emitted as sidecars.

Pinned 13,026-text integration must check the exact full source, CR count by owner type/feature, native occurrence count, TF load, retention of 815,026 real words plus three technical anchors, feature string equality, and performance/storage impact. If full-source runtime or graph size is unacceptable, hold the PR and benchmark alternative native representations. Re-run adversarial exact-head review after every fix.
