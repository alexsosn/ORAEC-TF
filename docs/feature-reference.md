# ORAEC-TF native Text-Fabric feature reference

Schema version: 2

Source: `schema/core.json` (the authoritative frozen schema).
This document is generated; do not edit it independently.

## Native graph model

Slot type: `word`.
Node types: 10. Node features: 58. Edge features: 11.

Each feature records its source/derived provenance and value type.
No external web endpoint is inferred from a node identifier.

## Node features

### `word`

Source identity: token_id.
Slot mapping: self.

|Feature|Origin|Value type|Source field(s)|Description|
|---|---|---|---|---|
|`token_id`|Source|str|token.token|Exact ORAEC token identifier for a real source word.|
|`written_form`|Source|str|token.written_form|Exact ORAEC transliterated written form.|
|`cotext_translation`|Source|str|token.cotext_translation|Exact ORAEC token-level cotext translation.|
|`hiero`|Source|str|token.hiero|Exact ORAEC Unicode hieroglyphic string; never repaired or normalized.|
|`line_count`|Source|str|token.lineCount|Exact ORAEC lineCount string including source whitespace.|
|`pos`|Source|str|token.pos|Exact ORAEC part-of-speech value.|
|`name_type`|Source|str|token.name|Exact ORAEC name subtype from token.name.|
|`number_type`|Source|str|token.number|Exact ORAEC number subtype from token.number.|
|`voice`|Source|str|token.voice|Exact ORAEC grammatical voice.|
|`genus`|Source|str|token.genus|Exact ORAEC grammatical genus/gender label.|
|`pronoun_type`|Source|str|token.pronoun|Exact ORAEC pronoun subtype.|
|`numerus`|Source|str|token.numerus|Exact ORAEC grammatical number label.|
|`epitheton`|Source|str|token.epitheton|Exact ORAEC epitheton/title subtype.|
|`morphology`|Source|str|token.morphology|Exact ORAEC morphology marker.|
|`inflection`|Source|str|token.inflection|Exact ORAEC inflection label.|
|`adjective_type`|Source|str|token.adjective|Exact ORAEC adjective subtype.|
|`particle_type`|Source|str|token.particle|Exact ORAEC particle subtype.|
|`adverb_type`|Source|str|token.adverb|Exact ORAEC adverb subtype.|
|`verbal_class`|Source|str|token.verbalClass|Exact ORAEC verbalClass value.|
|`status`|Source|str|token.status|Exact ORAEC grammatical status value.|
|`is_anchor`|Derived|int|ADR 0002 zero-token sentence compatibility|Marks the three converter-derived compatibility slots required for zero-token source sentences.|
|`trailer`|Derived|str|text display spacing; empty on anchors|Converter-derived display trailer: one space on real words and empty on technical anchors.|
|`word_cr_offsets`|Derived|str|exact source string U+000D positions; lossless TF 13.1 transport (ADR 0006)|Sparse per-word-node map feature=comma-separated original character offsets for each literal CR removed from TF string transport; paired reconstruction restores exact source Unicode.|

### `sentence`

Source identity: oraec_id+sentence_index.
Slot mapping: contained_words.

|Feature|Origin|Value type|Source field(s)|Description|
|---|---|---|---|---|
|`sentence_index`|Derived|int|1-based record.sentences array position|One-based source sentence array position within its ORAEC text.|
|`translation`|Source|str|sentence.translation|Exact ORAEC sentence translation; empty string is distinct from absence.|
|`sentence_cr_offsets`|Derived|str|exact source string U+000D positions; lossless TF 13.1 transport (ADR 0006)|Sparse per-sentence-node map feature=comma-separated original character offsets for each literal CR removed from TF string transport; paired reconstruction restores exact source Unicode.|

### `text`

Source identity: oraec_id.
Slot mapping: contained_words.

|Feature|Origin|Value type|Source field(s)|Description|
|---|---|---|---|---|
|`oraec_id`|Source|str|record.oraecid|Exact stable ORAEC text identifier.|
|`title`|Source|str|record.title|Exact ORAEC text title.|
|`bibliography`|Source|str|record.bibliography|Exact ORAEC bibliography string when present.|
|`condition`|Source|str|record.condition|Exact ORAEC condition value when present.|
|`license`|Source|str|credits.license|Exact per-text ORAEC credits.license value.|
|`text_cr_offsets`|Derived|str|exact source string U+000D positions; lossless TF 13.1 transport (ADR 0006)|Sparse per-text-node map feature=comma-separated original character offsets for each literal CR removed from TF string transport; paired reconstruction restores exact source Unicode.|

### `lex`

Source identity: lemma_id.
Slot mapping: union_of_occurrence_words.

|Feature|Origin|Value type|Source field(s)|Description|
|---|---|---|---|---|
|`lemma_id`|Source|str|token.lemmaID|Exact ORAEC lemmaID used as shared lexical identity.|
|`lemma_form`|Source|str|token.lemma_form|Exact ORAEC lemma_form associated with lemma_id.|
|`lex_cr_offsets`|Derived|str|exact source string U+000D positions; lossless TF 13.1 transport (ADR 0006)|Sparse per-lex-node map feature=comma-separated original character offsets for each literal CR removed from TF string transport; paired reconstruction restores exact source Unicode.|

### `cv`

Source identity: cv_kind+cv_id.
Slot mapping: union_of_referencing_text_words.

|Feature|Origin|Value type|Source field(s)|Description|
|---|---|---|---|---|
|`cv_kind`|Derived|str|source record field name|Converter-derived controlled-vocabulary domain name.|
|`cv_id`|Source|str|record.<cv_kind>[].id|Exact ORAEC controlled-vocabulary identifier.|
|`cv_label`|Source|str|record.<cv_kind>[].<cv_kind>|Exact ORAEC controlled-vocabulary display label.|
|`cv_cr_offsets`|Derived|str|exact source string U+000D positions; lossless TF 13.1 transport (ADR 0006)|Sparse per-cv-node map feature=comma-separated original character offsets for each literal CR removed from TF string transport; paired reconstruction restores exact source Unicode.|

### `author`

Source identity: author_name.
Slot mapping: all_corpus_words_if_corpus_author_else_union_of_referencing_text_words.

|Feature|Origin|Value type|Source field(s)|Description|
|---|---|---|---|---|
|`author_name`|Source|str|credits.author, README author column for oraec1.json .. oraec13026.json|Exact ORAEC credits.author string.|
|`is_corpus_author`|Source|int|README author column for oraec1.json .. oraec13026.json|Marks an exact author identity declared for the full ORAEC JSON corpus family in the upstream README.|
|`corpus_author_index`|Derived|int|1-based order in README author column for oraec1.json .. oraec13026.json|Preserves the source order of corpus-level authors declared in the upstream README.|
|`author_cr_offsets`|Derived|str|exact source string U+000D positions; lossless TF 13.1 transport (ADR 0006)|Sparse per-author-node map feature=comma-separated original character offsets for each literal CR removed from TF string transport; paired reconstruction restores exact source Unicode.|

### `source_ref`

Source identity: source_url.
Slot mapping: union_of_referencing_text_words.

|Feature|Origin|Value type|Source field(s)|Description|
|---|---|---|---|---|
|`source_url`|Source|str|credits.source[]|Exact ORAEC credits.source URL.|
|`source_ref_cr_offsets`|Derived|str|exact source string U+000D positions; lossless TF 13.1 transport (ADR 0006)|Sparse per-source_ref-node map feature=comma-separated original character offsets for each literal CR removed from TF string transport; paired reconstruction restores exact source Unicode.|

### `idno`

Source identity: oraec_id+idno_index.
Slot mapping: owning_text_words.

|Feature|Origin|Value type|Source field(s)|Description|
|---|---|---|---|---|
|`idno_value`|Source|str|record.idno[]|Exact ORAEC idno list item, including duplicate occurrences.|
|`idno_index`|Derived|int|1-based record.idno list position|One-based source idno list position.|
|`idno_cr_offsets`|Derived|str|exact source string U+000D positions; lossless TF 13.1 transport (ADR 0006)|Sparse per-idno-node map feature=comma-separated original character offsets for each literal CR removed from TF string transport; paired reconstruction restores exact source Unicode.|

### `hierarchy`

Source identity: exact_path_prefix.
Slot mapping: union_of_descendant_text_words.

|Feature|Origin|Value type|Source field(s)|Description|
|---|---|---|---|---|
|`hierarchy_id`|Derived|str|deterministic oraec-hierarchy:path-prefix:sha256(exact ordered label+TLA-href source prefix)|Deterministic identity of an exact ordered hierarchy (label, TLA href) path-prefix occurrence.|
|`hierarchy_label`|Source|str|oraec_hierarchical_path.tsv.column2.component|Exact source label for one hierarchy component.|
|`hierarchy_depth`|Derived|int|1-based hierarchy component position|One-based component position within the exact source hierarchy path.|
|`tla_url`|Source|str|oraec_hierarchical_path.tsv.column3.href|Exact TLA href parsed from the source linked hierarchy component.|
|`tla_id`|Derived|str|terminal identifier in tla_url|TLA identifier parsed losslessly from tla_url.|
|`tla_kind`|Derived|str|TLA URL path: object or text|Converter-derived TLA target kind (object or text) parsed from tla_url.|
|`hierarchy_cr_offsets`|Derived|str|exact source string U+000D positions; lossless TF 13.1 transport (ADR 0006)|Sparse per-hierarchy-node map feature=comma-separated original character offsets for each literal CR removed from TF string transport; paired reconstruction restores exact source Unicode.|

### `external_ref`

Source identity: external_system+external_value.
Slot mapping: union_of_referencing_native_node_words.

|Feature|Origin|Value type|Source field(s)|Description|
|---|---|---|---|---|
|`external_system`|Derived|str|mapping filename/domain|Converter-derived external namespace determined by the mapping family.|
|`external_value`|Source|str|mapping file target column|Exact mapping target identifier or URL from the source table.|
|`external_ref_cr_offsets`|Derived|str|exact source string U+000D positions; lossless TF 13.1 transport (ADR 0006)|Sparse per-external_ref-node map feature=comma-separated original character offsets for each literal CR removed from TF string transport; paired reconstruction restores exact source Unicode.|

## Edge features

|Feature|Origin|From → to|Value type|Value meaning|Description|
|---|---|---|---|---|---|
|`date`|Source|text → cv|int|source_list_ordinal|Relates a text to an ORAEC date controlled-vocabulary entity; value is the one-based source-list ordinal.|
|`origplace`|Source|text → cv|int|source_list_ordinal|Relates a text to an ORAEC original-place controlled-vocabulary entity; value is the one-based source-list ordinal.|
|`objecttype`|Source|text → cv|int|source_list_ordinal|Relates a text to an ORAEC object-type controlled-vocabulary entity; value is the one-based source-list ordinal.|
|`location`|Source|text → cv|int|source_list_ordinal|Relates a text to an ORAEC location controlled-vocabulary entity; value is the one-based source-list ordinal.|
|`material`|Source|text → cv|int|source_list_ordinal|Relates a text to an ORAEC material controlled-vocabulary entity; value is the one-based source-list ordinal.|
|`author`|Source|text → author|—|—|Relates a text exclusively to the exact ORAEC credits.author for that text. README corpus-level contribution does not create a credit edge.|
|`source`|Source|text → source_ref|int|source_list_ordinal|Relates a text to an exact ORAEC source URL; value is the one-based credits.source ordinal.|
|`idno`|Source|text → idno|—|—|Relates a text to an idno occurrence node so duplicate source list items remain distinct.|
|`hierarchy`|Source|text → hierarchy|—|leaf_membership|Relates an ORAEC text to the leaf occurrence in its exact source hierarchy path.|
|`parent`|Source|hierarchy → hierarchy|—|child_to_parent|Relates a hierarchy child occurrence to its immediate parent occurrence.|
|`external`|Source|text, lex, cv, author → external_ref|str|source_mapping_filename|Relates a native ORAEC entity to an external reference; edge value is the exact mapping filename for provenance.|

## Interpretation and limitations

- Linguistic fields, lineCount, and hieroglyphic Unicode are preserved
  from source annotations; technical anchor slots are derived.
- The source `lineCount` is a token annotation, not a constructed
  line-node hierarchy. Never infer line identity from its string.
- Schema v2 source U+000D (CR) is reconstructed losslessly from the
  native value feature and its `<node_type>_cr_offsets` feature.
  Direct feature values containing CR in source are TF-safe transport
  strings, not exact raw strings until reconstructed (ADR 0006).
- Per-text authorship is represented by source credit relations.
  README corpus-level contributors do not create invented text credits.
- Hierarchy nodes represent exact linked path prefixes, including
  potentially empty source labels.
- Licensed Trismegistos, Wikidata and Vega mappings are native TF
  relations. Karnak mapping TSVs remain excluded pending licensing.
- The source corpus and generated TF feature data are acquired or
  built separately, not committed to this software repository.
