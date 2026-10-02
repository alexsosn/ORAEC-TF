# Research

This file records research that constrains implementation. It is evidence, not a frozen schema.

## R-001 — initial ORAEC source reconnaissance

Date: 2026-10-02

### Upstream identity

Repository: `https://github.com/oraec/corpus_raw_data`

Current supported snapshot:

`b83a0ee5fae27a40d4c0a2a9a8c9c2973d45e9cd`

GitHub reports that commit as 2024-06-03, message `Add files via upload`.

The repository tree contains exactly **13,026** root files matching `oraec\d+.json`. The source repository also contains corpus-level mapping files, a large `oraec_hierarchical_path.tsv`, `collocation/`, and `statistics/`.

### Sampled per-text JSON structure

Direct inspection of source records across a size-stratified sample establishes this recurring structure.

Text-level fields observed:
- `oraecid`
- `title`
- `sentences`
- `credits`
- optionally `bibliography`, `date`, `origplace`, `objecttype`, `idno`, `location`

Sentence-level fields observed:
- `token`
- `translation`

Token-level fields observed:
- `token`
- `written_form`
- `hiero`
- `lineCount`
- `cotext_translation`
- `lemma_form`
- `lemmaID`
- `pos`
- `name`
- `number`
- `voice`
- `genus`
- `pronoun`
- `numerus`
- `epitheton`
- `morphology`
- `inflection`
- `adjective`
- `particle`
- `adverb`
- `verbalClass`
- `status`

This is not yet a complete corpus-wide field census. Issue #2 must compute it over all 13,026 records rather than treating the sample as exhaustive.

Examples demonstrate that:
- the same text can have multiple date values;
- grammatical features are sparse and part-of-speech-dependent;
- tokens without lexical analysis remain real tokens;
- `lineCount` is source data and can contain non-trivial labels, not just integers;
- `hiero` is a word-form-level hieroglyphic representation where present;
- each token has a stable-looking ORAEC token ID of the form `oraecTEXT-SENTENCE-TOKEN`, but uniqueness and regularity still require corpus-wide validation.

### Corpus-level mappings

Observed files include:
- `mapping_oraec_trismegistos.csv`
- `mapping_oraec_wikidata.tsv`
- `mapping_oraec_lemmata_vega.tsv`
- `mapping_oraec_karnak.tsv`
- `mapping_oraec_lemmata_karnak.tsv`
- `oraec_hierarchical_path.tsv`

The Trismegistos table maps ORAEC text IDs to Trismegistos Text IDs. The VÉgA table maps ORAEC/AED lemma IDs to VÉgA entry URLs. Karnak mappings are visibly one-to-many in at least some lemma cases, so any later TF design must not flatten them into a single value.

ORAEC documents its hierarchical path as context around individual text records. That makes hierarchy a candidate for corpus semantics rather than display-only metadata; issue #2 must audit its exact structure before issue #3 models it.

### Derived datasets

The upstream README labels all files in `collocation/` and `statistics/` as CC0. The statistics tree includes hieroglyph-frequency and TF-IDF/type-token material.

Working hypothesis: derived statistics that are fully reproducible from the native TF graph should not become duplicated authoritative corpus semantics. Issue #2 must classify every such family before issue #3 freezes the schema. If an upstream file contributes information not reconstructible from the core corpus, that fact must be modelled explicitly or the file must be documented as intentionally out of scope.

### Licence evidence

The upstream README explicitly assigns:
- core `oraec*.json`, hierarchy, and VÉgA lemma mapping: CC BY-SA 4.0;
- Trismegistos/Wikidata mappings, collocations, and statistics: CC0.

The pinned tree also contains two Karnak mapping files that are not listed in that licence table. Treat their redistribution status as unresolved until issue #2 records authoritative evidence.

### BHSA design reference

Current ETCBC/BHSA uses `word` as the slot type and represents larger linguistic structures and lexical entities as nodes. Its advanced app uses `app/config.yaml` with `apiVersion: 3`, provenance configuration, type display, and writing-system configuration.

ORAEC-TF may reuse BHSA patterns only when ORAEC supplies equivalent semantics. The current working hypothesis is word slots, with sentence/text and likely lexical/hierarchy layers above them. Issue #3 must decide this from the full audit.

### Agora contract research

Agora's materializer registry treats the third-party converter as owner of parsing and corpus semantics. A materializer manifest can declare Git acquisition, pass the acquired directory to a Python module, deny network during execution, and require Text-Fabric warp output plus provenance/validation reports.

ORAEC-TF should therefore support direct local conversion first. Agora integration must remain thin: acquisition and execution orchestration belong downstream; ORAEC parsing and TF modelling belong here.

## Open research questions

Issue #2 must answer at least:

- complete field/type/cardinality census across all records;
- whether any source object or token IDs collide;
- the full grammar/value vocabularies and anomalous values;
- all forms and semantics of `lineCount`;
- exact schema and identity semantics of `oraec_hierarchical_path.tsv`;
- whether text/date/place/object-type lists have stable IDs that warrant shared entity nodes;
- whether credits/authors should be entity nodes, edge relations, or source-faithful text metadata;
- the precise relation between `lemmaID`, `lemma_form`, and corpus-level lemma mappings;
- whether all hierarchy/mapping files are licensed for redistribution in the generated adaptation;
- whether any collocation/statistics artifacts encode non-reconstructible information.
