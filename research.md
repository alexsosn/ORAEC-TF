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

## R-002 — authoritative source layer and Text-Fabric Factory

Date: 2026-10-03  
Issue: #14  
ADR: `docs/adr/0001-source-layer-and-tff.md`

ORAEC's own README describes `oraec/corpus_raw_data` as the raw data of the ORAEC corpus and names AED/AES as sources of the 13,026 JSON text records.

A real aligned comparison was made between `oraec8036` and AED text `PLDASMSHTZFIJE3GUCFK2JOZNY`. ORAEC carries its own IDs and normalized token/lemma/morphology/translation representation. AED-TEI additionally carries TEI-specific editorial structures and metadata such as `supplied`, `damage`, `gap`, AED/TLA XML IDs, dating bounds, and physical-support notes. ORAEC also adds corpus-level hierarchy and mappings not supplied by a plain AED-TEI conversion.

Conclusion: the pinned ORAEC distribution is the semantic authority for ORAEC-TF. AED/AES and the earlier BBAW/TLA resources are provenance and evidence, not a second mandatory source layer.

`annotation/text-fabric-factory` 1.0.8 was inspected at repository head `bae4a39d298ab6a44668b37e565d799d11f9a244`. It is primarily XML/TEI/PageXML conversion tooling. Its generic XML converter explicitly presents itself as an example, while its richer production machinery is TEI-specific.

The useful graph-building mechanism, `tf.convert.walker.CV`, already belongs to Text-Fabric 13.1.0. ORAEC-TF will therefore use `CV` directly after its typed IR rather than adding Text-Fabric Factory as a dependency.

Reusable patterns from Factory are:
- corpus-specific `CV` director;
- convert → load validation;
- generated-dataset validation through `Fabric`;
- selected app/provenance design ideas.

Factory remains reference material only.

## R-003 — complete pinned-source audit

Date: 2026-10-03  
Issue: #2  
Report: `docs/research/source-audit.md`

The reproducible full-source audit establishes the complete record/sentence/token field census, stable text/token identities, controlled-vocabulary inventories, mapping multiplicities, hierarchy serialization, provenance regularities, and licence coverage for the supported snapshot.

It also found schema-sensitive cases absent from the initial sample: `material`, duplicated source `idno` pairs, three zero-token sentences, highly non-numeric `lineCount` values with source whitespace, and hieroglyphic placeholders/U+FFFD. Collocation/statistics files are classified as reconstructible ORAEC-derived analytical products rather than primary text semantics.

Follow-up: #17, #19, #20, #21. #3 should consume #19/#20 before freezing structural semantics.


## R-004 — zero-token sentence representation

Date: 2026-10-03  
Issue: #20  
ADR: `docs/adr/0002-zero-token-sentences.md`

The three zero-token ORAEC sentences were checked against their AED-TEI provenance. They represent three distinct source situations: a sentence containing only a line-break marker, a genuinely empty sentence, and a genuinely empty sentence with a non-empty stand-off translation.

Text-Fabric `v13.1.0` was inspected at commit `dd227ce62b5536de53a0e20eac98c0459da8fd3d`. Although the conceptual data-model documentation mentions nodes with no slots, the released CV/writer/reader path removes or rejects unlinked non-slot nodes and cannot round-trip an empty `oslots` target set.

ADR 0002 therefore requires exactly one explicitly marked technical anchor slot per zero-token source sentence, while rejecting the more misleading alternative of attaching an empty sentence to a neighbouring real token slot. The final slot-type name remains a #3 decision.


## R-006 — ORAEC hieroglyphic placeholder/replacement semantics

Date: 2026-10-03  
Issue: #21  
ADR: `docs/adr/0003-hieroglyphic-preservation.md`

The pinned ORAEC corpus contains 13,198 exact `[⯑]` hieroglyphic values and 6,545 values containing U+FFFD. These were checked against real AED stand-off files and ORAEC's own `formerly-mdc-now_unicode` producer repository.

The producer mapping explicitly maps uncertainty/control codes such as `HASH` and `hatching` to `[⯑]`, while numerous custom/unencoded sign identifiers such as `US85Aa1002XT` map to U+FFFD. AED comparison additionally shows that ORAEC may emit `[⯑]` for graphemically uncertain material even when AED contains Unicode signs inside `<unclear>`.

The markers therefore encode upstream transformation state and must remain exact source values in the core corpus. AED/MdC recovery is optional enrichment, not a core dependency, and must never overwrite `hiero`.
