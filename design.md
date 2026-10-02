# Design

Status: **working architecture; TF schema not frozen**.

Issue #3 freezes the graph model after issues #2 and #14 establish the complete source contract and source-layer boundary.

## Goals

ORAEC-TF must produce a complete, queryable Text-Fabric representation of the supported ORAEC corpus without requiring access to the original JSON/TSV files after materialization.

The generated corpus must preserve research semantics in native TF nodes, node features, and edge features.

## Non-goals

- storing an upstream ORAEC checkout in this repository;
- storing generated TF data in this repository;
- embedding raw JSON/XML or arbitrary serialized objects in TF features;
- using semantic sidecars as a shortcut around graph modelling;
- inventing linguistic analyses or repairing scholarly content silently;
- reconstructing every AED-TEI semantic that ORAEC itself does not publish;
- replacing the ORAEC website as the source project's editorial interface.

## Authoritative source layer

The pinned `oraec/corpus_raw_data` snapshot is the semantic authority for ORAEC-TF.

AED, AES, the 2018 BBAW extract, TLA, and other cited projects remain provenance and research evidence unless the ORAEC distribution itself ships a relation to them.

This prevents the converter from silently becoming a reconstruction of AED or TLA rather than a materializer of ORAEC. See `docs/adr/0001-source-layer-and-tff.md`.

## Source and build boundary

```text
Agora/manual acquisition
  -> immutable local ORAEC source checkout
  -> source audit/parser
  -> typed canonical IR
  -> ORAEC-specific tf.convert.walker.CV director
  -> native TF graph
  -> independent conservation validator
  -> ephemeral/release artifact
```

The converter stage is network-free.

Text-Fabric Factory is not a runtime dependency. Its useful `CV/director`, convert→load, app, and provenance patterns are reference material. The graph writer uses Text-Fabric's own `tf.convert.walker.CV` directly.

The repository may ship provenance/validation schemas and reports, but those reports may only carry build identity, counts, hashes, validation evidence, diagnostics, and other provenance. They are never the sole storage location for corpus semantics.

## Working graph hypothesis

Until issue #3 is complete:

- `word` is the candidate slot type, following ORAEC token granularity and the BHSA word-slot precedent;
- `sentence` and `text` are expected structural node types;
- explicit `line` nodes are allowed only if the source audit establishes a defensible line identity/order model from `lineCount`;
- lexical identity may warrant `lex` nodes, with word→lex relations, if corpus-wide lemma evidence supports stable identity;
- repeated date/place/object-type/hierarchy values may warrant shared entity or occurrence nodes rather than packed string features;
- external mappings must preserve multiplicity and provenance;
- source hierarchy must remain navigable/queryable if it is in release scope.

These are hypotheses, not implementation permission. No converter writer should freeze them before issue #3.

## Identity

Stable upstream IDs should be retained verbatim in dedicated features. Synthetic converter IDs, if required, must be deterministic and namespaced, and must never masquerade as ORAEC IDs.

Source order is semantically relevant unless the audit proves otherwise.

## Text and annotation

The model must retain, where present in ORAEC:

- exact `written_form`;
- hieroglyphic `hiero`;
- token ID;
- sentence translation;
- token/cotext translation;
- lemma form and lemma ID;
- part of speech;
- all attested grammatical feature families;
- line/address information;
- text title, bibliography, identifiers, location, date, original place, object type;
- credits, licence, author/responsibility, and source references;
- in-scope corpus hierarchy and mappings.

Missing source values remain missing. Empty and missing values are distinguished when the audit shows that the source distinguishes them semantically.

## BHSA reference rule

BHSA is the preferred design precedent when ORAEC evidence leaves multiple reasonable TF representations.

Reuse requires semantic equivalence. Examples:

- word slots are a plausible precedent because ORAEC annotation is token-centred;
- lexical nodes are a plausible precedent only if ORAEC lemma IDs behave as shared lexical identity;
- BHSA morphology names must not be copied onto ORAEC values merely to make APIs look familiar.

Every deliberate divergence from an applicable BHSA convention belongs in the frozen schema/ADR.

## Text-Fabric writer

After #3 freezes the ontology, #6 should implement an ORAEC-specific director over the typed IR using `tf.convert.walker.CV`.

The director must express the scholarly graph contract; it must not mechanically reproduce JSON nesting when that would flatten or misrepresent ORAEC semantics.

The emitted dataset must then be loaded through `Fabric` as an independent loadability gate before project-specific conservation checks.

## Text-Fabric app

A standard advanced app/browser is part of the deliverable. `app/config.yaml` is tracked from bootstrap, but display/section contracts are finalized only after the TF graph schema is frozen.

The app should expose useful transliteration and hieroglyphic formats, provenance, feature documentation, and stable ORAEC/source links where possible.

## Agora materializer

The public converter interface must be suitable for an Agora materializer:

```text
oraec-tf convert SOURCE_DIR --output OUTPUT_DIR --upstream-commit REVISION
```

The exact CLI is finalized with the converter. The materializer will:

1. acquire the pinned ORAEC repository;
2. pass the local source directory and resolved immutable revision to ORAEC-TF;
3. run conversion with network denied;
4. validate required TF output and provenance/build evidence;
5. publish/manage the artifact downstream.

Agora must not reimplement ORAEC parsing or repair TF semantics.

## Validation

Validation has two independent layers:

1. converter/unit/schema tests prove implementation contracts;
2. a separate source→graph audit rereads raw source independently and checks the generated TF graph.

Release validation must detect silent drops, duplicate identities, accidental normalization, flattening of one-to-many relations, and invented data.
