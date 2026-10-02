# Contributing

ORAEC-TF uses issue-driven, research-first development.

Before starting, read `AGENTS.md`, `research.md`, `design.md`, `plan.md`, and the active issue.

Every behavior change must pass:

1. research against real upstream evidence;
2. a written plan/design proportional to the semantic risk;
3. a RED test that demonstrates the missing behavior;
4. implementation;
5. exact-head local/CI verification;
6. logically independent adversarial review.

Corpus modelling changes must not be hidden inside refactors. If a PR changes what a source construct means in TF, document the evidence and update the schema/design reference.

Never commit upstream ORAEC data or generated TF artifacts. Synthetic fixtures are preferred for unit tests; full-corpus tests acquire the pinned source in CI or an explicit local workflow.

A PR is ready to merge only when its final head has been independently reviewed. Any behavior-changing commit after review requires re-review.
