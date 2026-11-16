# Research: reproducible ORAEC prerelease operator procedure (#109)

Date: 2026-11-15. Parent release gate #12, post-publication consumer check #106.

Checked live repository:
- `main` at `7feb7c0f89700ebc16fb5d9ed0be143e754fca54` (PR #107 added CITATION.cff); `ci.yml` push and `context-fabric-acceptance.yml` push at that SHA both succeeded. Earlier PR-head successes do **not** satisfy the release workflow's final SHA dispatch predicate.
- GitHub Releases API returned `[]`. `git/ref/tags/v0.1.0rc1` and `releases/tags/v0.1.0rc1` returned 404. Therefore the README correctly describes an unpublished `0.1.0rc1` software candidate.
- `software-release.yml` has a read-only staging job and a `publish` job restricted to `workflow_dispatch`, main, an **existing** `v0.1.0rc1` tag matching the checked-out commit and current main head, and a `release` environment. It refuses to overwrite existing releases. Assets: only wheel, source tarball and `release-manifest.json`. It requires successful exact-SHA `ci.yml` **push**, and manual dispatch events for `writer-validation.yml`, `release-rehearsal.yml`, `agora-materializer.yml`.
- The three full corpus workflows all support `workflow_dispatch` at `main`. Native writer and Agora do pinned source acquisition + graph audit, and installed release rehearsal also installs actual wheel with released tf-build and exercises Flask browser handlers. Generated data stays in runner temp.
- `scripts/verify_release_assets.py` checks software-only archive members, wheel built-from-sdist equivalence, actual SHA256 and exact three published files. `requirements/tf-build.txt` hash-pins external prerelease dependency.
- `docs/installed-distribution.md` documents a fresh offline wheelhouse with hash-locked normal resolver and source-free synthetic native TF smoke. No dedicated operator runbook currently explains the tag+dispatch order or how to halt if main changes.

Constraints: no third-party deployment tooling; production repository/tag mutation requires authorized human operation. The existing GitHub connector provides read, issues, PR/branch edits but **not** tag creation or Actions workflow dispatch. This ticket adds docs only; it does not simulate a published release.

Decision: use a concise operator runbook with explicit source SHA check, three manual full-source dispatches, verification of their exact SHA, immutable annotated tag, dispatch of `software-release.yml` with the tag input, assets inspection, and separate published-byte smoke tracked by #106. Make it explicit that a new commit after check starts invalidates release-head evidence; defer / do not move an existing release tag.
