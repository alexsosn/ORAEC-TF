# ORAEC-TF native graph: researcher feature reference

**Corpus source:** [`oraec/corpus_raw_data`](https://github.com/oraec/corpus_raw_data) pinned to `b83a0ee5fae27a40d4c0a2a9a8c9c2973d45e9cd`; **schema:** `core.json` version 2. Generated `.tf` files are built locally and are not distributed in this software repository.

## Reading the native representation

Source features are marked `source` and preserve the canonical ORAEC annotation (subject to the CR transport caveat below); `derived` features are explicit conversion structure, not additional scholarly assertions. The **word** slot is the lowest TF level. Exactly **815,026 source tokens** plus **3 technical anchor slots** represent 101,796 sentences; anchors have `is_anchor=1`, no source token identity and an empty `trailer`. There are 13,026 text nodes.

Words belong to sentence nodes and sentences to text nodes by `oslots`. Corpus lexemes, CV entities, credits, bibliographic sources, duplicate-preserving idno occurrences, hierarchy ancestors and external IDs are native TF nodes and edges, **not lists serialized inside JSON/XML sidecars**. Text and sentence section identifiers are `text.oraec_id` and `sentence.sentence_index`.

**Missing versus empty:** An absent source field corresponds to a missing feature value (`None`) in TF, not an invented sentinel; a present source empty string can remain `""`. Use `api.F.<feature>.v(node)` to inspect a scalar and `api.E.<edge>.f(node)` to inspect a relation. All feature names below are exact TF identifiers.

**Hieroglyphic writing:** `word.hiero` is verbatim source Unicode, and `word.written_form` is the source transliteration; do not infer Egyptian characters when the source does not supply them. The app offers `text-orig-full` and, when `hiero` occurs, `text-orig-hiero` formats.

**Controlled vocabulary and crosswalks:** CV nodes identify entries by `(cv_kind, cv_id)`; occurrence order is retained in valued edges `date`, `origplace`, `objecttype`, `location`, and `material`. `source` edges preserve source-URL order, `idno` keeps distinct occurrences even for identical values, and `external` carries mapping-provenance filenames. Supported mappings are Trismegistos, VÉgA, and Wikidata. Karnak mapping data remains excluded pending licence verification (#17). Linked hierarchy entries provide `tla_url` with its original TLA target and `parent` chains; do not guess unverified URLs from ORAEC IDs.

**CR transport limitation (issue #42):** TF 13.1 cannot safely store a literal carriage return (U+000D) in a `.tf` row. The current source-preserving encoding removes `\r` from the transport scalar and records its original character offsets in a sparse per-node `*_cr_offsets` TF feature. The **exact original source string** is therefore the result of `oraec_tf.text_codec.restore_source_string(api.F.bibliography.v(node), api.F.text_cr_offsets.v(node), "bibliography")`, not necessarily the raw value returned by `F.bibliography` alone. These packed offset strings are temporary architecture debt tracked in #42, not research-facing list annotations. Do not compare transport-only scalars for exact provenance.

**Provenance and licence:** Repository software is MIT; the main source corpus is CC BY-SA 4.0. TF feature `license` is source-specific where present; source author credits are separate from README contributor authors. The local build can be reproduced at the pinned revision and audited with the independent raw-to-graph verifier in CI.

## Native node features

| Exact feature | Value type | Origin | Canonical source or derivation | Meaning |
| --- | --- | --- | --- | --- |
| `word.token_id` | `str` | `source` | token.token | Exact ORAEC token identifier for a real source word. |
| `word.written_form` | `str` | `source` | token.written_form | Exact ORAEC transliterated written form. |
| `word.cotext_translation` | `str` | `source` | token.cotext_translation | Exact ORAEC token-level cotext translation. |
| `word.hiero` | `str` | `source` | token.hiero | Exact ORAEC Unicode hieroglyphic string; never repaired or normalized. |
| `word.line_count` | `str` | `source` | token.lineCount | Exact ORAEC lineCount string including source whitespace. |
| `word.pos` | `str` | `source` | token.pos | Exact ORAEC part-of-speech value. |
| `word.name_type` | `str` | `source` | token.name | Exact ORAEC name subtype from token.name. |
| `word.number_type` | `str` | `source` | token.number | Exact ORAEC number subtype from token.number. |
| `word.voice` | `str` | `source` | token.voice | Exact ORAEC grammatical voice. |
| `word.genus` | `str` | `source` | token.genus | Exact ORAEC grammatical genus/gender label. |
| `word.pronoun_type` | `str` | `source` | token.pronoun | Exact ORAEC pronoun subtype. |
| `word.numerus` | `str` | `source` | token.numerus | Exact ORAEC grammatical number label. |
| `word.epitheton` | `str` | `source` | token.epitheton | Exact ORAEC epitheton/title subtype. |
| `word.morphology` | `str` | `source` | token.morphology | Exact ORAEC morphology marker. |
| `word.inflection` | `str` | `source` | token.inflection | Exact ORAEC inflection label. |
| `word.adjective_type` | `str` | `source` | token.adjective | Exact ORAEC adjective subtype. |
| `word.particle_type` | `str` | `source` | token.particle | Exact ORAEC particle subtype. |
| `word.adverb_type` | `str` | `source` | token.adverb | Exact ORAEC adverb subtype. |
| `word.verbal_class` | `str` | `source` | token.verbalClass | Exact ORAEC verbalClass value. |
| `word.status` | `str` | `source` | token.status | Exact ORAEC grammatical status value. |
| `word.is_anchor` | `int` | `derived` | ADR 0002 zero-token sentence compatibility | Marks the three converter-derived compatibility slots required for zero-token source sentences. |
| `word.trailer` | `str` | `derived` | text display spacing; empty on anchors | Converter-derived display trailer: one space on real words and empty on technical anchors. |
| `word.word_cr_offsets` | `str` | `derived` | exact source string U+000D positions; lossless TF 13.1 transport (ADR 0006) | Sparse per-word-node map feature=comma-separated original character offsets for each literal CR removed from TF string transport; paired reconstruction restores exact source Unicode. |
| `sentence.sentence_index` | `int` | `derived` | 1-based record.sentences array position | One-based source sentence array position within its ORAEC text. |
| `sentence.translation` | `str` | `source` | sentence.translation | Exact ORAEC sentence translation; empty string is distinct from absence. |
| `sentence.sentence_cr_offsets` | `str` | `derived` | exact source string U+000D positions; lossless TF 13.1 transport (ADR 0006) | Sparse per-sentence-node map feature=comma-separated original character offsets for each literal CR removed from TF string transport; paired reconstruction restores exact source Unicode. |
| `text.oraec_id` | `str` | `source` | record.oraecid | Exact stable ORAEC text identifier. |
| `text.title` | `str` | `source` | record.title | Exact ORAEC text title. |
| `text.bibliography` | `str` | `source` | record.bibliography | Exact ORAEC bibliography string when present. |
| `text.condition` | `str` | `source` | record.condition | Exact ORAEC condition value when present. |
| `text.license` | `str` | `source` | credits.license | Exact per-text ORAEC credits.license value. |
| `text.text_cr_offsets` | `str` | `derived` | exact source string U+000D positions; lossless TF 13.1 transport (ADR 0006) | Sparse per-text-node map feature=comma-separated original character offsets for each literal CR removed from TF string transport; paired reconstruction restores exact source Unicode. |
| `lex.lemma_id` | `str` | `source` | token.lemmaID | Exact ORAEC lemmaID used as shared lexical identity. |
| `lex.lemma_form` | `str` | `source` | token.lemma_form | Exact ORAEC lemma_form associated with lemma_id. |
| `lex.lex_cr_offsets` | `str` | `derived` | exact source string U+000D positions; lossless TF 13.1 transport (ADR 0006) | Sparse per-lex-node map feature=comma-separated original character offsets for each literal CR removed from TF string transport; paired reconstruction restores exact source Unicode. |
| `cv.cv_kind` | `str` | `derived` | source record field name | Converter-derived controlled-vocabulary domain name. |
| `cv.cv_id` | `str` | `source` | record.<cv_kind>[].id | Exact ORAEC controlled-vocabulary identifier. |
| `cv.cv_label` | `str` | `source` | record.<cv_kind>[].<cv_kind> | Exact ORAEC controlled-vocabulary display label. |
| `cv.cv_cr_offsets` | `str` | `derived` | exact source string U+000D positions; lossless TF 13.1 transport (ADR 0006) | Sparse per-cv-node map feature=comma-separated original character offsets for each literal CR removed from TF string transport; paired reconstruction restores exact source Unicode. |
| `author.author_name` | `str` | `source` | — | Exact ORAEC credits.author string. |
| `author.is_corpus_author` | `int` | `source` | README author column for oraec1.json .. oraec13026.json | Marks an exact author identity declared for the full ORAEC JSON corpus family in the upstream README. |
| `author.corpus_author_index` | `int` | `derived` | 1-based order in README author column for oraec1.json .. oraec13026.json | Preserves the source order of corpus-level authors declared in the upstream README. |
| `author.author_cr_offsets` | `str` | `derived` | exact source string U+000D positions; lossless TF 13.1 transport (ADR 0006) | Sparse per-author-node map feature=comma-separated original character offsets for each literal CR removed from TF string transport; paired reconstruction restores exact source Unicode. |
| `source_ref.source_url` | `str` | `source` | credits.source[] | Exact ORAEC credits.source URL. |
| `source_ref.source_ref_cr_offsets` | `str` | `derived` | exact source string U+000D positions; lossless TF 13.1 transport (ADR 0006) | Sparse per-source_ref-node map feature=comma-separated original character offsets for each literal CR removed from TF string transport; paired reconstruction restores exact source Unicode. |
| `idno.idno_value` | `str` | `source` | record.idno[] | Exact ORAEC idno list item, including duplicate occurrences. |
| `idno.idno_index` | `int` | `derived` | 1-based record.idno list position | One-based source idno list position. |
| `idno.idno_cr_offsets` | `str` | `derived` | exact source string U+000D positions; lossless TF 13.1 transport (ADR 0006) | Sparse per-idno-node map feature=comma-separated original character offsets for each literal CR removed from TF string transport; paired reconstruction restores exact source Unicode. |
| `hierarchy.hierarchy_id` | `str` | `derived` | deterministic oraec-hierarchy:path-prefix:sha256(exact ordered label+TLA-href source prefix) | Deterministic identity of an exact ordered hierarchy (label, TLA href) path-prefix occurrence. |
| `hierarchy.hierarchy_label` | `str` | `source` | oraec_hierarchical_path.tsv.column2.component | Exact source label for one hierarchy component. |
| `hierarchy.hierarchy_depth` | `int` | `derived` | 1-based hierarchy component position | One-based component position within the exact source hierarchy path. |
| `hierarchy.tla_url` | `str` | `source` | oraec_hierarchical_path.tsv.column3.href | Exact TLA href parsed from the source linked hierarchy component. |
| `hierarchy.tla_id` | `str` | `derived` | terminal identifier in tla_url | TLA identifier parsed losslessly from tla_url. |
| `hierarchy.tla_kind` | `str` | `derived` | TLA URL path: object or text | Converter-derived TLA target kind (object or text) parsed from tla_url. |
| `hierarchy.hierarchy_cr_offsets` | `str` | `derived` | exact source string U+000D positions; lossless TF 13.1 transport (ADR 0006) | Sparse per-hierarchy-node map feature=comma-separated original character offsets for each literal CR removed from TF string transport; paired reconstruction restores exact source Unicode. |
| `external_ref.external_system` | `str` | `derived` | mapping filename/domain | Converter-derived external namespace determined by the mapping family. |
| `external_ref.external_value` | `str` | `source` | mapping file target column | Exact mapping target identifier or URL from the source table. |
| `external_ref.external_ref_cr_offsets` | `str` | `derived` | exact source string U+000D positions; lossless TF 13.1 transport (ADR 0006) | Sparse per-external_ref-node map feature=comma-separated original character offsets for each literal CR removed from TF string transport; paired reconstruction restores exact source Unicode. |

## Native edge features

Some native TF edges are **valued**: iterate `(target, value)` pairs and retain source order/provenance. Unvalued edges yield target nodes. Text-Fabric `oslots` expresses all node-to-word coverage (the full derived union is independently audited).

| Exact feature | Value type | Origin | Canonical source or derivation | Meaning |
| --- | --- | --- | --- | --- |
| `edge.date` | `int` | `source` | — | Relates a text to an ORAEC date controlled-vocabulary entity; value is the one-based source-list ordinal. |
| `edge.origplace` | `int` | `source` | — | Relates a text to an ORAEC original-place controlled-vocabulary entity; value is the one-based source-list ordinal. |
| `edge.objecttype` | `int` | `source` | — | Relates a text to an ORAEC object-type controlled-vocabulary entity; value is the one-based source-list ordinal. |
| `edge.location` | `int` | `source` | — | Relates a text to an ORAEC location controlled-vocabulary entity; value is the one-based source-list ordinal. |
| `edge.material` | `int` | `source` | — | Relates a text to an ORAEC material controlled-vocabulary entity; value is the one-based source-list ordinal. |
| `edge.author` | `—` | `source` | credits.author | Relates a text exclusively to the exact ORAEC credits.author for that text. README corpus-level contribution does not create a credit edge. |
| `edge.source` | `int` | `source` | — | Relates a text to an exact ORAEC source URL; value is the one-based credits.source ordinal. |
| `edge.idno` | `—` | `source` | — | Relates a text to an idno occurrence node so duplicate source list items remain distinct. |
| `edge.hierarchy` | `—` | `source` | — | Relates an ORAEC text to the leaf occurrence in its exact source hierarchy path. |
| `edge.parent` | `—` | `source` | — | Relates a hierarchy child occurrence to its immediate parent occurrence. |
| `edge.external` | `str` | `source` | — | Relates a native ORAEC entity to an external reference; edge value is the exact mapping filename for provenance. |

## Section, query and interpretation examples

Run the ordinary Text-Fabric API query examples in [`docs/examples.py`](examples.py) with a locally generated TF directory. These examples use `Fabric` rather than converter internals and cover source identity, sentence navigation, lexical spans, morphology/Unicode, ancestor hierarchy, and external mapping identifiers. Consult the pinned-source reproducible build in the project README. The browser uses the standard advanced app under `app/config.yaml`, not an ORAEC-specific web application.
