# Researcher cookbook: querying ORAEC-TF

These examples use the native **word-slot** Text-Fabric graph generated from the
immutable ORAEC source revision `b83a0ee5fae27a40d4c0a2a9a8c9c2973d45e9cd`.
They do not require XML/JSON/TSV semantic sidecars or inferred annotations.
Follow [the local rebuild and browser guide](app-browser.md) to obtain a
validated local TF folder. Every feature/edge name below is defined in the
[generated schema reference](feature-reference.md).

## Load a local corpus

```python
from tf.fabric import Fabric
from oraec_tf.research_queries import (
    find_text, words_with_pos, lemma_occurrences,
    texts_with_cv_label, ordered_idnos, hierarchy_path,
)

api = Fabric(locations="/absolute/path/to/generated/tf", silent="deep").loadAll(
    silent="deep"
)
assert api is not None
F, E, L, T, S = api.F, api.E, api.L, api.T, api.S
```

The API uses exact source identities. A native word is a source token iff
`F.token_id.v(word)` is not `None`; three technical slots from zero-token
sentences are marked by `is_anchor=1` and must not be counted as Egyptian
words.

## Navigate a text and sentence

```python
text = find_text(api, "oraec1")
assert text is not None
print(F.title.v(text), F.oraec_id.v(text))
sentences = L.d(text, otype="sentence")
first = sentences[0]
print(T.sectionFromNode(first))
print(T.text(first, fmt="text-translit"))
print(T.text(first, fmt="text-hiero"))
print(F.translation.v(first))
```

Sections use `oraec_id` and the one-based `sentence_index`, not TLA paths.
Hieroglyphic strings are source supplied: no glyph is invented when `hiero`
is missing. Missing or damaged signs and U+FFFD remain unchanged.

## Morphology, line annotations and Text-Fabric search

```python
# Match only the actual source POS label shown in your dataset.
words = words_with_pos(api, "substantive")
for word in words[:10]:
    print(
        F.token_id.v(word),
        F.written_form.v(word),
        F.pos.v(word),
        F.genus.v(word),
        F.voice.v(word),
        F.line_count.v(word),
    )

# Equivalent TF search-template idiom (also works in the standard browser):
matches = S.search("word pos=substantive", limit=10)
for (word,) in matches:
    print(F.written_form.v(word))
```

Use the values actually attested in `F.pos`, `F.voice`, `F.status`,
`F.pronoun_type` and other source features. Source `lineCount` is the
**string** `F.line_count`, not a reconstructed structural line node.

## Lexical entries and word occurrence slots

```python
# L1 is an illustrative identifier: substitute an attested F.lemma_id value.
lex = next(iter(F.otype.s("lex")))
lemma_id = F.lemma_id.v(lex)
occurrences = lemma_occurrences(api, lemma_id)
print(lemma_id, F.lemma_form.v(lex), len(occurrences))
for word in occurrences[:10]:
    print(F.token_id.v(word), F.written_form.v(word))
```

A shared `lex` node contains the exact set of word-occurrence slots for
its source lemma identity, not an invented token-level lemma edge.

## Periods, provenance and repeated identifiers

```python
# Find a period label from the corpus rather than guessing one.
text_with_date = next(
    (t for t in F.otype.s("text") if E.date.f(t)), None
)
if text_with_date is not None:
    date_node, ordinal = E.date.f(text_with_date)[0]
    label = F.cv_label.v(date_node)
    for text in texts_with_cv_label(api, "date", label)[:10]:
        print(F.oraec_id.v(text))

# Keep repeated IDs in the source order, not as a set:
if text_with_date is not None:
    print(ordered_idnos(api, text_with_date))

# Separate per-text author credits from README corpus contributors.
if text_with_date is not None:
    print([
        F.author_name.v(author)
        for author in E.author.f(text_with_date)
    ])
```

The edge value on `E.date`, `E.source`, etc. stores a one-based source
list ordinal. The `author.is_corpus_author` node feature identifies README
contributors; it must not be interpreted as per-text authorship.

## Exact hierarchy and licensed external IDs

```python
text = find_text(api, "oraec1")
if text is not None:
    for label, tla_url in hierarchy_path(api, text):
        print(label, tla_url)

    # External references use the edge's source mapping filename.
    for external, filename in E.external.f(text):
        print(F.external_system.v(external), F.external_value.v(external), filename)
```

Hierarchy links come from the exact source linked paths, with the original
labels (including possible empty strings) and `tla_url` retained. External
mapping families included by licence are Trismegistos, Wikidata, and VÉgA;
the Karnak mapping TSVs are excluded from distributed TF.

## Exact source Unicode including CRLF

Text-Fabric 13.1 cannot safely transport literal U+000D within a single
ordinary scalar. Schema v3 models each source CR as a native, queryable
`cr_occurrence` node with integer `cr_offset`, `cr_feature` and
an explicit `cr_owner` edge to the original source node (ADR 0007).
The scalar `F.bibliography.v(text)` remains a CR-free TF-safe transport value.
To reconstruct exact original Unicode, including CRLF:

```python
from oraec_tf.text_codec import NativeCRIndex

if text is not None:
    index = NativeCRIndex(api)  # Create once for the loaded corpus.
    source_bibliography = index.restore(text, "bibliography")
    print(source_bibliography)

    # Native per-character source offsets can also be queried directly.
    cr_nodes = (
        cr for cr in api.F.otype.s("cr_occurrence")
        if text in api.E.cr_owner.f(cr)
        and api.F.cr_feature.v(cr) == "bibliography"
    )
    print(sorted(api.F.cr_offset.v(cr) for cr in cr_nodes))
```

For the raw source, do not silently replace CRLF, normalize hieroglyphs or
HTML entities, remove repeated `idno` values, or collapse list ordinals.

## Validation and reproducibility

The schema is `schema/core.json`. The feature reference is generated
deterministically and can be checked offline:

```bash
python scripts/update_feature_reference.py --check
```

The conversion CI independently rereads all pinned raw source records and
compares them with the generated TF graph, including the exact source strings
reconstructed under schema v3. Produced reports record the source and converter
commits, TF version, schema version and per-file SHA-256; no semantic sidecars
are required to query research content.
