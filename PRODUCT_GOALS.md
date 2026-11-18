# Product goals — ORAEC-TF

## Users and purpose

Egyptologists and computational philologists should be able to locally convert the audited Open Richly Annotated Egyptian Corpus to native Text-Fabric and query its source-attested texts, tokens, morphology, hieroglyphic writing, metadata and relationships without requiring JSON sidecars.

## Representative research journeys

1. Acquire the exact supported ORAEC source revision, locally convert it, and load the generated TF corpus.
2. Locate an Egyptian text and inspect its sentence/token hierarchy, transliteration and hieroglyphic features as actually supplied.
3. Search lexical, morphological or writing annotations and navigate each result to attested source context.
4. Query native hierarchy, metadata and mapping relationships without converting uncertain/missing values to asserted facts.
5. Open representative passages and search via the standard Text-Fabric browser or direct public API.

## Minimum usable release

Publish the **software-only** 0.1.0 converter release with verified dependency installation, complete pinned-source conservation, native TF reload and a genuine researcher CLI/browser smoke. The software release does not bundle upstream ORAEC or pre-generated TF data; downstream Agora registry publication is a separate step. A release-candidate wheel or CI artifact does not count as a public release.

## Boundaries and priority

Respect per-source redistribution conditions. The optional local Karnak crosswalk does not create permission to redistribute source-derived data; absence of that permission must not hold an otherwise valid software-only release hostage. Keep Egyptian source semantics in native TF and repair only demonstrated install/reader defects. Complete issue #12 and real-browser smoke (#119) rather than inventing certification or a parallel viewer.

## Autonomous-development decision rules

- Select work by the researcher journeys above, not issue count or the ease of adding tests. Prefer finishing active PRs and releases over opening new tickets.
- Before introducing a new adapter, workflow, registry, protocol, or validation layer, demonstrate that an existing mechanism cannot meet a concrete acceptance need.
- Preserve source fidelity, access controls, security, and applicable upstream rights. Do not invent inferred text or silently weaken correctness gates.
- Batch repetitive data changes and reuse parameterized tests. Keep independent adversarial review proportional to risk, and validate the actual researcher path.
- If two successive cycles do not advance a journey or remove an observed blocker, reconsider the approach. Stop when the scoped deliverable works instead of generating optional infrastructure work.
