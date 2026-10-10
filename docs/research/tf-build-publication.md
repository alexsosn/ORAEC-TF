# Research: adopt tf-build publication and raw TF verification

Issue: ORAEC-TF #54; parent tf-build #53.

## Current real consumer paths

`src/oraec_tf/cli.py::_convert` currently verifies the frozen source revision, runs `validate_corpus_source`, serializes through the ORAEC-specific `write_tf` into a sibling `tempfile.mkdtemp`, loads only three selected TF features with `Fabric.load("oraec_id sentence_index token_id")`, compares text/sentence/token/technical-anchor counts against the parsed source, then calls `stage.replace(target)`. This final rename is not a no-clobber operation: a different owner can create `target` after the earlier empty/absent test, and can be overwritten. Text-Fabric's ordinary loading can prefer a newer compiled `.tf/*.tfx` body even when shipped raw feature bodies are corrupted.

ORAEC deliberately accepts a nonexistent or **preexisting empty** output directory, rejects nonempty or symlink targets, and refuses output inside the source checkout. The public CLI JSON includes output path, revision and text/sentence/real-token/anchor/slot counts. These are consumer contracts, not shared tf-build semantics.

`tf_build.workspace.BuildWorkspace` at exact pinned SHA `2b2f0f8776b42423d4b450d4e2fe0040ab63a8e6` stages privately beside an **absent** destination and uses platform-supported atomic no-clobber publication. `tf_build.validate.validate_tf_artifact(level="all")` creates a private source-only view and forces a real `.tf` body reload, rather than trusting a newer preexisting binary cache. It checks TF structural metadata but does **not** know ORAEC word/text/sentence conservation; keep our independent comparison.

## Compatibility decision

Keep the currently pinned pre-release tf-build source dependency (exact full Git commit; network at install, not conversion), with no moving branch or claimed PyPI wheel. Preserve existing empty-directory acceptance **locally** by removing an already-empty target only after full parsed-source validation and immediately before constructing `BuildWorkspace`. On build/validation/publish failure, restore that empty directory only if the destination remains absent. A concurrently created destination (directory, file, or symlink) must never be overwritten; the shared atomic publish enforces no clobber after the compatibility removal. This contract does not guarantee the existing empty directory remains continuously visible during a long build. The release path must document that limitation.

Use `BuildWorkspace` staging, `validate_tf_artifact(level="all", require_otext=True)` on the generated TF *before* the existing ORAEC-specific independent count check, then `workspace.publish()`. Preserve parsing/writer schema version 3, native CR nodes, Text-Fabric `Fabric.load` for the count-specific check and existing CLI JSON.

## Evidence and independent gates

Real synthetic `TextIR` fixtures exercise the CLI end-to-end without downloading upstream data. RED tests must create an intervening destination exactly before publication and prove sentinel preservation, check cleanup after partial writer failures, preserve caller-owned empty-directory success/error behavior, and corrupt a real saved integer feature after forcing an actual `.tfx` cache newer than the raw `.tf`; exhaustive source-backed validation must reject this despite the cache.

Full ready-state ORAEC writer/source and Agora materializer CI runs on the actual frozen `b83a0ee5fae27a40d4c0a2a9a8c9c2973d45e9cd` source remain the release-relevant gates: 13,026 texts, 101,796 sentences, 815,026 real tokens, 3 technical anchors and native CR occurrences checked independently. Keep distribution/licence and release gate #12 separate; neither source data nor generated TF files belong in this repo.
