# Plan — software-only Karnak release policy

Issue #12, #17, #85. Date: 2026-10-12.

1. Research real package contents, pinned-source mapping licences, native schema, parser/writer, independent raw-source graph audit, and downstream Agora host boundary (see `docs/research/software-only-karnak-release-boundary.md`).
2. **RED-first** policy tests: require an explicit software-only release licence boundary, #17 nonblocking status for software, current exclusion accurately stated, optional future local-support ticket #85, separate hosted-distribution licence gate, and no claim that Agora `network: deny` proves data privacy. Preserve existing frozen schema exclusion tests until #85 implements a new mode.
3. **GREEN** update `README.md`, `LICENSE_SCOPE.md`, `AGENTS.md`, `docs/agora.md`, and the accepted schema ADR to reflect the legal/software-vs-data boundary with explicit current converter limitations. Do not change semantics, `pyproject.toml` version, `schema/core.json`, or shipping contents.
4. Update issue requirements #12/#17 and file focused #85 implementation issue. Run exact-head test matrix and a logically independent skeptical review before merging the policy/documentation PR.
5. **Separate #85 TDD PR** for opt-in local mapping behavior (both tables, graph cardinality, independent raw-source audit, provenance). The existing default must remain unchanged until tests/changes are deliberately merged. Publishing generated datasets with Karnak mappings remains separately blocked by #17 absent an adequate rights review.

Safeguard: changing the statement of policy must never be reported as having enabled a currently excluded mapping in code.
