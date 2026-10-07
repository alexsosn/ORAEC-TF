# Design

Status: **native TF schema frozen by ADR 0005 and `schema/core.json`**.

Changes to node types, source-field coverage, identity rules, or serialization semantics now require an explicit schema/ADR revision rather than ad-hoc writer changes.

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

## Frozen core graph

The machine-readable authority is `schema/core.json`; ADR 0005 records the rationale.

Core node types:

- `word` slots, including exactly three explicitly marked technical anchors required by ADR 0002;
- `sentence`, `text`, `lex`, `cv`, `author`, `source_ref`, `idno`, `hierarchy`, and `external_ref` nodes.

Core edge features:

- metadata relations `date`, `origplace`, `objecttype`, `location`, and `material`;
- provenance/occurrence relations `author`, `source`, and `idno`;
- hierarchy relations `hierarchy` and `parent`;
- provenance-valued `external` mappings.

There is no core `line` node type. Lexical entities use shared `lex` nodes keyed by exact ORAEC lemma IDs. Multi-valued metadata is relational, never delimiter-packed. Known duplicate `idno` values are preserved as occurrence nodes.

Every non-slot entity has an explicit `oslots` strategy because Text-Fabric 13.1 cannot serialize unlinked semantic nodes.

## Identity

Stable upstream IDs should be retained verbatim in dedicated features. Synthetic converter IDs, if required, must be deterministic and namespaced, and must never masquerade as ORAEC IDs.

Source order is semantically relevant unless the audit proves otherwise.

## Text and annotation

The model must retain, where present in ORAEC:

- exact `written_form`;
- exact hieroglyphic `hiero`, preserved code-point-for-code-point under ADR 0003;
- token ID;
- sentence translation;
- token/cotext translation;
- lemma form and lemma ID;
- part of speech;
- all attested grammatical feature families;
- exact token-level `lineCount` when present; no core line nodes are inferred from it;
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

## Zero-token sentence preservation

The supported ORAEC snapshot contains three real sentence records with no source tokens. ADR 0002 requires one explicitly marked technical anchor slot for each so all 101,796 sentence records remain first-class TF sentence nodes without falsely linking an empty sentence to a neighbouring source token.

For the pinned snapshot the conservation contract is 815,026 source tokens plus 3 anchors = 815,029 total slots. Anchor slots carry no fabricated ORAEC token identity or linguistic annotation and render as empty text. The slot type is frozen as `word`; the anchor marker is `is_anchor=1`.

## lineCount boundary

ADR 0004 treats `lineCount` as exact source-token annotation, not a complete structural line model. Equal labels cross sentence boundaries, repeat across texts, and are interrupted by unlabeled gap tokens inside a real source line. The core graph therefore stores exact `lineCount` on real source-token slots and does not create `line` nodes from contiguous runs or normalized labels.

Any later reconstructed line/navigation layer is converter-derived, separately provenanced, and cannot replace the authoritative feature.

## Text-Fabric writer

#6 implements ADR 0005 and `schema/core.json` through an ORAEC-specific director over the typed IR using `tf.convert.walker.CV`.

The director must express the scholarly graph contract; it must not mechanically reproduce JSON nesting when that would flatten or misrepresent ORAEC semantics.

The emitted dataset must then be loaded through `Fabric` as an independent loadability gate before project-specific conservation checks.

## Text-Fabric app

A standard advanced app/browser is part of the deliverable. `app/config.yaml` is tracked from bootstrap, but display/section contracts are finalized only after the TF graph schema is frozen.

The app should expose useful transliteration and hieroglyphic formats, provenance, feature documentation, and stable ORAEC/source links where possible. Under ADR 0003 it must render exact ORAEC `hiero` values visibly, including `[⯑]` and U+FFFD, without silently reconstructing or replacing them.

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

Release validation must detect silent drops, duplicate identities, accidental normalization, flattening of one-to-many relations, and invented data. Exact Unicode equality is part of conservation for source `hiero` values under ADR 0003. Converter-derived technical anchors are allowed only under explicit schema rules such as ADR 0002 and must be independently countable and excluded from source-token conservation.
