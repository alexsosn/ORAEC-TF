# Research: ORAEC source compatibility with tf-build

Issue: #52; parent infrastructure migration: alexsosn/tf-build#53.

## Concrete code comparison

`src/oraec_tf/source.py` has `validate_revision` (only 40 hex), `SourceSnapshot(path, revision)`, `verify_source` (clean checkout with directory equal to Git top-level) and `fetch_source` (origin remote + pinned fetch + detach + verify + `Path.replace`). Its pre-publication exists check is separated from `replace`, allowing overwrite in an intervening race. Its fetched repository retains `remote.origin.url` and `FETCH_HEAD` source metadata. Git subprocesses are unbounded.

`tf_build.source` at immutable SHA `2b2f0f8776b42423d4b450d4e2fe0040ab63a8e6` validates 40 **or** 64 hex, verifies a clean checkout even if called on a nested subdir, and returns `SourceSnapshot(path, repository_root, revision, object_format)`. Its pinned `fetch_git_source` stages acquisition, fetches without a persisted `origin`, unlinks transient `FETCH_HEAD`, rejects symlink/nonempty destinations, and atomically publishes with no-clobber semantics on supported operating systems. It times out each Git command and supports local relative source paths.

These broader tf-build rules require an ORAEC adapter: validate revision with ORAEC's 40-hex rule *first*; require `snapshot.path == snapshot.repository_root` after verification; project snapshot into ORAEC's existing two-field dataclass; map `GitSourceError` and filesystem publication errors into `SourceAcquisitionError`. Preserve `resolve_revision` as a legacy local helper for compatibility without using it for the new verified fetch path.

## Delivery and reproducibility

tf-build currently declares Python >=3.11, Text-Fabric >=13.1,<14, and version `0.1.0.dev0`. At this checkpoint no downloadable tagged wheel release is confirmed; don't use `tf-build>=...` from PyPI as though released.

For this pre-release consumer integration, the exact immutable PEP-508 git SHA is `tf-build @ git+https://github.com/alexsosn/tf-build.git@2b2f0f8776b42423d4b450d4e2fe0040ab63a8e6`. Git and repository network access are necessary **at package installation time**, not at `oraec-tf convert` runtime. This is an immutable dependency-source pin, not a wheel hash/published 0.1 release. It will require an explicit migration to a versioned hash-pinned wheel or package release before independent offline packaging, and must be documented accurately.

## Integration boundaries

`tests/test_source.py` currently asserts a fabricated `_run_git` call sequence with origin, so rewrite its acquisition-success contract against a **real local Git repository** rather than force the new implementation to mimic the old one. Existing source-info, verify-source CLI JSON, root-only checks and invalid/dangling symlink cases remain. Writer, frozen expected corpus counts, bibliography CR schema and live PR #51 are not part of this ticket.
