# Research — ORAEC-TF software release versus Karnak-derived data distribution

Date: 2026-10-12. Issues: #12, #17, #85. Source revision: `b83a0ee5fae27a40d4c0a2a9a8c9c2973d45e9cd`.

## Verified source and code boundaries

- `MANIFEST.in` includes only `schema/core.json`; ORAEC-TF README, `AGENTS.md` and CI say upstream `oraec*.json` and generated `.tf` corpus data are not shipped. MIT covers project-authored **software**, not upstream data or independent user-generated corpus exports.
- The pinned ORAEC root README's file-level licence table omits `mapping_oraec_karnak.tsv` and `mapping_oraec_lemmata_karnak.tsv`. The 2022 policy and June 2024 Karnak article support intended CC0 authorship but are not incontrovertible file-level redistribution grants. See #17 and `LICENSE_SCOPE.md` for contrary VÉgA provenance.
- Actual current converter **does not include Karnak mappings**: `src/oraec_tf/parser.py::MAPPING_SPECS` marks both `release_included=False`; `parser_validation.py` skips release-excluded tables, `writer.py` skips them, and `audit_graph.py` explicitly rejects `external_system=karnak`. `schema/core.json` freezes them as excluded and tests currently require that behavior.
- `agora.materializer.json` declares an upstream conversion adapter, but a marketplace host may transmit/cache/publish generated data; `network: deny` does not prove a private end-to-end user-controlled distribution boundary (Agora #224).

## Legal/operational distinction

Publishing a software package with source-acquisition functionality is not itself a publication of the acquired upstream TSVs or a derived TF corpus. Local conversion of lawfully obtained files and onward redistribution of the resulting mapping data present distinct rights/questions; neither the MIT licence nor a blog footer grants automatic republication rights. Do not describe conversion as categorically legal in every jurisdiction or under every access contract.

Therefore #17 is **not** a blocker for the standalone **software-only** v0.1.0 release; it remains open for project-/host-published Karnak-bearing corpus artifacts. #85 separately designs/tests user-selected local Karnak materialization including both mapping tables, one-to-many semantics, source-specific provenance, and independent adversarial conservation. Do not flip the schema's current excluded/default flags in a documentation-only PR or claim #85 has shipped.

## Release consequences

Keep source→native TF corpus integration and independent full-data CI on the **already supported** mapped families. Require no upstream or generated corpus data in package/release/CI artifacts. Release packaging and exact-head checks remain mandatory (#12/#59). Actual downstream Agora registration/host sandbox is a separate milestone (#224); any sharing of generated Karnak-bearing datasets still requires the rights review in #17.
