# Plan

The 0.1.0 path is issue-driven. Dependencies are intentional: do not implement a semantic writer before the source contract and graph model are known.

## Bootstrap

- #1 Bootstrap autonomous development — repository rules, initial research/design/plan, package/CI scaffold, pinned manual acquisition helper.

## Research and schema

- #14 Decide authoritative source layer and Text-Fabric Factory boundary.
- #2 Complete ORAEC source/schema/licence audit.
- #3 Freeze the native TF ontology and serialization contract — ADR 0005 + `schema/core.json`.

ADR 0005 consumes #14/#2 plus ADRs 0002–0004. Downstream semantic implementation must conform to `schema/core.json`; the core schema has no inferred `line` nodes.

## Source pipeline

- #4 Pinned upstream acquisition and source-identity verification.
- #5 Canonical parser and typed IR.
- #6 Native TF writer and Text-Fabric load validation.
- #7 Native modelling of hierarchy, lexical entities, and external mappings.

Dependencies:
- #5 is unblocked by ADR 0005; it must parse the complete `schema/core.json` source contract and preserve exact/missing `lineCount` and `hiero` values.
- #6 requires #5 and implements ADR 0005 directly with `tf.convert.walker.CV`, including ADR 0002 anchors, ADR 0003 exact `hiero`, and ADR 0004 exact token-level `lineCount` without core line nodes.
- #7 requires the ADR 0005 entity/edge contract plus the relevant #5/#6 interfaces; Karnak remains gated by #17.

#4 may proceed in parallel because it concerns source identity rather than corpus semantics.

## Corpus-level correctness

- #8 Independent whole-corpus semantic conservation and reproducibility gates.

Dependency: #8 requires #5–#7 sufficiently complete to audit the frozen schema, including independent verification of ADR 0002's source-token/anchor conservation equations.

## Researcher interfaces

- #9 Standard Text-Fabric advanced app/browser, including exact placeholder/U+FFFD rendering required by ADR 0003.
- #10 Researcher-facing feature docs and reproducible query examples.

Dependencies:
- #9 requires a loadable graph from #6 and schema stability from #3.
- #10 requires #3 and representative generated output.

## Distribution

- #11 Agora-compatible materializer and downstream registration contract.

Dependency: direct conversion must already work. Agora integration must not become the place where parser/semantic bugs are repaired.

## Release

- #12 0.1.0 complete-corpus release gate.

The release requires all upstream dependencies above, full-corpus validation, standard TF app/browser loading, licensing/attribution correctness, Agora end-to-end materialization, green CI, and exact-head independent adversarial review.

## Autonomous continuation rule

If an issue is blocked, work on another unblocked dependency. If the explicit backlog is exhausted, continue with evidence-driven performance, stability, ergonomics, documentation, reproducibility, and edge-case work. New issues may be created by the research step when actual source/code evidence justifies them.
