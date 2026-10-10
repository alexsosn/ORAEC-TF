# Plan: atomic no-clobber Agora outer promotion

Issue #57.

1. RED-first `tests/test_agora_materializer.py`: run the real `agora.materialize` function, inject a fake CLI which creates the full minimal adapter-expected TF output and also creates an **empty competing destination** *after* preflight, capture its inode, and demand `FileExistsError`, identical inode, empty destination, no leaked `.agora-*` temporary directory. On the old POSIX `stage.replace`, the test must fail because the competitor is silently replaced.
2. Preserve and extend existing normal success/invalid revision/partial CLI output tests, including formerly empty target success and its restoration on failed conversion. Keep source/network boundaries identical.
3. Replace only outer `stage.replace(target)` with `tf_build._atomic.publish_path_no_clobber(stage,target)`. Treat it as an immutable-commit-pinned private primitive until a separate public helper is designed; no duplication of Linux/macOS/Windows rename syscalls.
4. Explain the outer vs inner publication boundaries in README/Agora docs; generated semantic TF data and native CR schema are untouched.
5. Run fast Ruff/strict mypy/pytest on exact Python 3.11–3.13 head; ready-state *both* full pinned-source writer and Agora output/conservation runs, with exact published corpus metadata verification. Independent adversarial review must check the actual raced-empty-directory inode contract and cleanup, not just import of a helper.
6. Synchronize with merged ORAEC-TF #56 before final review, keeping its source-backed CLI validation intact.
