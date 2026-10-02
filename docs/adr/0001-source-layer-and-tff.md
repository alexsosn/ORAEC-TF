# ADR 0001 — ORAEC source layer and Text-Fabric Factory

Status: accepted  
Issue: #14

Decision: use as implementation/reference material only

## Context

ORAEC-TF materializes the Open Richly Annotated Egyptian Corpus into native Text-Fabric.

The project must decide both:

1. which upstream layer is authoritative for ORAEC-TF semantics; and
2. whether `annotation/text-fabric-factory` should be a converter dependency.

The relevant upstreams are not equivalent representations of the same thing.

- `oraec/corpus_raw_data` is published by ORAEC as the raw data of the ORAEC corpus.
- ORAEC identifies AED and AES as sources for the 13,026 ORAEC text JSON records.
- AED-TEI is a richer TEI source collection: per text it separates base text, sentence translation, cotextual word translation, and hieroglyphic encoding into stand-off XML files and also ships dictionary, thesaurus, and morphology resources.
- ORAEC adds its own corpus-level data, including hierarchical paths and cross-project mappings, and publishes its own derived statistical datasets.

## Evidence from a real aligned text

ORAEC `oraec8036` credits AED text `PLDASMSHTZFIJE3GUCFK2JOZNY`.

The ORAEC record preserves, among other things:

- ORAEC text and token identities;
- title;
- date/original-place/object-type controlled vocabulary IDs;
- bibliography;
- sentence translations;
- word forms;
- line labels;
- lemma IDs/forms;
- POS and grammatical features;
- cotext translations;
- ORAEC's normalized textual rendering.

The AED-TEI base and stand-off files additionally contain source-layer TEI semantics that ORAEC does not export as equivalent structured fields, for example:

- `<supplied reason="lost">`;
- `<damage>`;
- `<gap reason="lost">`;
- AED/TLA XML identifiers for sentences and words;
- `notBefore` / `notAfter` dating bounds;
- physical-support notes;
- TEI publication/revision metadata.

ORAEC normalizes some editorial markup into its transcription strings and omits other AED-specific metadata. Conversely, ORAEC contributes semantics not supplied by a simple AED-TEI conversion, especially ORAEC identifiers, later hierarchy, project mappings, and ORAEC-created derivative layers.

Therefore AED-TEI is not a lossless substitute for the ORAEC release, and rebuilding from AED-TEI would amount to reimplementing ORAEC's own transformation/enrichment pipeline.

## Authoritative source decision

The authoritative semantic input for ORAEC-TF is the pinned snapshot of:

`oraec/corpus_raw_data`

AED, AES, the 2018 BBAW extract, TLA, VÉgA, Trismegistos, Karnak, and other cited resources are upstream provenance/evidence unless ORAEC itself ships a relation to them in the supported snapshot.

Consequences:

- ORAEC-TF models what ORAEC publishes, not every structure in every upstream source.
- AED-TEI-only editorial semantics are not silently reintroduced into ORAEC-TF.
- If a future project wants the richer AED TEI editorial graph, it should be represented by a separate AED-TF corpus or an explicitly aligned enrichment/module with independently justified identity mapping.
- ORAEC source credits and source URLs remain provenance and must be preserved as ORAEC supplies them.
- Full-corpus audit #2 determines the exact in-scope ORAEC semantics before #3 freezes the TF ontology.

## Text-Fabric Factory assessment

Evaluated upstream:

- repository: `annotation/text-fabric-factory`
- observed package version: `1.0.8`
- observed repository head during research: `bae4a39d298ab6a44668b37e565d799d11f9a244`

Text-Fabric Factory provides substantial machinery for:

- generic XML conversion;
- TEI conversion;
- PageXML;
- XML schema analysis/validation;
- app generation;
- convert/load/browse workflows;
- NLP enrichment;
- IIIF/WATM-related workflows.

Its generic XML converter explicitly describes itself as an example rather than a production conversion engine. Its TEI converter is much richer but remains TEI-specific.

ORAEC-TF does not have an XML/TEI primary source contract. Adding Factory as a runtime dependency would therefore introduce source-format abstractions and transitive machinery unrelated to ORAEC JSON+TSV semantics.

Factory also declares an unbounded `text-fabric` dependency, while ORAEC-TF deliberately constrains Text-Fabric to `>=13.1,<14`.

## Reusable design patterns

The useful Factory patterns do not require a Factory dependency.

### Direct `CV` writer

Factory ultimately builds TF through `tf.convert.walker.CV`.

That class already belongs to Text-Fabric itself. ORAEC-TF should implement its writer directly against:

`tf.convert.walker.CV`

The intended boundary is:

```text
pinned ORAEC JSON/TSV
        ↓
ORAEC parser
        ↓
typed canonical IR
        ↓
ORAEC-specific CV director
        ↓
native Text-Fabric
```

The director is corpus-specific and follows the frozen schema from #3. It must not mirror JSON containers mechanically when a different native TF representation is semantically correct.

### Convert → load validation

Factory's pattern of converting and then loading the emitted dataset with `Fabric` is useful.

ORAEC-TF should retain an explicit post-write load gate so malformed warp data, metadata, feature types, and section/text-format contracts are caught by Text-Fabric itself in addition to project-specific validation.

### App configuration

Factory's app generation is useful as reference material, but ORAEC-TF should maintain its own `app/` because its display needs are corpus-specific:

- Egyptian transliteration;
- hieroglyphic rendering;
- ORAEC metadata;
- external identifiers;
- ORAEC section/navigation choices.

### Feature provenance metadata

Factory distinguishes literal/source-derived and converter-derived feature production. ORAEC-TF should preserve the principle, not the TEI-specific vocabulary. The frozen schema may define corpus-appropriate metadata for source vs converter-derived structure.

## Rejected options

### Adopt Factory as the primary converter

Rejected because the primary ORAEC input is JSON+TSV, not XML/TEI, and because a generic serialization-driven converter would not decide the scholarly TF ontology.

### Convert AED-TEI and reconstruct ORAEC

Rejected because it would require reimplementing ORAEC's normalization/enrichment logic and would not faithfully reproduce the published ORAEC corpus without additional ORAEC inputs.

### Hybrid mandatory ORAEC + AED conversion

Rejected as the baseline because it introduces two semantic authorities and makes reproducibility dependent on cross-version alignment. AED may remain evidence for audits or future optional alignment work.

### Add Factory only for `CV`

Rejected because `CV` is already part of `text-fabric`.

## Consequences for open issues

- #2 audits the pinned ORAEC distribution, not AED-TEI as a second mandatory input.
- #3 freezes a semantic ORAEC TF ontology rather than an XML serialization model.
- #5 parses ORAEC JSON/TSV into a typed IR.
- #6 should use `tf.convert.walker.CV` directly unless real corpus evidence demonstrates a concrete reason not to.
- #9 may borrow app ideas from Factory but owns an ORAEC-specific advanced app.
- #11 remains a thin Agora acquisition/execution contract around the ORAEC-TF converter.

## Dependency decision

Do **not** add `text-fabric-factory` to ORAEC-TF runtime or development dependencies for the current architecture.

Revisit this ADR only if ORAEC changes its canonical distribution format, or a future requirement specifically needs a Factory-owned capability that cannot be obtained directly from Text-Fabric without duplicating substantial maintained logic.
