"""Deterministic ambiguity framework with one illustrative English fixture.

The fixture exercises the explainability contract; it is not a Telugu lexicon
or a validated Telugu-English code-mixed-language rule.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.schemas.analysis import AmbiguityCandidate, AmbiguityRecord, AnalyzedToken, TransliterationResult


@dataclass(frozen=True)
class _Candidate:
    candidate_id: str
    description: str


@dataclass(frozen=True)
class _Rule:
    rule_id: str
    surface: str
    required_label: str
    candidates: tuple[_Candidate, ...]
    anchors: tuple[tuple[str, str], ...]
    source: str


_BANK_RULE = _Rule(
    rule_id="fixture.english_bank_immediate_context.v1",
    surface="bank",
    required_label="ENGLISH",
    candidates=(
        _Candidate("financial_institution", "financial institution (illustrative English sense)"),
        _Candidate("river_edge", "land beside a river (illustrative English sense)"),
    ),
    anchors=(
        ("account", "financial_institution"),
        ("loan", "financial_institution"),
        ("river", "river_edge"),
        ("shore", "river_edge"),
    ),
    source="illustrative_project_fixture:english_bank_polysemy",
)
_RULES = (_BANK_RULE,)


def resolve_ambiguities(
    *,
    normalized_text: str,
    tokens: list[AnalyzedToken],
    transliterations: list[TransliterationResult],
) -> list[AmbiguityRecord]:
    """Apply exact candidate rules using the target label and immediate context.

    Failed/unavailable transliteration records never serve as evidence. The
    current English fixture does not depend on transliteration.
    """
    by_index = {result.token_index: result for result in transliterations}
    rules = {(rule.surface, rule.required_label): rule for rule in _RULES}
    records: list[AmbiguityRecord] = []

    for position, token in enumerate(tokens):
        if normalized_text[token.start:token.end] != token.text:
            raise ValueError("Token surface and offsets do not match normalized text.")
        rule = rules.get((token.text.casefold(), token.language.label))
        if rule is None:
            continue

        anchor_map = dict(rule.anchors)
        observations: list[tuple[str, str, str]] = []
        neighbors = (
            tokens[position - 1] if position > 0 else None,
            tokens[position + 1] if position + 1 < len(tokens) else None,
        )
        for neighbor in neighbors:
            if neighbor is None:
                continue
            result = by_index.get(neighbor.index)
            if result is not None and result.status != "skipped":
                continue
            candidate_id = anchor_map.get(neighbor.text.casefold())
            if candidate_id is not None:
                side = "left" if neighbor.index < token.index else "right"
                observations.append((side, neighbor.text, candidate_id))

        supported = {candidate_id for _, _, candidate_id in observations}
        if len(supported) == 1:
            selected = next(iter(supported))
            details = ", ".join(
                f"{side} neighbor {surface!r} supports {candidate_id}"
                for side, surface, candidate_id in observations
            )
            status = "resolved"
            evidence = f"Configured immediate-context rule matched {details}."
        else:
            selected = None
            status = "abstained"
            if len(supported) > 1:
                details = ", ".join(
                    f"{side} neighbor {surface!r} supports {candidate_id}"
                    for side, surface, candidate_id in observations
                )
                evidence = f"Conflicting configured immediate-context anchors ({details}); no candidate selected."
            else:
                evidence = "No configured immediate English context anchor matched; evidence is insufficient."

        records.append(AmbiguityRecord(
            token_index=token.index,
            surface=token.text,
            start=token.start,
            end=token.end,
            status=status,
            candidates=[
                AmbiguityCandidate(
                    candidate_id=candidate.candidate_id,
                    description=candidate.description,
                    source=rule.source,
                )
                for candidate in rule.candidates
            ],
            selected_candidate=selected,
            rule_id=rule.rule_id,
            evidence=evidence,
        ))
    return records
