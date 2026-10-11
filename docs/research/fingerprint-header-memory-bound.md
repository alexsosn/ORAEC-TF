# Fingerprint header memory bound (issue #70)

Date: 2026-10-11. Scope: `src/oraec_tf/tf_fingerprints.py` only; no graph/schema or source-data change.

## Verified implementation evidence

* The merged PR #69 `hash_tf_feature` scans the first `@node` / `@edge` / `@config` marker with an unbounded binary `readline()` and likewise scans metadata records with `readline()`. The `HEADER_LIMIT = 4 * 1024 * 1024` check follows allocation of the entire returned line. An attacker-supplied feature with a single enormous unterminated metadata line can force unbounded allocation before rejection.
* Text-Fabric 13.1.0 `tf/core/data.py` at `annotation/text-fabric` tag `v13.1.0`, lines 240–269, parses first-line type, metadata lines starting `@`, and a blank line terminating metadata. Writer lines 516–531 emit exactly this header and `@dateWritten`, with a blank line before the data. Windows text-mode writing may use CRLF.
* Existing tests in `tests/test_tf_semantic_fingerprints.py` cover authentic writer-generated TF, timestamp neutrality, CRLF, and invalid metadata. The existing oversized-header test only checks final rejection and does not detect over-allocation.
* The body already uses bounded `read(1024 * 1024)`; no change is needed there. The semantic digest intentionally removes precisely one validated UTC timestamp metadata record.

## Required invariant

Every header `readline` must have an explicit positive maximum based on the remaining `HEADER_LIMIT` budget, including the initial type marker. No oversized row is hashed before the size rejection; incomplete metadata rows fail closed without yielding either digest. Ordinary LF/CRLF feature hashes, clock neutrality, and failures for invalid metadata must remain identical. Hashes are not a substitute for independent source-to-graph conservation.

This is a header-parsing resource-exhaustion fix, not a change to published TF bytes or corpus semantics.
