# Native Text-Fabric raw and semantic fingerprints

ORAEC-TF emits **two separate SHA-256 inventories** for generated, validated
native `.tf` feature files. Neither changes the original generated files or
replaces the independent raw-ORAEC → TF conservation audit.

| Audit report key | Agora provenance key | Meaning |
| --- | --- | --- |
| `output_sha256` | `tf_sha256` | Exact physical file bytes, including the wall-clock `@dateWritten` line |
| `output_semantic_sha256` | `tf_semantic_sha256` | Exact file bytes **excluding only** the single valid header `@dateWritten` line |

## Why these are different

Text-Fabric 13.1 emits `@dateWritten=<UTC clock>` into the metadata header of
every feature every time it writes one. Two builds from the identical pinned
source may have completely different raw byte hashes due only to timestamps.
The semantic digest is calculated by a strict streaming reader that validates
the standard `@node`, `@edge`, or `@config` format, finds the header/body
separator, requires exactly one canonical UTC clock, hashes every other header
and body byte unchanged, and **does not rewrite** any generated output.

Both Text-Fabric writer formats `YYYY-MM-DDTHH:MM:SSZ` and
`YYYY-MM-DDTHH:MM:SS+00:00Z` are accepted, but malformed or non-UTC timestamps,
duplicate/missing clocks, symlinks, and incomplete headers are rejected.
A string in the data section resembling `@dateWritten` is **not** removed.
Other metadata changes, source tokens, feature assignments, node/edge identity,
Unicode glyphs and whitespace all change the semantic hash.

## Limits

"Semantic SHA-256" means *timestamp-neutral serialized feature fingerprint*,
**not** a mathematical proof that all alternative .tf representations encode
equivalent graphs. Changes in serialization order, spacing or any other
metadata still change this digest. A matching digest for all features, together
with the complete source revision/schema/package identity and independent
conservation report, is useful reproducibility evidence. A matching raw digest
is exact build-artifact integrity evidence. Neither hash alone proves the
upstream ORAEC source was faithfully converted.

The full corpus consists of 13,026 texts, 101,796 source sentences,
815,026 tokens, 3 derived anchor slots and 2,930 native `cr_occurrence`
nodes. No bulk corpus or hash-derived semantic sidecars are checked into
this repository; hashes appear only in conversion audit/provenance JSON.

## Researcher usage

For an installed ORAEC-TF environment with a locally generated native
`otype.tf`:

```python
from oraec_tf.tf_fingerprints import hash_tf_feature
raw_sha, semantic_sha = hash_tf_feature("path/to/generated/otype.tf")
print(raw_sha, semantic_sha)
```

For a complete corpus, compare **every** filename and semantic fingerprint
in `output_semantic_sha256` or `tf_semantic_sha256`, not a subset of files.
Do not use a timestamp-neutral digest for security-sensitive verification of
a published exact-byte artifact; use the raw SHA-256 and locked source/build
identity for that purpose.
