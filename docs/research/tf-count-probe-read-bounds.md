# Mandatory source TF count-probe memory limits (issue #72)

Date: 2026-10-11. Authoritative code: `src/oraec_tf/tf_count_probe.py` after merged performance PR #68 (`612a708c`). Upstream file grammar checked against Text-Fabric v13.1.0 `tf/core/data.py`: `@node` header, metadata and blank separator, then node-range/value rows, with Windows-compatible CRLF.

## Defect and scope

The now-mandatory `_rows` implementation calls unrestricted text `readline()` for its type marker and iterates headers and body using `for line in handle`. Each iteration internally reads until a line break; on an adversarial multi-GiB unterminated line, a size/syntax check cannot prevent allocation. `_rows` only reads two node features (`otype.tf` and `token_id.tf`) and must not attempt to parse the whole TF corpus. It operates only after `tf-build.validate_tf_artifact(level="all")` completes exhaustive source-only TF validation in normal conversion. Current pinned genuine data passed #68 exact-head source/graph/Agora checks, so this is hardening for hostile or forged artifacts rather than correction of demonstrated source loss.

The fingerprint file reader in #70/#71 has a different binary hashing contract; reuse its 4 MiB header ceiling as an explicit conservative resource budget, not by importing the fingerprint function. In the count-probe body, `otype` values are known short ASCII node types while `token_id` values come from bounded source token identifiers; still use a generous 4 MiB *per-row* bound to avoid rejecting any legitimate writer text. Test against the complete pinned corpus before merge to falsify that assumption.

## Invariants

Every file line read in `_rows` must be bounded using `readline(size)`, including the initial marker, header metadata and all feature body lines. Total header line bytes/characters must not exceed 4 MiB; a single body row must not exceed 4 MiB. Reject overlong/unterminated lines with a specific `ProbeError` before parsing their text, and never accept truncation as a valid row. The text file is opened with `newline=""` to preserve LF/CRLF distinctions. Preserve count results and all malformed data rejections, no compiled-cache reads, no extra Fabric loads, no corpus payload in reports. Since text-mode `readline(size)` is in decoded characters, this guarantees a finite bound on Python characters; multi-byte allocation is bounded by the UTF-8 decoder but the 4 MiB numeric threshold is not a byte-exact wire-size guarantee.

The full independently validated pinned ORAEC graph, including 13,026 texts, 101,796 sentences, 815,026 real tokens, 3 anchors and 2,930 CR occurrences, remains the release-grade acceptance oracle.
