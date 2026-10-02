# Plan

The 0.1.0 path is issue-driven. Dependencies are intentional: do not implement a semantic writer before the source contract and graph model are known.

## Bootstrap

- #1 Bootstrap autonomous development — repository rules, initial research/design/plan, package/CI scaffold, pinned manual acquisition helper.

## Research and schema

- #14 Decide authoritative source layer and Text-Fabric Factory boundary.
- #2 Complete ORAEC source/schema/licence audit.
- #3 Freeze the native TF ontology and serialization contract.

Dependency: #3 requires #14 and #2, and must consume the focused structural research from #19 and #20.

## Source pipeline

- #4 Pinned upstream acquisition and source-identity verification.
- #5 Canonical parser and typed IR.
- #6 Native TF writer and Text-Fabric load validation.
- #7 Native modelling of hierarchy, lexical entities, and external mappings.

Dependencies:
- #5 requires #14, #2, and #3.
- #6 requires #3 and #5; its default implementation path is direct `tf.convert.walker.CV`, not Text-Fabric Factory. It must implement ADR 0002's zero-token sentence anchors.
- #7 requires #2, #3, and the relevant parser/writer interfaces.

#4 may proceed in parallel because it concerns source identity rather than corpus semantics.

## Corpus-level correctness

- #8 Independent whole-corpus semantic conservation and reproducibility gates.

Dependency: #8 requires #5–#7 sufficiently complete to audit the frozen schema, including independent verification of ADR 0002's source-token/anchor conservation equations.

## Researcher interfaces

- #9 Standard Text-Fabric advanced app/browser.
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
