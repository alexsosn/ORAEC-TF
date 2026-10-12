# Licence scope

## ORAEC-TF software

Converter code, tests, CI/configuration, acquisition helpers, app configuration, and software documentation authored for this repository are licensed under the MIT License in `LICENSE`. The 0.1.0 deliverable is a **software-only release**: wheels/sdist, project source, app configuration and documentation, not upstream ORAEC JSON/TSV files or any generated TF corpus. The Karnak redistribution licence question in #17 **does not block the software-only v0.1.0 release**; licensing concerns for data become relevant when those datasets or their derived content are actually shared.

## ORAEC source and generated corpus

The root MIT licence does **not** relicense ORAEC source data or Text-Fabric data generated from it.

At the currently pinned upstream revision `b83a0ee5fae27a40d4c0a2a9a8c9c2973d45e9cd`, the upstream `oraec/corpus_raw_data` README states:

- `oraec1.json .. oraec13026.json`: CC BY-SA 4.0;
- `oraec_hierarchical_path.tsv`: CC BY-SA 4.0;
- `mapping_oraec_lemmata_vega.tsv`: CC BY-SA 4.0;
- `mapping_oraec_trismegistos.csv`: CC0;
- `mapping_oraec_wikidata.tsv`: CC0;
- files under `collocation/`: CC0;
- files under `statistics/`: CC0.

A generated ORAEC-TF corpus that adapts the CC BY-SA source must therefore retain the applicable CC BY-SA 4.0 terms and attribution. CC0 auxiliary data does not remove the ShareAlike obligations arising from the main corpus.

Per-text `credits` metadata, named contributors, and source links must be preserved in the generated graph where the frozen schema requires them.

## Karnak crosswalks

The pinned source also contains:

- `mapping_oraec_karnak.tsv`;
- `mapping_oraec_lemmata_karnak.tsv`.

The root upstream README licence table does not list these two later-added files. That **README omission** is retained here as a provenance fact; the classification below is based on independent project-authored licensing evidence rather than pretending the table contains entries that it does not.

### ORAEC's prospective CC0 policy

ORAEC's 2022-11-30 licensing post explains the attribution problem caused by combining additional third-party source material with the CC BY-SA corpus and then states that the project will put **“our own things we create in the future”** under CC0 so newly created ORAEC data can be reused without adding attribution obligations.

This prospective policy predates both Karnak crosswalks.

### File provenance

The mapping files were published directly by the ORAEC project account:

- `mapping_oraec_lemmata_karnak.tsv` was added at commit `edd5e4dc1e567274819ed05c644b6f83cc243579` on 2024-05-31;
- `mapping_oraec_karnak.tsv` was added at commit `b83a0ee5fae27a40d4c0a2a9a8c9c2973d45e9cd` on 2024-06-03.

ORAEC's 2024-06-05 “SITH Karnak” post describes the project as having found the 31 text correspondences itself and says **“we have created a table”** with nearly 2,000 ORAEC-lemma ↔ Karnak equivalences. It links directly to `mapping_oraec_lemmata_karnak.tsv`.

Taken together, the prospective CC0 policy, the ORAEC-authored file history, and the project's explicit description of creating/finding these correspondences are **strong evidence of intended CC0** treatment.

They are nevertheless **insufficient for release-grade file-level licensing** because the canonical distribution's licence table does not name either file, and no explicit licence declaration tied to these exact two TSV files has yet been located. ORAEC-TF therefore does not promote the intent evidence into a settled redistribution licence.

### VÉgA counterexample

A CC0 footer on an ORAEC blog post is **not** by itself sufficient evidence for the licence of a linked dataset.

The 2023 VÉgA post also has a CC0 page footer, but explicitly says the mapping was scraped from TLA and **adapted from TLA** to ORAEC. The canonical source README accordingly classifies `mapping_oraec_lemmata_vega.tsv` as CC BY-SA 4.0.

The Karnak classification therefore does not use the blog footer as a blanket licence inference. It rests on the different provenance: ORAEC says it created/found the Karnak correspondences after adopting its prospective CC0 policy.

### External-resource boundary

The evidence discussed here concerns only the ORAEC-authored mapping/crosswalk pairs: ORAEC identifiers paired with SITH Karnak identifiers/URLs. It does **not** relicense the external target resource and specifically is **not the content behind SITH URLs**.

**Current implementation:** the shipped default converter intentionally omits both Karnak crosswalks: its typed parser sets `release_included=False`, its TF writer skips these mappings, and the independent graph auditor rejects generated Karnak edges. Opt-in local processing of both mappings is **not yet implemented**. Issue #85 tracks the separate research/TDD change to support user-selected local conversion with exact native one-to-many edges and independent raw-source conservation. Do not present the software policy change as functionality already shipped.

**Local processing vs distribution:** a user who lawfully obtains the source may process it locally under applicable source terms. Such local use does not itself distribute the upstream tables or generated TF data; it is not a blanket legal determination for every jurisdiction or access contract. For a future #85 local artifact, document provenance and state exactly **Karnak mapping redistribution terms: unresolved**. Do not label either TSV definitively CC0 on the present evidence. This warning must not be placed solely in a separate semantic sidecar instead of in the product's usage/provenance documentation.

**Project/host publication:** until an **explicit upstream clarification** or a recorded independent rights determination justifies release of these exact TSV-derived correspondences, project release artifacts and hosts must **exclude the Karnak mappings from distributable generated corpora**. This includes hosted downloads, published GitHub Release assets, public Context-Fabric resources and Agora-hosted artifacts that are shared or cached for distribution. A remote execution service can access the result even if a manifest declares `network: deny`; review the actual service boundary before calling it private use.

If upstream later clarifies the two files explicitly, update this section and #17 with the exact rights evidence before publishing any Karnak-bearing dataset; this does not retroactively limit the MIT converter software release.

## Generated reports

Generated build/provenance reports inherit whatever source material they reproduce. Keep such reports minimal and focused on identities, counts, hashes, validation evidence, and other provenance rather than duplicating corpus content.
