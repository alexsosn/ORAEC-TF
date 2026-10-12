# Research — opt-in local Karnak native TF crosswalks (#85)

Date: 2026-10-12. Supported source: `oraec/corpus_raw_data@b83a0ee5fae27a40d4c0a2a9a8c9c2973d45e9cd`.

## Real source findings

Directly read both TSVs at the exact pinned upstream revision (no in-repository redistribution):

| File | Rows | Source IDs | Target IDs | One-to-many source maximum |
| --- | ---: | ---: | ---: | ---: |
| `mapping_oraec_karnak.tsv` | 31 | 31 | 22 | 1 |
| `mapping_oraec_lemmata_karnak.tsv` | 1,973 | 1,917 | 1,963 | 6 |

Both use exact two-column tab-separated source/target pairs and `http://sith.huma-num.fr/...` targets. Text mapping can have multiple ORAEC texts pointing at one external Karnak document. Lemma mapping has multiple targets for the same ORAEC lemma; any lookup or native TF graph must preserve **all pairs**, without assuming one-to-one identities or coercing target URL categories into false equivalences.

## Current implementation traced

- `parser.py::MAPPING_SPECS` parses both files with `release_included=False`. The typed `MappingTableIR` carries this flag and the source filename.
- `parser_validation._check_mapping` skips excluded mappings and does not validate source IDs; `validate_corpus_source` distinguishes included/excluded row counts.
- `writer.write_tf` rejects non-whitelisted included mapping tables and skips excluded rows. It supports native `external_ref` nodes and provenance-valued `external` edges, but only branch-matches Trismegistos, VÉgA, and Wikidata.
- `audit_graph._verify_readme_and_external_crosswalks` independently reads three accepted input mapping files; it disallows any Karnak external nodes. `audit_basic_graph` compares all node/edge relations through native `Fabric`.
- Direct CLI `oraec-tf convert` invokes validation and writer. Agora's `oraec_tf.agora.materialize` invokes the CLI **without** any optional flag: this must stay the default; a remotely hosted service's network-denied conversion does not prove outputs private.
- `schema/core.json` freezes release/default `excludedMappings`; do not silently flip this. A new explicit **local optional mode** may extend the schema without changing the default materializer result.
- `LICENSE_SCOPE.md` and release gate #12 now distinguish MIT software publication from corpus data publication; #17 still holds public sharing rights review for datasets containing Karnak pairs.

## Design constraints

Expose an explicit CLI `--include-karnak` **only for direct local conversion**, with no equivalent Agora manifest option by default. Propagate this flag to parser source validation, writer and independent audit. Preserve row cardinalities, every native edge and exact mapping-filename provenance. Reject source-ID mismatches, malformed or duplicate pair rows, unresolved relationships, or publication of partially validated output. The default graph and all canonical default semantic fingerprints must remain unchanged.

For local-mode evidence, use separate test workflow/manual command on pinned source `oraec-tf convert ... --include-karnak` plus independent raw-source-to-TF audit in include-karnak mode. Do not upload the generated graph, bulk TSV content or expanded private data as CI artifacts. Include only counts, checksums and final success/failure.
