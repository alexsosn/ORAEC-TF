# ADR 0004 — Preserve lineCount exactly; do not infer core line nodes

Status: accepted for schema input  
Issue: #19  
Supported ORAEC source: `b83a0ee5fae27a40d4c0a2a9a8c9c2973d45e9cd`

## Decision

ORAEC-TF has **no core `line` node type** derived from `lineCount` in the initial native corpus.

The authoritative source value is an exact `lineCount` feature on the source-token occurrence where ORAEC supplies it. Exact `lineCount` values are preserved code-point-for-code-point, including leading/trailing whitespace and whitespace-only values. The authoritative feature **must not be stripped**, normalized, parsed into a number, or replaced by a derived label.

Any future line navigation, normalized labels, or reconstructed line spans are converter-derived analysis. They must be separate features/nodes/modules with explicit provenance and must never replace the exact source feature.

## Corpus-wide evidence

The reproducible #19 analysis of the complete supported snapshot measured:

- 815,026 source tokens;
- 789,633 tokens with `lineCount`;
- 28,672 distinct exact labels;
- 25,678 distinct labels after trimming;
- 2,994 trim-normalization collisions;
- 96,721 exact contiguous runs;
- 30,467 exact runs crossing ORAEC sentence boundaries;
- 2,143 texts with non-contiguous reuse of an exact label;
- 6,798 non-contiguous exact-label instances;
- 30,991 sentences containing more than one exact run;
- 7,119 exact labels shared by more than one text;
- maximum exact-label scope: 5,565 texts.

These measurements establish two different facts at once: `lineCount` often carries genuine edition/line-address information, but its token-level serialization is not a complete line-boundary structure.

## Real counterexample: `oraec1:83`

In ORAEC sentence 83:

- token 1 has `lineCount = "[Vs 22]"`;
- token 2 is the lost-text token `[...]` and has no `lineCount`;
- token 3 and following tokens return to `lineCount = "[Vs 22]"`.

The aligned AED base sentence has a word, then `<gap reason="lost"/>`, then the following words, with **no intervening `<lb>`**.

Therefore the missing `lineCount` on the gap token does not represent a physical/source line break. **contiguous-run reconstruction** would incorrectly split one source line into multiple line nodes.

The same pattern occurs around labels such as `[liS 35]`–`[liS 50]`: AED `<lb n="..."/>` marks real changes, while ORAEC lost-text/gap tokens may lack `lineCount` inside the same line.

## Why exact-label equality is not line identity

An equal `lineCount` label cannot be treated as a globally shared line entity:

- 7,119 exact labels occur in multiple texts;
- one exact label occurs in 5,565 different texts;
- many labels are conventional local addresses such as `[1]`, not globally unique identifiers.

Within one text, equal exact labels may also recur non-contiguously. Some of that reuse is caused by unlabeled gap tokens, and other cases may reflect edition conventions. The source does not provide a stable line entity ID that resolves these cases.

## Whitespace and normalization

Whitespace is part of the authoritative source serialization. The full audit found extensive leading whitespace and a small number of trailing/blank values. The dedicated analysis found 2,994 cases where different exact spellings collapse to the same trim-normalized value.

Consequently:

- the source feature is stored exactly;
- `strip()` is not applied before storage;
- a normalized display/search value, if later useful, must be a distinct converter-derived feature;
- normalization must not be used to create authoritative identity.

## Interaction with sentence structure

`lineCount` and ORAEC sentence boundaries are independent dimensions:

- 30,467 exact lineCount runs cross sentence boundaries;
- 30,991 sentences contain multiple exact runs.

A `sentence` node therefore cannot stand in for a physical line, and lineCount changes cannot define sentence boundaries.

## Core TF contract

For every real source-token slot:

- if ORAEC has a string `lineCount`, TF stores exactly that string;
- if ORAEC omits `lineCount`, TF omits the feature value;
- technical anchor slots from ADR 0002 have no fabricated `lineCount`.

The core graph does not synthesize `line` nodes from lineCount runs, equal-label groups, or trimmed labels.

## Optional derived line layer

A future derived line layer is allowed only if a separate research issue establishes a defensible reconstruction algorithm. Such an algorithm may use richer provenance such as AED `<lb>` information, but AED remains optional enrichment under ADR 0001 and cannot become an undeclared mandatory source for the core ORAEC materializer.

A derived layer must:

- carry explicit converter/source provenance;
- preserve exact source `lineCount` independently;
- distinguish reconstructed spans from ORAEC-declared data;
- publish regression/conservation evidence for gap handling, repeated labels, and sentence crossings.

## Consequences

- #3 should omit `line` from the initial core node-type set and define exact `lineCount` as a source-token feature.
- #5 must preserve missing-vs-present and exact Unicode/whitespace for `lineCount` in the IR.
- #6 must emit the exact feature without normalization and must not synthesize core line nodes.
- #8 must compare every present/missing `lineCount` value source→TF exactly.
- #9 may display `lineCount` verbatim; any prettier/normalized display is explicitly derived.

#19 can close when this research decision and its corpus-wide analyzer are merged. Generated-TF equality belongs to #6/#8.