# ORAEC-TF as an Agora materializer

The repository root contains [`agora.materializer.json`](../agora.materializer.json),
a schema-v1 materializer manifest compatible with the current Agora
acquisition/execution/output contract. This is an **upstream contract**; registering
it in [Agora](https://github.com/alexsosn/Agora) is a separate downstream action.

## Trust and ownership

Agora is responsible for installation trust, selecting and downloading the
upstream source, creating a local output destination, and enforcing the
materializer's `execution.network: deny` sandbox. The source is acquired
as an exact Git checkout of `oraec/corpus_raw_data` at
`b83a0ee5fae27a40d4c0a2a9a8c9c2973d45e9cd`. A local source selection is
also permitted **only** when it is a clean Git worktree root at that same
immutable commit. Branches, dirty trees, mismatched revisions, source symlinks
at the manifest boundary, and unsupported corpus revisions are not accepted.

ORAEC-TF owns ORAEC parsing, the Text-Fabric semantic model, preservation of
source Unicode and feature missingness, licensing exclusions, writing native
warp/features, source validation, and its documented TF advanced app. It does
not attempt to acquire source files from inside the Agora execution sandbox.
Conversion calls the **existing public** `oraec_tf.cli.main(["convert", ...])`
path, not a second converter.

## Direct end-to-end invocation

After acquiring the pinned source using the repository's acquisition command:

```bash
oraec-tf fetch upstream/corpus_raw_data
oraec-tf verify-source upstream/corpus_raw_data

# No network is needed or requested during this execution.
python -m oraec_tf.agora upstream/corpus_raw_data build/agora-oraec \
  --source-revision b83a0ee5fae27a40d4c0a2a9a8c9c2973d45e9cd
```

`build/agora-oraec` must be nonexistent or empty, not a symlink and not inside
the source checkout. The adapter builds in a sibling private directory,
rechecks the public CLI output and minimum TF warp files, and publishes the
complete artifact only after success. On failure no partial dataset is published.

Output layout:

```text
build/agora-oraec/
  tf/
    otype.tf
    oslots.tf
    otext.tf
    ... all generated native feature and edge .tf files ...
  conversion-summary.json
```

The JSON summary contains **provenance only**: pinned source repository and
revision, converter package name/version, exact source/slot counts, a description
of the CLI preflight checks, and SHA-256 of generated `.tf` files. It contains
no source JSON, hieroglyphic/transliteration text dumps, separate lexeme graph,
or other semantic sidecar. Git/source artifacts are not copied into the output.

The materializer requires ordinary native Text-Fabric files, which can be
loaded with:

```python
from tf.fabric import Fabric

api = Fabric(locations="build/agora-oraec/tf", silent="deep").loadAll(
    silent="deep"
)
assert len(api.F.otype.s("text")) == 13026
assert len(api.F.otype.s("word")) == 815029  # 815026 tokens + 3 anchors
```

## Validation and distribution boundary

The dedicated GitHub Actions workflow
[`agora-materializer.yml`](../.github/workflows/agora-materializer.yml)
acquires the pinned source, executes this exact module, checks the full corpus
totals and warp files, then **independently compares the entire raw source
against the generated TF graph**, including source string fidelity. The
workflow uploads only count/hash/provenance JSON reports, never upstream source
or generated research corpus. The standard CI matrix tests the adapter's
immutable-pinning, public-CLI delegation and transactional failure behavior
using a small isolated fixture.

**Important:** The network-denial policy is declared for Agora's actual
executor. The GitHub Actions job fetches source *before* calling the
materializer and is not itself a proof of kernel-level network isolation.
Downstream Agora registration must verify the executor actually enforces
`network: deny` and delivers the exact source revision binding.

Generated corpus content adapts CC BY-SA 4.0 input. See
[`LICENSE_SCOPE.md`](../LICENSE_SCOPE.md) for attribution and the exclusion of
Karnak mappings pending explicit file-level licence evidence.

The standard local TF advanced app and complete schema reference remain in
`app/` and `docs/`. The CR offset transport limitation, still natively
round-trippable but not the final queryable ontology, is tracked in issue #42.
