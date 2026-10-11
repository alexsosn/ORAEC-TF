# Research: the Agora outer artifact has an independent publication race

Issue #57; follow-up to ORAEC-TF #54 / tf-build #53.

`src/oraec_tf/agora.py::materialize` calls the public `cli.main("convert", ..., stage/"tf", ...)`, verifies the returned counts, removes derived TF runtime caches, fingerprints the actual shipped feature files and creates an operational `conversion-summary.json`. The **outer** `stage` then replaces `target` with `stage.replace(target)`. The inner CLI's `BuildWorkspace.publish()` does not protect this outer rename.

The adapter permits an *absent or existing empty* target; Agora may already own an empty output root. POSIX `rename`/Python `Path.replace` can replace an existing **empty directory** after a separate preflight. I reproduced this in a real POSIX temporary directory: `stage.replace(newly_created_empty_target)` succeeded and the target inode changed. Replacing an existing **nonempty** sentinel directory normally fails `ENOTEMPTY`; tests limited to that case would miss the bug.

At the tf-build version pinned in ORAEC-TF (immutable SHA `2b2f0f8776b42423d4b450d4e2fe0040ab63a8e6`), `tf_build._atomic.publish_path_no_clobber` already implements atomic no-replace publication using Linux renameat2, macOS renamex_np, or Windows rename. `BuildWorkspace` is the public create-only wrapper but would require removing Agora's host-owned empty destination at the *start* of materialization, unlike current behavior which keeps it in place until all validation has passed.

## Decision

For this narrow outer-boundary fix, reuse the pinned internal `tf_build._atomic.publish_path_no_clobber(stage,target)` at the same final-promotion point, after the optional existing-empty `target.rmdir()`. This preserves the original time at which an Agora-owned empty root is removed, and fails closed if a new owner creates a destination after preflight or after that removal. The existing catch path removes unpublished stage and restores a formerly empty target only when absent.

Tradeoff: `_atomic` is an internal pre-release API. The immutable package dependency pins its contract for this migration; a future audited *public* atomic publication surface may be justified by the now-proven second consumer. Do not duplicate ctypes rename code inside ORAEC or change the broader tf-build workspace contract opportunistically.

## Independent evidence

Use real POSIX directory inodes rather than a fabricated Git/TF loader or mocking the publish function. For the outer filesystem boundary, the adapter's established `cli.main` stub is sufficient to emit three minimal TF feature filenames, capture actual JSON, compute actual SHA-256 hashes and execute real final publication. The full pinned-source Agora CI on ready-state PR must still exercise the entire ORAEC corpus and independent source–TF conservation; this test alone makes no scholarly semantics claim.
