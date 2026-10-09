# ADR 0005 — Freeze the native ORAEC Text-Fabric schema

Status: accepted  
Issue: #3  
Machine-readable contract: schema/core.json  
Supported ORAEC source: b83a0ee5fae27a40d4c0a2a9a8c9c2973d45e9cd

## Decision

ORAEC-TF freezes a native Text-Fabric graph whose slot type is word.

This follows the BHSA convention because ORAEC annotation is overwhelmingly word/token-centred: the supported snapshot has 815,026 real source-token occurrences. ADR 0002 requires only three exceptional technical anchors, so choosing a generic slot type for the entire corpus would make the ordinary researcher API less natural in order to accommodate three compatibility records.

The resulting warp contains 815,029 slots:

- 815,026 real ORAEC word/token occurrences;
- 3 technical anchor slots required by the zero-token sentence cases.

Technical anchors are explicitly marked by is_anchor=1, render as empty text, and carry none of the source-token linguistic features.

The core graph has no core `line` nodes. ADR 0004 establishes that lineCount is exact token-level source annotation, not a safe structural line identity.

No semantic sidecars are required to query any in-scope corpus semantics. JSON, XML, TSV, or report files may be used as acquisition inputs or provenance/validation artifacts, but not as the sole representation of corpus content.

## Text-Fabric node types

The frozen node types are:

- word — slot type, one per source token plus the three ADR 0002 anchors;
- sentence — one per source sentence;
- text — one per ORAEC text;
- lex — shared lexical entity keyed by lemmaID;
- cv — shared ID-backed controlled-vocabulary entity;
- author — shared exact credits author;
- source_ref — shared exact credits source URL;
- idno — one occurrence node per source idno list item;
- hierarchy — one exact hierarchy path-prefix occurrence;
- external_ref — shared external target within one external namespace.

There is deliberately no line node type.

## Word features

Every real word preserves the source token identifier and every audited token field without semantic compression.

Direct word features are:

- token_id from token.token;
- written_form;
- cotext_translation;
- hiero;
- line_count from lineCount;
- pos;
- name_type from name;
- number_type from number;
- voice;
- genus;
- pronoun_type from pronoun;
- numerus;
- epitheton;
- morphology;
- inflection;
- adjective_type from adjective;
- particle_type from particle;
- adverb_type from adverb;
- verbal_class from verbalClass;
- status.

The renamed TF features are only ergonomic names. Their sourceField metadata records the exact ORAEC field, and their source strings are preserved exactly.

The two token fields lemmaID and lemma_form are not duplicated on words. They define the shared lex node described below.

Derived word features are:

- is_anchor — sparse integer marker, value 1 only for ADR 0002 anchors;
- trailer — display spacing, one space for real words and the empty string for anchors.

## Sentence nodes

Sentence identity is the pair ORAEC text ID + 1-based source sentence index.

Features:

- sentence_index — derived 1-based array position;
- translation — exact source sentence.translation.

Text-Fabric string features distinguish the empty string from absence. Therefore the 1,163 source translations equal to the empty string are stored as the empty string; no sentinel value is invented.

Every sentence has oslots equal to its contained word slots. For the three zero-token source sentences, the single technical anchor provides the required Text-Fabric slot linkage without fabricating an Egyptian word.

## Text nodes

Text identity is exact oraecid.

Features:

- oraec_id;
- title;
- bibliography when present;
- condition when present;
- license from credits.license.

Text oslots are all slots in the text, including a technical anchor when one is needed to preserve an otherwise zero-token sentence.

## Lexical entities

The full audit found 18,733 distinct lemma IDs and no case where one lemmaID maps to multiple lemma_form values.

ORAEC-TF therefore follows the BHSA lexeme precedent:

- one lex node per exact lemmaID;
- lemma_id stores lemmaID;
- lemma_form stores the associated exact lemma_form;
- lex oslots are the union of all occurrence words carrying that lemmaID.

A separate word-to-lex edge is unnecessary because the lex node's oslots already provide the standard Text-Fabric occurrence relation.

Any lemma ID/form conflict in a future supported source revision fails closed.

## Controlled vocabulary

The audited date, origplace, objecttype, location, and material lists have stable IDs and no ID-to-label collisions.

They become shared cv nodes keyed by cv_kind + cv_id, with:

- cv_kind — derived from the source record field;
- cv_id — exact source item ID;
- cv_label — exact source label.

Text-to-cv edge features are named date, origplace, objecttype, location, and material.

Each edge value is the 1-based source-list ordinal. This preserves order and multiplicity rather than packing arrays into string features.

If the same target would occur twice in one list, Text-Fabric's single-value-per-edge semantics would collapse the occurrence. Such a future source case fails closed until an occurrence-node representation is designed.

## idno occurrences

The supported source has idno on 3,803 texts and every current idno list contains the same value twice.

A normal text-to-value edge would lose this source multiplicity. Therefore each list item becomes an idno occurrence node keyed by ORAEC text ID + 1-based idno index.

Features:

- idno_value — exact source string;
- idno_index — derived 1-based list position.

The text-to-idno edge is unvalued. This is the intentional idno occurrence model and preserves duplicate source list items exactly.

## Credits and provenance entities

`author_name` is a shared exact-source identity whose provenance may be either per-text `credits.author` or the README corpus-author list. The machine schema records both source loci rather than pretending every author name came from per-text credits.

The upstream README also declares an exact corpus-level author list for the `oraec1.json .. oraec13026.json` family. Those names instantiate the same author identity domain. Membership is preserved by sparse source feature `is_corpus_author=1`, and `corpus_author_index` preserves the 1-based order of the README author list. Duplicate names in that ordered corpus-author list fail closed because one shared author identity cannot losslessly carry two source positions. This is required by real data: Wikidata key `Renata Landgrafova` is present in the README author list but does not occur as a per-text `credits.author` value.

credits.source list items become shared source_ref nodes keyed by exact source_url. The text-to-source edge value stores the 1-based source-list ordinal.

credits.license remains an exact text feature because it is a scalar property of the text record.

Author nodes referenced by per-text credits obtain the union of those text slots. Corpus-level authors obtain all corpus word slots, which supplies a Text-Fabric 13.1 oslots anchor for their corpus-wide provenance scope. `is_corpus_author` distinguishes that source claim from per-text authorship. source_ref nodes obtain slots from referencing texts.

## Source hierarchy

oraec_hierarchical_path.tsv is a path serialization, not an opaque feature value.

Each hierarchy component is represented by a hierarchy path-occurrence node. Its identity is the exact ordered prefix of source (label, TLA href) pairs, encoded deterministically as a namespaced SHA-256 key. Including both values prevents equal display labels that point at different upstream objects from collapsing.

This deliberately does not use the TLA URL as the node identity. A stable TLA object/text identifier is valuable upstream identity, but assuming that one TLA entity always has one ORAEC parent/depth could collapse distinct source path contexts.

Hierarchy node features are:

- hierarchy_id — deterministic path-prefix identity;
- hierarchy_label — exact source component label, including the empty string when the source component label is empty;
- hierarchy_depth — derived 1-based component position;
- tla_url — exact source href from the linked path;
- tla_id — identifier parsed from that URL;
- tla_kind — object or text parsed from the URL path.

parent edges run child to immediate parent. A text-to-hierarchy edge links each ORAEC text to the leaf path occurrence.

Hierarchy oslots are the union of descendant text slots.

Empty hierarchy labels are legitimate source values, not missing components. The pinned snapshot has five empty linked labels; four are trailing components and `oraec12216` is a one-component path whose plain label is the empty string and whose linked component points to TLA text `JPGGWWBWTBEFXPBJNMCQQSYSW4`. Exact path-prefix identity includes the empty label plus its href.

Conversion fails closed if label/link component counts disagree after preserving empty components, a linked component does not contain exactly one supported TLA href, deterministic identities collide, or the source parentage cannot be reconstructed exactly.

## External mappings

External targets become external_ref nodes keyed by external_system + exact external_value.

The external edge links a native source entity to the external_ref. Its string edge value is the exact source mapping filename, which makes relation provenance directly queryable in TF.

Supported release mappings are:

- mapping_oraec_trismegistos.csv: text to Trismegistos reference;
- mapping_oraec_lemmata_vega.tsv: lex to VÉgA reference;
- mapping_oraec_wikidata.tsv: author or cv to Wikidata reference.

Wikidata source keys are heterogeneous. A key must resolve exactly once, either to exact author_name or exact cv_id. No match or more than one match fails closed.

The Karnak text and lemma mapping files remain excluded from distributable materializations under issue #17. Their source semantics may be researched and tested, but they are not included in a release until explicit file-level licence clarification exists.

## Derived upstream analytical files

The collocation and statistics directories are reproducible ORAEC-derived analytical outputs. They are not copied into the authoritative core graph.

Equivalent analyses may later be exposed as queries, reports, or optional modules. If a future audit discovers non-reconstructible semantics in those files, that datum requires an explicit schema change rather than an opaque blob.

## Edge features

Frozen core edge features are:

- date, origplace, objecttype, location, material: text to cv, valued by source-list ordinal;
- author: text to author;
- source: text to source_ref, valued by source-list ordinal;
- idno: text to idno occurrence;
- hierarchy: text to hierarchy leaf occurrence;
- parent: hierarchy child to hierarchy parent;
- external: text, lex, cv, or author to external_ref, valued by mapping filename.

One-to-many external mappings remain separate edges and are never delimiter-packed. Mapping-table row order is treated as serialization rather than scholarly semantics: the conserved object is the exact relation pair plus its mapping-file provenance. This is safe for the audited supported files, whose source keys are unique except for the explicitly one-to-many Karnak lemma table, which is currently release-excluded.

## Sections

The Text-Fabric section system is:

- sectionTypes: text,sentence;
- sectionFeatures: oraec_id,sentence_index.

This gives stable navigation by ORAEC text ID and sentence number while matching the actual source hierarchy of the edition itself.

The variable-depth ORAEC metadata hierarchy is not configured as a fixed Text API structure. It remains the native hierarchy graph above.

## Text formats

The frozen otext formats are:

- text-orig-full = {written_form}{trailer};
- text-translit = {written_form}{trailer};
- text-hiero = {hiero}{trailer};
- lex-default = {lemma_form}.

Text-Fabric treats an undefined feature as empty output in a format and treats an explicit empty string as a real value. Therefore anchors render empty without fabricated written_form or hiero values.

Issue #9 may add presentation-oriented formats after the core schema, but it may not redefine these source features or silently normalize them.

## Source and derived feature provenance

Every generated feature carries metadata declaring:

- valueType;
- origin = source or derived;
- description.

Source features also declare sourceField. Derived features declare derivedFrom.

This makes converter-derived conveniences such as sentence_index, cv_kind, hierarchy_id, trailer, and is_anchor distinguishable from ORAEC-authored strings.

Exact source strings are not stripped, normalized, repaired, case-folded, Unicode-normalized, or otherwise rewritten.

## Oslots strategy

Text-Fabric 13.1 removes or cannot serialize unlinked non-slot nodes. Every native entity therefore has an explicit oslots strategy:

- sentence and text: contained words;
- lex: union of occurrence words;
- cv and source_ref: union of words in referencing texts;
- author: all corpus words for README corpus authors, otherwise union of words in referencing texts;
- idno: words of its owning text;
- hierarchy: union of descendant text words;
- external_ref: union of the slots of native entities that map to it.

If an in-scope semantic entity cannot acquire slots under these rules, materialization fails closed instead of creating a hidden sidecar or silently dropping the entity.

## Fail-closed boundary

The parser/materializer must fail closed on at least:

- an unknown source field;
- an unsupported source shape or type;
- a lemma ID/form conflict;
- a controlled-vocabulary ID/label conflict;
- a duplicate relation that a Text-Fabric edge would collapse;
- an unresolved or ambiguous Wikidata key;
- malformed hierarchy label/link alignment;
- hierarchy identity/parentage conflicts or hash collision;
- an unsupported or unlicensed mapping family;
- an unlinked non-slot semantic node;
- any attempted normalization of an exact source string.

The idno occurrence model is the explicit exception to the generic duplicate-edge failure because it was designed specifically to preserve known duplicate source occurrences.

## Conservation targets

For the pinned source, later implementation and independent validation must establish at minimum:

- 13,026 text nodes;
- 101,796 sentence nodes;
- 815,026 real source-word slots;
- 3 technical anchor slots;
- 815,029 total word slots;
- 18,733 lex nodes;
- exact source equality for every modeled source string;
- no source record, sentence, token, supported hierarchy component, metadata relation, or supported external mapping silently dropped.

Issues #5, #6, and #7 implement this schema. Issue #8 independently rereads the source and validates the generated graph rather than trusting the writer's own bookkeeping.
