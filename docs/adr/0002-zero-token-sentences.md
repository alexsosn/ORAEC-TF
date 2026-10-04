# ADR 0002 — Preserve zero-token ORAEC sentences with technical anchor slots

Status: accepted for schema input  
Issue: #20  
Supported ORAEC source: `b83a0ee5fae27a40d4c0a2a9a8c9c2973d45e9cd`  
Text-Fabric evidence: `v13.1.0`, commit `dd227ce62b5536de53a0e20eac98c0459da8fd3d`

## Decision

Preserve every ORAEC sentence record as a first-class `sentence` node.

When, and only when, a source sentence has zero source tokens, allocate exactly one converter-derived **technical anchor slot** inside that sentence so the node can be represented by the Text-Fabric 13.1 warp.

For the supported snapshot this means:

- **815,026 source tokens**;
- **3 technical anchor slots**;
- **815,029 total slots**.

The slot-type name is deferred to #3. This ADR decides the zero-token invariant, not whether the final slot type is called `word`, `token`, `slot`, or another justified label.

Do not anchor to a neighbouring real source-token slot. That would give an empty source sentence a false textual extent and make Text-Fabric locality report containment that is not in ORAEC.

## Real source cases

### `oraec17:248`

ORAEC has an empty token list and empty translation.

AED provenance:
- `JIPPXMXOTNCQDIKJIQVYWMKOWU`;
- sentence `tlaIBUBdxY2gpt4BkLPqqWyiFqWQ4c`;
- content is only `<lb n="[236]"/>`;
- no `<w>` elements;
- stand-off sentence translation is empty.

### `oraec34:256`

ORAEC has an empty token list and empty translation.

AED provenance:
- `RP2F6BGNDBAARDBNDHGFSFPIEM`;
- sentence `tlaIBUBdWmUUCWH80FNmJaOcWwaxFw`;
- base sentence is an empty `<s></s>`;
- stand-off translation is empty.

### `oraec5614:3`

ORAEC has an empty token list and translation `{Chui-en-Chenemu}`.

AED provenance:
- `NS6BAIQRENELJM2A2LDNHIYK6E`;
- sentence `tlaIBUBd4R4jQOm80W1gMPGfy493eQ`;
- base sentence is an empty `<s></s>`;
- stand-off translation is exactly `{Chui-en-Chenemu}`.

The third case proves that a zero-token sentence can still carry source semantics that must remain independently queryable.

## Text-Fabric 13.1 constraint

Text-Fabric's data-model documentation says that some non-slot nodes may be linked to no slots. The shipped 13.1 serialization/conversion path does not support that case for a normal loadable warp.

Verified against tag `v13.1.0`:

1. `tf.convert.walker.CV._removeUnlinked()` removes every non-slot node with no `oslots` entry.
2. `Fabric.save()` checks that every non-slot node is mapped by `oslots`.
3. The TF edge reader rejects an empty target specification as `emptyNode2Spec`.
4. The `oslots` reader explicitly relies on the assumption that all non-slot nodes are linked.

An empty target set therefore cannot be round-tripped by the standard Text-Fabric 13.1 writer/reader path.

## Anchor semantics

A technical anchor:

- is converter-derived;
- has no ORAEC token ID;
- has no `written_form`;
- has no lemma ID/form;
- has no POS or morphology;
- has no cotext translation;
- has no hieroglyphic value;
- must be explicitly identifiable by a dedicated feature finalized by #3;
- renders as empty text;
- belongs to exactly one zero-token sentence;
- is ordered at the source sentence position.

For an empty sentence between non-empty sentences, its anchor is inserted between the preceding sentence's final real token slot and the following sentence's first real token slot.

For a trailing empty sentence, its anchor follows the preceding sentence's final real token slot.

No anchor is created for a sentence that contains at least one source token.

## Sentence identity and order

ORAEC sentence records do not carry a separate sentence ID field. Their identity is the pair:

`(oraecid, 1-based sentence index)`.

The final schema should preserve that index on sentence nodes.

An anchor is an implementation device for warp placement. It is not the sentence identity and must not receive a fabricated ORAEC token ID.

## Conservation invariants

For any supported source revision:

```text
real_slot_count       == source_token_count
anchor_slot_count     == zero_token_sentence_count
total_slot_count      == source_token_count + zero_token_sentence_count
sentence_node_count   == source_sentence_count
```

For the currently supported snapshot:

```text
real_slot_count       == 815026
anchor_slot_count     == 3
total_slot_count      == 815029
sentence_node_count   == 101796
```

Independent source→graph validation in #8 must additionally prove:

- every source token maps to exactly one non-anchor slot;
- every technical anchor maps to exactly one source sentence with `token: []`;
- every zero-token source sentence maps to exactly one sentence node and one anchor;
- no non-empty source sentence has an anchor;
- source sentence translations, including empty strings and `{Chui-en-Chenemu}`, are conserved;
- default token/word statistics exclude anchors;
- anchor slots have none of the source-token linguistic features listed above.

## Interaction with `tf.convert.walker.CV`

This decision preserves ADR 0001's direct-`CV` architecture.

The director can open the sentence node, emit one technical slot only for a zero-token source sentence, annotate that slot as technical, and terminate the sentence normally.

No post-hoc mutation of warp files, custom serializer, or semantic sidecar is required.

## Rejected alternatives

### Drop zero-token sentences

Rejected because all three are explicit ORAEC sentence records, and one carries a non-empty translation.

### Store them only in provenance/validation output

Rejected because provenance sidecars are not allowed to be the sole storage of corpus semantics.

### Attach the sentence node to an adjacent real token slot

Rejected because it fabricates textual extent, creates false sentence overlap/locality, and makes the neighbour appear to belong to two source sentences.

### Patch Text-Fabric files to encode an empty `oslots` set

Rejected for the current release because Text-Fabric 13.1's normal writer/reader/validation path does not round-trip that representation.

### Change the entire corpus to a more abstract slot type solely for these three cases

Not decided here. A neutral slot type could model anchors more literally, while a conventional word-like slot type may provide better TF ecosystem ergonomics. #3 must evaluate that trade-off across the whole corpus.

## Consequences for implementation

- #3 must define the slot type and final anchor feature names while preserving this invariant.
- #5 must preserve zero-token sentence records in the IR instead of filtering empty token arrays.
- #6 must emit the technical anchors and load the result with Text-Fabric.
- #8 must independently enforce the conservation equations and anchor exclusions.
- #9 must render anchors as empty and keep them out of researcher-facing token statistics by default.

#20 remains open until the generated-TF regression and independent conservation tests exist.
