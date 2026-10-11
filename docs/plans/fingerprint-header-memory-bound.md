# Bound TF fingerprint header reads (issue #70)

1. RED: add a stream guard at the actual `Path.open("rb")` boundary for a valid LF/CRLF feature. Fail any header `readline()` without a positive size or exceeding `HEADER_LIMIT+1`. Check that the real function still hashes a well-formed feature and reads the body in bounded blocks. Add an adversarial `HEADER_LIMIT+1` unterminated metadata row and boundary cases for exactly within / one byte beyond the cap.
2. GREEN: bound the first marker `readline(HEADER_LIMIT + 1)`; bound each following line with `readline(HEADER_LIMIT - header_size + 1)`, rejecting header-size overflow **before** digest updates. Preserve the existing marker, newline, UTC timestamp, UTF-8, separator, and body rules. No whole-file buffering, silent truncation, or normalization.
3. Verify: run strict Ruff, mypy and pytest on 3.11–3.13, the existing genuine Text-Fabric writer fingerprint regression, and the pinned full-source conservation/Agora gate on the final PR head. The PR remains open if any required gate is unavailable.
4. Perform a separate skeptical review of the exact diff and execution evidence, especially off-by-one boundaries, CRLF, truly bounded allocations, symlinks, and whether raw/semantic hashes remain identical for valid input. Review fixes repeat RED/GREEN.

Out of scope: changing timestamp semantics, identifying graph-isomorphic hashes across newline variants, and replacing the exhaustive Text-Fabric validator.
