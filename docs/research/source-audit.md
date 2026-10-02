# ORAEC pinned-source audit

Issue: #2  
Supported source: `oraec/corpus_raw_data@b83a0ee5fae27a40d4c0a2a9a8c9c2973d45e9cd`

This report records corpus-wide facts that constrain the Text-Fabric schema. It is research evidence, not a semantic sidecar for the future corpus.

## Reproducibility

The audit is implemented by `src/oraec_tf/audit.py` and `scripts/audit_source.py`.

Final evidence run: GitHub Actions source-audit run **37069853172** on ORAEC-TF head `0a1a8b1e722708bb9a8706c1ee8b68c82ea83606`.

Artifact id: `11253987082`  
Artifact digest: `sha256:74aa91445bca4020f6ae201f75e471b153472ad86667ab4b290a3f0ad68da283`

The workflow acquired the exact source commit, verified its SHA, audited the complete tree, and reported a clean checkout.

## Corpus identity

- 13,026 text JSON files, continuously numbered 1–13,026.
- 101,796 sentences.
- 815,026 tokens.
- 13,026 unique text IDs with no identity anomalies.
- 815,026 unique token IDs with no duplicates, malformed IDs, missing IDs, or position mismatches.
- no malformed JSON or unsupported record/sentence/token container shapes.

## Record fields

| Field | Present | Observed shape |
| --- | ---: | --- |
| `oraecid` | 13,026 | unique string |
| `title` | 13,026 | string; 10,713 distinct |
| `sentences` | 13,026 | list; 1–1,233 sentences |
| `credits` | 13,026 | dict, exactly 3 fields |
| `bibliography` | 12,888 | non-empty string |
| `date` | 12,841 | list; cardinality 1–2 |
| `origplace` | 12,931 | one-item controlled-vocabulary list |
| `objecttype` | 12,942 | controlled-vocabulary list; cardinality 1–4 |
| `location` | 3,803 | one-item controlled-vocabulary list |
| `idno` | 3,803 | two-item list |
| `material` | 971 | one-item controlled-vocabulary list |
| `condition` | 170 | `fragmentarisch` or `vollständig` |

Every current `idno` list contains the same source value twice. This is upstream multiplicity and must not be silently normalized before #3 defines the contract.

## Controlled vocabularies

| Vocabulary | Occurrences | IDs | Missing IDs | ID/label collisions |
| --- | ---: | ---: | ---: | ---: |
| date | 15,371 | 104 | 0 | 0 |
| original place | 12,931 | 116 | 0 | 0 |
| object type | 13,181 | 52 | 0 | 0 |
| location | 3,803 | 97 | 0 | 0 |
| material | 971 | 7 | 0 | 0 |

Multi-valued metadata must remain relational/queryable rather than delimiter-packed.

## Sentences

Every sentence has `translation` and `token`.

- 101,796 translations, including 1,163 empty strings.
- exactly three zero-token sentences:
  - `oraec17:248`, empty translation;
  - `oraec34:256`, empty translation;
  - `oraec5614:3`, translation `{Chui-en-Chenemu}`.

Their TF representation is tracked in #20.

## Tokens and lexical identity

Every token has `token` and `written_form`.

| Field | Present | Distinct |
| --- | ---: | ---: |
| `lineCount` | 789,633 | 28,672 |
| `cotext_translation` | 783,161 | 31,456 |
| `pos` | 783,318 | 13 |
| `lemmaID` | 779,011 | 18,733 |
| `lemma_form` | 779,011 | 14,750 |
| `hiero` | 267,042 | 40,686 |

Across all 779,011 lemmatized tokens, no `lemmaID` maps to multiple `lemma_form` values. Shared lexical nodes keyed by lemma ID are therefore a strong candidate for #3.

All sparse grammar fields are scalar strings in the supported snapshot; the audit artifact records their complete value vocabularies.

### lineCount

This field is not safely interpreted as a numeric line number:

- 28,672 exact values;
- 372,047 occurrences begin with whitespace;
- 5 end with whitespace;
- 5 are whitespace-only;
- values include numeric-looking labels and descriptive prose.

Exact source values must be preserved. #19 researches whether real TF line nodes are warranted and whether a separate derived navigation label is defensible.

### Hieroglyphic values

Among 267,042 `hiero` values:
- 13,198 are exact `[⯑]`;
- 6,545 contain U+FFFD.

No repair is justified by the audit alone. #21 covers provenance and rendering.

## Credits/provenance

Every record has:
- licence `cc-by-sa-4.0`;
- one author; 25 distinct authors;
- exactly two source URLs.

One source URL, `https://github.com/simondschweitzer/aes`, occurs in every record. The other is a per-text AED-TEI XML URL; 13,026 such URLs are distinct. These are provenance links, consistent with ADR 0001; they do not make AED/AES a second semantic authority.

## Hierarchy and external mappings

### ORAEC hierarchy

`oraec_hierarchical_path.tsv` has 13,026 rows and exactly 3 columns:
1. unique ORAEC text ID;
2. `→`-separated human-readable path;
3. corresponding HTML-linked path carrying TLA object/text URLs and IDs.

The human path has 12,981 distinct values; shared-path multiplicity reaches 5.

The path/HTML serialization must be parsed into native hierarchy semantics under #7 rather than stored as an opaque semantic blob.

### Mapping multiplicity

| Mapping | Rows | Source keys | Targets | Max source multiplicity | Max target multiplicity |
| --- | ---: | ---: | ---: | ---: | ---: |
| Trismegistos | 1,244 | 1,244 | 279 | 1 | 182 |
| VÉgA lemma | 7,464 | 7,464 | 3,588 | 1 | 461 |
| Karnak text | 31 | 31 | 22 | 1 | 4 |
| Karnak lemma | 1,973 | 1,917 | 1,963 | 6 | 3 |
| Wikidata | 310 | 310 | 303 | 1 | 3 |

The Wikidata source-key domain is heterogeneous: contributor names and controlled-vocabulary IDs both occur. #7 must resolve node ownership instead of attaching the table wholesale to one node type.

Karnak mappings are one-to-many in real data; their redistribution licence remains open in #17.

## Derived datasets

The upstream tree contains:
- 18,736 files under `collocation/`;
- 10 files under `statistics/`.

ORAEC documents collocations as lemma co-occurrence within sentence boundaries. Those results are reproducible once sentence membership and word→lemma relations exist in TF. The statistics directory likewise contains computed hieroglyph-frequency and TF-IDF/type-token outputs.

They should not be duplicated as authoritative core graph semantics. If later useful, they can be reproduced as queries/reports/modules. Non-reconstructible evidence, if discovered, must be modelled explicitly rather than kept as opaque files.

## Licence boundary

The root upstream licence table covers 31,776 audited paths. Exactly two paths are uncovered:
- `mapping_oraec_karnak.tsv`;
- `mapping_oraec_lemmata_karnak.tsv`.

Upstream blog evidence supports ORAEC-created CC0 intent, but the repository table omits them. #17 is release-blocking; until resolved, release builds must fail closed or exclude these mappings.

## Consequences

#3 should consume #19 and #20 before freezing structural semantics.

Evidence-backed candidates:
- token/word occurrences as the likely slot layer;
- shared `lex` nodes keyed by `lemmaID`;
- shared controlled-vocabulary entities for ID-backed metadata;
- native hierarchy entities/edges;
- occurrence-preserving multi-valued relations;
- exact source features where normalization would discard evidence.

Focused follow-up:
- #17 Karnak licence;
- #19 `lineCount` semantics;
- #20 zero-token sentences;
- #21 hieroglyph placeholder/U+FFFD provenance and rendering.
