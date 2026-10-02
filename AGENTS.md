# ORAEC-TF agent instructions

ORAEC-TF is designed for autonomous, issue-driven development. Coding agents must treat this file as the mandatory entry point.

## Read first

Before changing code or corpus semantics, read in order:

1. `README.md`
2. `research.md`
3. `design.md`
4. `plan.md`
5. `LICENSE_SCOPE.md`
6. `docs/agentic-dev-loop.md`
7. the active GitHub issue and all linked PR/review discussion

When work depends on ORAEC, AED/AES/TLA, Text-Fabric, ETCBC/BHSA, or Agora behavior, verify the current upstream contract against actual data/code/documentation rather than relying on memory.

## Development gates

Every behavior or semantic change follows:

**research → plan/design → RED-first TDD → implementation → exact-head tests → logically independent adversarial review**

- Work from a GitHub issue with explicit acceptance criteria.
- Check for overlapping open issues and PRs before starting.
- Ground research in actual source records and current upstream code/docs.
- Preserve a deterministic failing test before implementing production behavior.
- Semantic mapping changes require written research/design evidence before code.
- Run the complete relevant test suite against the exact final head.
- A review is valid only for the exact final head. Production changes after review invalidate approval.
- Review fixes that change behavior repeat RED → fix → GREEN → re-review.
- Reviews must be skeptical and evidence-driven; inspect real source data and generated TF where applicable.
- Do not merge release-critical work with unexplained corpus failures, silent partial success, or unreviewed approximations.

Research may create focused issues when evidence reveals missing work. Do not manufacture speculative scope.

## Repository and data boundary

This repository stores software, tests, documentation, app configuration, and acquisition helpers only.

Do not commit an ORAEC source checkout, generated TF corpus files, copied upstream bulk JSON/TSV data, derived corpus caches, or release artifacts.

Small synthetic fixtures authored specifically for tests are allowed.

## Corpus semantics

The source of truth is the pinned ORAEC source snapshot.

Non-negotiable rules:

- Do not store source semantics as raw JSON/XML blobs merely to avoid modelling them.
- Do not serialize arrays/objects into delimiter-packed strings as a substitute for a graph model.
- Do not require semantic sidecars when information can be represented as TF nodes, edges, or features.
- Sidecars/reports are allowed only for provenance, validation evidence, build identity, hashes, and diagnostics.
- Preserve upstream wording, IDs, order, uncertainty, missingness, translations, morphology, credits, bibliography, and relations; do not silently normalize or improve them.
- Do not invent morphology, lemmas, translations, lines, hierarchy, equivalences, dates, or reconstructed text.
- Distinguish source-declared data from converter-derived structure with explicit provenance where relevant.
- Unknown or unsupported in-scope constructs must be measured and fail closed unless the frozen schema explicitly classifies them as ignorable.
- One-to-many source relations must remain one-to-many.

## Text-Fabric design

The initial working hypothesis is `word` slots because ORAEC's fundamental annotated unit is the token and BHSA provides a mature word-slot precedent. Issue #3 must confirm or reject that choice after issue #2 audits the whole source.

When uncertain:
1. inspect the ORAEC evidence;
2. inspect BHSA/ETCBC for a semantically equivalent pattern;
3. reuse the pattern only when the semantics match;
4. document deliberate differences.

Do not create BHSA-style features merely for familiarity when ORAEC does not supply the corresponding analysis.

Generated output must load with the supported Text-Fabric version and work through the standard advanced app/browser under `app/`.

## Acquisition and Agora boundary

Manual development acquisition may use ORAEC-TF helpers, but conversion receives a local source directory and must not access the network.

ORAEC-TF owns source parsing, normalization rules, canonical IR, scholarly semantics, TF graph construction, corpus validation, advanced-app configuration, and source-specific documentation.

Agora owns marketplace registration/discovery, acquisition/execution integration, sandbox/trust UX, artifact publication/provenance, and consumer-side composition.

If the same semantic bug occurs when ORAEC-TF runs directly, fix it here rather than in Agora.

Do not publish `agora.materializer.json` as a working contract until the direct converter CLI it invokes exists and passes its own end-to-end tests.

## Release mode

Issue #12 is the 0.1.0 release gate. A sample converter is not a release. The release must convert and independently validate the complete supported source snapshot, load through Text-Fabric, work through the advanced app/browser, and pass the Agora materializer path.
