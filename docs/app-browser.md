# ORAEC-TF standard Text-Fabric browser

ORAEC-TF uses the normal Text-Fabric advanced app and browser, not a custom
web service. The `app/config.yaml` file is maintained in this software
repository, while the raw upstream JSON/TSV and generated TF features stay
**local** (ignored by Git) or in separately published licensed corpus artifacts.

## Rebuild and browse locally

For Text-Fabric's normal `clone` lookup, place this repository under the
usual clone location:

```bash
mkdir -p ~/github/alexsosn
git clone https://github.com/alexsosn/ORAEC-TF.git \
  ~/github/alexsosn/ORAEC-TF
cd ~/github/alexsosn/ORAEC-TF
python -m pip install -e '.[dev]'

# Source acquisition is explicit and pins the immutable upstream commit.
oraec-tf fetch upstream/corpus_raw_data
oraec-tf verify-source upstream/corpus_raw_data

# Conversion itself is offline and publishes only validated native TF features.
oraec-tf convert upstream/corpus_raw_data \
  --output tf \
  --upstream-commit b83a0ee5fae27a40d4c0a2a9a8c9c2973d45e9cd

# Standard Text-Fabric browser with the app and data from the local clone.
tf alexsosn/ORAEC-TF:clone checkout=clone
```

The `tf/` folder is Git-ignored. The command above never implies that TF data
are present in the remote GitHub software repository. After corpus publication,
a public archive/installation workflow will be documented separately.

For a generated TF folder in another location, inspect it directly with the
normal API:

```python
from tf.fabric import Fabric

api = Fabric(locations="/absolute/path/to/generated/tf", silent="deep").loadAll(
    silent="deep"
)
text = api.F.otype.s("text")[0]
sentence = api.L.d(text, otype="sentence")[0]
print(api.T.sectionFromNode(sentence))
print(api.T.text(sentence, fmt="text-translit"))
print(api.T.text(sentence, fmt="text-hiero"))
```

A complete researcher-facing reference is available in
[the frozen feature catalogue](feature-reference.md) and
[the executable query cookbook](query-recipes.md). The catalogue is generated
from `schema/core.json` and CI verifies that it has not drifted.

The advanced-app smoke runner also supports arbitrary ephemeral outputs without
moving files or contacting a server:

```bash
python scripts/validate_advanced_app.py /absolute/path/to/generated/tf
```

## Display and navigation

| Format | TF origin | Use |
|---|---|---|
| `text-orig-full` | `written_form` + `trailer` | Existing original transliteration |
| `text-translit` | `written_form` + `trailer` | Default app view |
| `text-hiero` | `hiero` + `trailer` | Supplied Unicode Egyptian hieroglyphs |

The app navigates `text` by the exact `oraec_id`, then `sentence` by its
source array index. A technical word slot tagged `is_anchor=1` is hidden from
the visual word display but remains in the source-faithful TF graph. Neither
the app nor the converter guesses missing hieroglyphic text. Uncertain signs
(`[⯑]`) and U+FFFD are displayed exactly when present.

Metadata features and relations remain available through the usual `F`, `E`,
`L`, `T`, and TF search interfaces. Stable individual ORAEC online text URLs
have **not** been verified, so the app does not invent a `webBase` link
template. Read real TLA target URLs from `F.tla_url` on hierarchy nodes.

### Literal source values and carriage returns

Text-Fabric 13.1 cannot directly serialize U+000D carriage returns in TF
feature values. Schema v2 stores an exact reversible offset map on each node
as `<node_type>_cr_offsets`. Standard display formats show CR-free transport
text; for exact raw-source comparisons, reconstruct using *both* native fields:

```python
from oraec_tf.text_codec import restore_source_string

exact_bibliography = restore_source_string(
    api.F.bibliography.v(text),
    api.F.text_cr_offsets.v(text),
    "bibliography",
)
```

This representation preserves CRLF vs. LF and original positions without
semantic JSON/XML sidecars (see ADR 0006).

## Validation and current limits

The pinned-source CI builds the complete TF corpus, reruns an independent
raw-JSON/TSV-to-graph audit, and smoke-tests the app against that *same*
ephemeral generated TF directory. A passing YAML parse alone is not
sufficient to certify browser behavior.

Text-Fabric does not currently support an Egyptian-specific `writing: egy`
setting; the app leaves `writing` unset and uses normal Unicode-capable
font fallback. This project does not distribute fonts. Researcher-facing
feature-by-feature documentation is tracked separately under issue #10.
