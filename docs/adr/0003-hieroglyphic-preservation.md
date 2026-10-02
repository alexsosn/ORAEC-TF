# ADR 0003 — Preserve ORAEC hieroglyphic strings exactly

Status: accepted for schema/app input  
Issue: #21  
Supported ORAEC source: `b83a0ee5fae27a40d4c0a2a9a8c9c2973d45e9cd`

## Decision

The authoritative Text-Fabric `hiero` feature preserves every ORAEC `hiero` value **code-point-for-code-point**.

The converter must not normalize, trim, repair, reconstruct, replace, or reinterpret the source string. In particular:

- exact `[⯑]` remains `[⯑]`;
- bare `⯑` remains distinct from `[⯑]`;
- U+FFFD `�` remains U+FFFD wherever ORAEC contains it;
- mixed strings such as `�𓇾` preserve both the replacement marker and recoverable Unicode signs;
- no guessed Gardiner/MdC sign may overwrite the authoritative value.

For the pinned corpus audit:

- `hiero` occurs on **267,042** tokens;
- there are **40,686** distinct exact values;
- **13,198** token values are exactly `[⯑]`;
- **6,545** token values contain U+FFFD.

These are conservation counts, not targets for automatic cleanup.

## Producer evidence

ORAEC publishes `oraec/formerly-mdc-now_unicode`; its README describes Egyptian texts encoded in MdC and **transformed into Unicode by ORAEC**.

Its `complete_mapping.csv` documents the transformation vocabulary directly. Uncertainty/control mappings include:

- `HASH,[⯑]`;
- `H_HASH,[⯑]`;
- `Q_HASH,[⯑]`;
- `V_HASH,[⯑]`;
- `hatching,[⯑]`;
- `/,[⯑]`;
- `//,[⯑]`.

The same table maps custom or otherwise unavailable sign identifiers to U+FFFD, for example:

- `US85Aa1002XT,�`;
- `US85Aa1001XT,�`;
- `O238,�`;
- `A366,�`;
- `Ff1,�`.

It also contains sign identifiers mapped to bare `⯑`. Therefore `[⯑]`, bare `⯑`, and U+FFFD are not interchangeable normalization variants.

## AED provenance checks

### U+FFFD example: `oraec489`

AED file `454USWR57RCEJALWEGQ7VWSHE4_hiero.xml` contains word-level notes stating that some MdC signs or sequences have no Unicode equivalent, including `T32B-N17` and `I119`.

ORAEC emits values such as `�𓇾` and `�`: mapped Unicode signs are retained while unavailable/custom positions are represented by U+FFFD.

U+FFFD is therefore already an intentional output of the upstream ORAEC Unicode transformation, not a UTF-8 decoding error introduced by ORAEC-TF.

### Placeholder example: `oraec8015`

AED file `MYNG746HDVDZBDRJTPPHQRRDJE_hiero.xml` contains real Unicode hieroglyphs inside `<unclear>…</unclear>` for several words, while the corresponding ORAEC values are `[⯑]`.

Thus `[⯑]` does not simply mean “there was no Unicode code point”. It can encode ORAEC's treatment of uncertain/lost graphemic rendering.

### Mixed uncertainty example: `oraec995`

AED file `A4C6JDTVC5DTVLASOA5FV7XKJM_hiero.xml` uses `<gap>`, `<unclear>`, and notes about unavailable Unicode. ORAEC's transformed representation uses `[⯑]` for many uncertain positions.

The authoritative ORAEC core preserves the result of that transformation rather than attempting to reverse it.

## Core feature contract

If a source token has a `hiero` key:

- the IR retains the exact Unicode string;
- the writer emits the same sequence of code points;
- the loaded TF feature compares equal to the source value;
- empty, missing, placeholder, and replacement-containing values are not conflated.

If a source token has no `hiero`, the converter must not invent one.

Any converter-derived quality classification must use a separate feature whose name/schema is decided by #3. Such predicates are diagnostics, not corrected readings.

## Advanced app/browser

The app renders the authoritative `hiero` value visibly as supplied by ORAEC.

It may style markers, add explanatory tooltips, expose filters, or show a separately sourced enrichment. It must not silently hide U+FFFD, strip brackets from exact `[⯑]`, or substitute reconstructed AED signs as though they were ORAEC values.

## Recovery/enrichment boundary

AED and `oraec/formerly-mdc-now_unicode` are useful provenance, but AED is **not a mandatory source** for the ORAEC-TF core materializer under ADR 0001.

Some original MdC/custom sign identities may be recoverable from AED notes, producer mappings, or future Unicode additions. That belongs in a separately justified **optional enrichment** or TF module.

An optional enrichment **must not overwrite** the authoritative `hiero` feature and must carry its own source/provenance/revision.

## Conservation and regression tests

#5/#6/#8 must eventually prove on the full pinned corpus:

- exact source→IR→TF equality for every present `hiero` string;
- 267,042 present values;
- 13,198 exact `[⯑]` values;
- 6,545 values containing U+FFFD;
- no normalization or replacement introduced by the converter.

#9 must smoke-test rendering of ordinary Unicode hieroglyphs, exact `[⯑]`, U+FFFD-only values, and mixed U+FFFD + hieroglyph strings.

#21 remains open until implementation-level round-trip and app tests exist.
