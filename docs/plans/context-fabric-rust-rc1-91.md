# Plan — ORAEC Rust Context-Fabric acceptance (#91)

1. Research exact 0.6.0rc1 PyPI wheel, cache and API differences (see research note); freeze ORAEC raw source and native Text-Fabric truth.
2. RED-first tests must detect single-value mutations, absent vs present, one-to-many valued edge corruption and changed .tf sources after compiling a cache. Tests precede helper implementation.
3. GREEN create an optional standalone typed node/edge digest comparator; compare complete values with deterministic ordering, bounded memory, and explicit mismatches.
4. Dedicated Python 3.13 workflow installs the exact Rust RC1 wheel, fetches pinned ORAEC, runs native converter/independent raw→TF and app, then compiles/reloads .cfr; verify 998,775 nodes, source .tf byte integrity and complete 62 feature values.
5. Run real cache-staleness mutation on a disposable fixture and a researcher TF query. Compare search result tuples as sets; record separate initial compilation vs repeated load metrics.
6. Keep software-only release and default/Agora using Text-Fabric. Review by a logically independent skeptical pass after exact-head CI; no merge if full corpus value conservation fails.
7. No corpus/cache upload. Update #88/#91 and the prior 0.5.7 baseline scope; preserve older benchmark as historical evidence.
