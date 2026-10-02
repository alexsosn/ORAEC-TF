# Autonomous development loop

ORAEC-TF follows the strict loop used across the related Text-Fabric converter projects.

## 1. Select an issue

Choose an unblocked issue that advances #12. Read all linked discussion and check for overlapping work.

## 2. Research

Inspect the real upstream files, current code, Text-Fabric behavior, BHSA precedent, and Agora contract relevant to the issue.

Record material findings in `research.md` or a focused document under `docs/research/`.

Research may create new issues when evidence reveals a separate problem. Do not broaden scope speculatively.

## 3. Plan/design

Write the intended behavior, invariants, failure policy, affected interfaces, and test strategy before implementation.

For corpus-semantic changes, state:
- the exact source construct;
- how it appears in TF;
- how multiplicity/order/identity are preserved;
- how unsupported cases fail;
- the independent validation strategy.

## 4. RED-first test

Add a deterministic test that fails for the intended reason before production code is changed.

A test that merely exercises a mock or duplicates implementation logic is not sufficient evidence for a semantic claim.

## 5. Implement

Make the smallest coherent change that satisfies the researched contract. Do not hide unrelated behavior changes in cleanup.

## 6. Verify exact head

Run all relevant unit/integration/full-corpus gates. Record the exact commit under review.

For complete-corpus changes, validate against the pinned ORAEC snapshot and load the emitted graph with Text-Fabric.

## 7. Independent adversarial review

Review the exact final head from a logically independent perspective.

The reviewer should try to falsify the PR's claims using:
- real source examples;
- corpus-wide measurements where relevant;
- generated TF data;
- public API behavior;
- current documentation and licence evidence.

Review questions include:
- Did anything get silently dropped?
- Was a list flattened?
- Was missingness normalized away?
- Was source uncertainty converted into certainty?
- Is an ID actually unique?
- Does validation independently test the writer?
- Would the bug exist outside Agora?
- Are tests proving production behavior rather than the test double?

## 8. Iterate or merge

Behavior-changing review fixes require a new RED/GREEN cycle and re-review of the new head.

Only merge when the exact head is green and reviewed.
