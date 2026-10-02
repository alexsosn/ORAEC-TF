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

Two files present at the pinned revision, `mapping_oraec_karnak.tsv` and `mapping_oraec_lemmata_karnak.tsv`, are not listed in the current upstream README licence table. They must not be assigned an invented licence. Issue #2 is release-blocking until their provenance/licensing and intended inclusion are resolved.

Per-text `credits` metadata, named contributors, and source links must be preserved in the generated graph where the frozen schema requires them.

Generated build/provenance reports inherit whatever source material they reproduce. Keep such reports minimal and focused on identities, counts, hashes, and validation evidence.
