"""Typed intermediate representation for the pinned ORAEC source contract."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ControlledValueIR:
    kind: str
    cv_id: str
    label: str


@dataclass(frozen=True, slots=True)
class CreditsIR:
    license: str
    author: str
    sources: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TokenIR:
    token_id: str
    written_form: str
    cotext_translation: str | None = None
    lemma_id: str | None = None
    lemma_form: str | None = None
    line_count: str | None = None
    hiero: str | None = None
    pos: str | None = None
    name_type: str | None = None
    number_type: str | None = None
    voice: str | None = None
    genus: str | None = None
    pronoun_type: str | None = None
    numerus: str | None = None
    epitheton: str | None = None
    morphology: str | None = None
    inflection: str | None = None
    adjective_type: str | None = None
    particle_type: str | None = None
    adverb_type: str | None = None
    verbal_class: str | None = None
    status: str | None = None


@dataclass(frozen=True, slots=True)
class SentenceIR:
    index: int
    translation: str
    tokens: tuple[TokenIR, ...]


@dataclass(frozen=True, slots=True)
class TextIR:
    oraec_id: str
    title: str
    sentences: tuple[SentenceIR, ...]
    credits: CreditsIR
    bibliography: str | None = None
    condition: str | None = None
    dates: tuple[ControlledValueIR, ...] = ()
    original_places: tuple[ControlledValueIR, ...] = ()
    object_types: tuple[ControlledValueIR, ...] = ()
    locations: tuple[ControlledValueIR, ...] = ()
    materials: tuple[ControlledValueIR, ...] = ()
    idnos: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CorpusMetadataIR:
    corpus_authors: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class HierarchyComponentIR:
    label: str
    tla_url: str
    tla_kind: str
    tla_id: str


@dataclass(frozen=True, slots=True)
class HierarchyRowIR:
    oraec_id: str
    components: tuple[HierarchyComponentIR, ...]


@dataclass(frozen=True, slots=True)
class MappingRowIR:
    source: str
    target: str


@dataclass(frozen=True, slots=True)
class MappingTableIR:
    filename: str
    source_domain: str
    target_system: str
    release_included: bool
    rows: tuple[MappingRowIR, ...]
