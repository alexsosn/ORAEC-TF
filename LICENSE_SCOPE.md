# Licence scope

## ORAEC-TF software

Converter code, tests, CI/configuration, acquisition helpers, app configuration, and software documentation authored for this repository are licensed under the MIT License in `LICENSE`.

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

Taken together, the prospective CC0 policy, the ORAEC-authored file history, and the project's explicit description of creating/finding these correspondences are sufficient project-side evidence to classify the **ORAEC crosswalk data as published** under CC0.

### VÉgA counterexample

A CC0 footer on an ORAEC blog post is **not** by itself sufficient evidence for the licence of a linked dataset.

The 2023 VÉgA post also has a CC0 page footer, but explicitly says the mapping was scraped from TLA and **adapted from TLA** to ORAEC. The canonical source README accordingly classifies `mapping_oraec_lemmata_vega.tsv` as CC BY-SA 4.0.

The Karnak classification therefore does not use the blog footer as a blanket licence inference. It rests on the different provenance: ORAEC says it created/found the Karnak correspondences after adopting its prospective CC0 policy.

### External-resource boundary

The CC0 classification here covers the ORAEC-authored mapping/crosswalk data as distributed in these two TSV files: ORAEC identifiers paired with SITH Karnak identifiers/URLs.

It does **not** relicense **the content behind SITH URLs**. ORAEC-TF must not treat this classification as permission to redistribute SITH inscriptions, lexicon entries, images, transliterations, translations, metadata, or other target-resource content.

ORAEC-TF may therefore include these crosswalk relations in a generated corpus under the ORAEC-side CC0 classification, while retaining provenance and one-to-many relation semantics.

## Generated reports

Generated build/provenance reports inherit whatever source material they reproduce. Keep such reports minimal and focused on identities, counts, hashes, validation evidence, and other provenance rather than duplicating corpus content.
