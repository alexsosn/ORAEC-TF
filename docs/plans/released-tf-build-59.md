# Plan: released wheel and offline resolver (#59)

1. Preserve RED tests for exact version dependency metadata, portable manifest,
   rejection of wrong published tf-build bytes, and a real dependency-resolving
   offline pip install that rejects a missing transitive wheel.
2. Replace the VCS requirement with `tf-build==0.1.0rc1`. Add an explicit online
   release-wheel requirement with its SHA-256 and freeze runtime versions/hashes.
   All existing online CI installations use the published wheel acquisition input.
3. Reuse the cross-platform wheelhouse verifier: check release wheel identity,
   emit version/hash requirements, retain pip's resolver with local find-links,
   no indexes/Git, then run installed CLI, native TF/CR, no-clobber and app checks.
4. Update the existing Linux/Windows job to acquire locked runtime wheels and
   build ORAEC only; record hashes without uploading corpus or wheel payloads.
5. Update installation documentation, run focused/full tests and exact-head
   Linux/Windows, pinned-source writer/audit/browser and Agora integration CI.
   Independently review the frozen final head before merge. Keep #12 open until
   its separate final software release acceptance is complete.

No parser, schema, corpus semantics, Karnak defaults or Agora registry changes.
