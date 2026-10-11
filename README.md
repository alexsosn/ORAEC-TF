# ORAEC-TF

ORAEC-TF converts the [Open Richly Annotated Egyptian Corpus (ORAEC)](https://github.com/oraec/corpus_raw_data) into a native [Text-Fabric](https://annotation.github.io/text-fabric/) corpus.

## Status

**Pre-0.1 / research and converter bootstrap.** There is not yet a released TF corpus.

This repository contains only the software, tests, Text-Fabric app configuration, documentation, and source-acquisition helpers needed to build the corpus. It intentionally does **not** store either the ORAEC upstream files or generated Text-Fabric data.

The initial supported upstream snapshot is:

- repository: `oraec/corpus_raw_data`
- commit: `b83a0ee5fae27a40d4c0a2a9a8c9c2973d45e9cd`
- upstream commit date: 2024-06-03

The upstream repository contains 13,026 `oraec*.json` text records plus corpus-level hierarchy, mapping, collocation, and statistics files. The exact in-scope semantic contract is being audited in issue #2 before the TF ontology is frozen.

## Target architecture

The release target is a complete native TF modelling of the supported ORAEC source semantics:

- no raw JSON/XML blobs inside features;
- no delimiter-packed pseudo-lists standing in for structured source data;
- no semantic sidecars required to query the corpus;
- multi-valued metadata and relationships represented with proper TF nodes/features/edges;
- ORAEC token, sentence, text, lexical, hierarchy, metadata, translation, morphology, hieroglyphic-writing, identifier, and mapping semantics preserved where supported by the audited source;
- provenance and validation reports may exist outside TF, but they may not be the only place where research semantics survive.

When ORAEC semantics are ambiguous and an established Text-Fabric design pattern is relevant, ETCBC/BHSA is the primary design reference. Compatibility means equivalent semantics, not cosmetic copying of BHSA feature names.

The intended build flow is:

```text
pinned ORAEC source
        ↓
source audit / typed parser
        ↓
canonical IR
        ↓
native TF writer
        ↓
independent source→graph conservation
        ↓
Text-Fabric app/browser + Agora materializer
```

## Repository boundary

Local source and generated data are ignored by Git. A researcher or materializer acquires the upstream source separately and passes a local directory to ORAEC-TF.

For development:

```bash
python -m pip install -e '.[dev]'
oraec-tf source-info
oraec-tf fetch upstream/corpus_raw_data
oraec-tf verify-source upstream/corpus_raw_data
```

The fetch command acquires the exact supported immutable Git commit into a clean detached checkout. Alternate revisions must also be full 40-hex commit IDs; branches, tags, abbreviated SHAs, and dirty worktrees are rejected. `verify-source` applies the same identity contract to an existing local checkout, requiring the Git **worktree root**. Acquisition uses tf-build's pinned, bounded Git subprocesses and atomic no-clobber publication; the published checkout retains neither the origin remote URL nor transient `FETCH_HEAD` metadata. Conversion itself remains network-free; Agora owns acquisition and then invokes ORAEC-TF on the verified local source directory.

**Pre-release dependency:** the current development package pins `tf-build` to the exact Git commit
`2b2f0f8776b42423d4b450d4e2fe0040ab63a8e6`. Installing ORAEC-TF
therefore needs Git and access to that repository **during installation**. No
tf-build PyPI release or hash-pinned wheel is assumed. A versioned, verified
wheel/package artifact is required before ORAEC's independent offline release;
this Git-commit pin is a temporary, reproducible development source, not a
claim of offline wheel availability.

## Local Text-Fabric conversion (development builds)

After installing from this repository and fetching the verified pinned checkout, run:

```bash
oraec-tf convert upstream/corpus_raw_data \
  --output build/oraec-tf \
  --upstream-commit b83a0ee5fae27a40d4c0a2a9a8c9c2973d45e9cd
```

Conversion uses **only local files** and performs no source fetch or network calls.
The source must be a clean Git checkout at the exact supported immutable commit.
The output path must be absent or empty, outside the source checkout and not a
symbolic link. TF is first assembled in a private sibling directory through
tf-build's `BuildWorkspace`, validated from **raw .tf feature files** using
`validate_tf_artifact(level="all")` (never trusting a newer compiled .tfx
cache), then independently checked for ORAEC text/sentence/token/anchor
conservation before atomic no-clobber publication. Conversion never silently
replaces a destination created concurrently.

For compatibility, an existing **empty** destination is also accepted. It is
removed only after source validation, temporarily remains absent while the
private build runs, and is restored on a failed conversion **only if** no
other actor created a replacement. A concurrently created destination is
never overwritten, even when publication fails; existing nonempty paths and
symlinks remain forbidden. This is an ORAEC-specific output contract, not a
new tf-build replacement API.

The pinned source has 13,026 texts, 101,796 sentences and 815,026 real tokens,
plus three explicitly marked technical anchor slots for zero-token sentences.
**Native CR occurrence model (ADR 0007, schema v3):** Text-Fabric 13.1
cannot safely read literal carriage returns (U+000D) inside a regular .tf
feature row. The scalar feature contains a CR-free transport string. Every
original CR is a separate queryable `cr_occurrence` TF node with integer
`cr_offset` (original Unicode code-point position), `cr_feature` and
an explicit `cr_owner` edge to its exact source owner. No delimited offset
lists, copied JSON/XML or semantic sidecars are used. The exact source value
can be read with `NativeCRIndex(api).restore(text_node, "bibliography")`
from `oraec_tf.text_codec` after loading the standard Fabric API. It is
**not** correct to compare a CR-bearing source string to the transport-only
`F.bibliography.v(text_node)`. Full-source independent CI reconstructs and
verifies every source string, including standalone CR and CRLF.

The default generated corpus excludes Karnak crosswalks while their distribution
licence remains unresolved (#17). This is a development conversion path;
independent raw-source-to-TF validation (#8), the TF advanced app (#9),
researcher documentation (#10), and the upstream Agora materializer (#11)
are implemented and tested. Final 0.1.0 release verification and downstream
Agora registration remain separate gates (#12 and Agora #224).

## Text-Fabric app/browser

The repository includes the standard Text-Fabric advanced-app configuration under `app/`. Its display contract will be completed after the native TF schema is frozen in issue #3. A custom web application is not required to browse the generated corpus.

## Agora

ORAEC-TF owns source parsing, scholarly semantics, TF construction, validation, app configuration, and source-specific documentation.

Agora owns marketplace registration, source acquisition/execution integration, sandbox/trust UX, artifact publication/provenance, and consumer composition. The materializer contract is tracked in issue #11 and must run with network access denied during conversion.

## Development process

Every semantic or behavioral change follows:

**research → plan/design → RED-first TDD → implementation → exact-head tests → logically independent adversarial review**

See `AGENTS.md` and `docs/agentic-dev-loop.md`.

The 0.1.0 release gate is issue #12.

## Licensing

Repository-authored software is MIT licensed. ORAEC source texts and the generated TF adaptation retain upstream data terms; the main corpus is CC BY-SA 4.0. Some auxiliary upstream mappings are CC0, while the licensing of newer Karnak mapping files still requires explicit audit before release.

See `LICENSE_SCOPE.md`.
