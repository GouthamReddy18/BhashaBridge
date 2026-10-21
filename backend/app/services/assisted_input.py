"""Conservative, traceable assisted-input construction."""
from app.schemas.experiment import (
    AssistedInputResult,
    SkippedTransformation,
    TransformationRecord,
    TransformationRule,
)
from app.services.preprocessing import normalize_whitespace


def build_assisted_input(
    *,
    original_input: str,
    normalized_input: str,
    tokens,
    transliterations,
    ambiguities,
    rules=None,
    allow_synthetic_test_fixtures: bool = False,
) -> AssistedInputResult:
    """Apply explicit synthetic test rules; production substitutions are disabled."""
    skipped: list[SkippedTransformation] = []
    try:
        if normalize_whitespace(original_input) != normalized_input:
            raise ValueError("normalization mismatch")

        previous_end = 0
        for index, token in enumerate(tokens):
            if token.index != index:
                raise ValueError("nonsequential token indices")
            if (
                token.start < previous_end or token.start < 0
                or token.end < token.start or token.end > len(normalized_input)
            ):
                raise ValueError("overlapping or invalid token spans")
            if normalized_input[token.start:token.end] != token.text:
                raise ValueError("token surface/span mismatch")
            previous_end = token.end

        for record in transliterations:
            if record.token_index < 0 or record.token_index >= len(tokens):
                raise ValueError("invalid transliteration token reference")
            token = tokens[record.token_index]
            if (record.start, record.end, record.original_surface) != (
                token.start, token.end, token.text
            ):
                raise ValueError("transliteration trace mismatch")

        for record in ambiguities:
            if record.token_index < 0 or record.token_index >= len(tokens):
                raise ValueError("invalid ambiguity token reference")
            token = tokens[record.token_index]
            if (record.start, record.end, record.surface) != (
                token.start, token.end, token.text
            ):
                raise ValueError("ambiguity trace mismatch")

        parsed = [
            rule if isinstance(rule, TransformationRule)
            else TransformationRule.model_validate(rule)
            for rule in (rules or [])
        ]
        if len({rule.rule_id for rule in parsed}) != len(parsed):
            raise ValueError("duplicate transformation rule IDs")

        eligible_rules: list[TransformationRule] = []
        for rule in parsed:
            if rule.token_index < 0 or rule.token_index >= len(tokens):
                raise ValueError("invalid transformation token index")
            token = tokens[rule.token_index]
            if token.text != rule.expected_surface or token.language.label != rule.expected_language:
                raise ValueError("transformation source surface or language mismatch")
            if token.language.label not in {"TELUGU_ROMANIZED", "ENGLISH"}:
                raise ValueError("protected token cannot be transformed")

            # Metadata strings and entity assertions are caller claims, not authorization.
            if rule.evidence_status == "verified":
                skipped.append(SkippedTransformation(
                    token_index=rule.token_index,
                    operation="rule",
                    reason="production_transformations_disabled_no_trusted_registry",
                    rule_id=rule.rule_id,
                ))
                continue
            if not allow_synthetic_test_fixtures:
                skipped.append(SkippedTransformation(
                    token_index=rule.token_index,
                    operation="rule",
                    reason="synthetic_fixture_test_opt_in_required",
                    rule_id=rule.rule_id,
                ))
                continue
            eligible_rules.append(rule)

        spans = sorted(
            (tokens[rule.token_index].start, tokens[rule.token_index].end)
            for rule in eligible_rules
        )
        if any(current[0] < previous[1] for previous, current in zip(spans, spans[1:])):
            raise ValueError("transformation spans overlap")

        edits: list[tuple[int, int, str]] = []
        applied: list[TransformationRecord] = []
        for rule in eligible_rules:
            token = tokens[rule.token_index]
            if rule.replacement == token.text:
                raise ValueError("transformation replacement is identical to source")
            applied.append(TransformationRecord(
                rule_id=rule.rule_id,
                version=rule.version,
                token_index=token.index,
                start=token.start,
                end=token.end,
                before=token.text,
                after=rule.replacement,
                provenance=rule.provenance,
                evidence=rule.evidence,
                evidence_status="synthetic_fixture",
            ))
            edits.append((token.start, token.end, rule.replacement))

        assisted = normalized_input
        for start, end, replacement in sorted(edits, reverse=True):
            assisted = assisted[:start] + replacement + assisted[end:]

        for record in transliterations:
            skipped.append(SkippedTransformation(
                token_index=record.token_index,
                operation="transliteration",
                reason=f"transliteration_{record.status}_not_an_authorized_replacement",
            ))
        for record in ambiguities:
            skipped.append(SkippedTransformation(
                token_index=record.token_index,
                operation="ambiguity",
                reason=(
                    "abstained_no_candidate_selected"
                    if record.status == "abstained"
                    else "candidate_id_is_not_replacement_text"
                ),
            ))
        transformed_indices = {rule.token_index for rule in eligible_rules}
        for token in tokens:
            if token.language.label in {
                "UNKNOWN", "OTHER", "TELUGU_SCRIPT", "NUMBER", "PUNCTUATION"
            }:
                skipped.append(SkippedTransformation(
                    token_index=token.index,
                    operation="token",
                    reason=f"protected_label:{token.language.label}",
                ))
            elif token.index not in transformed_indices:
                skipped.append(SkippedTransformation(
                    token_index=token.index,
                    operation="token",
                    reason="no_authorized_transformation_rule",
                ))

        return AssistedInputResult(
            original_input=original_input,
            normalized_input=normalized_input,
            assisted_input=assisted,
            transformations=applied,
            skipped_transformations=skipped,
            # Current applied records are synthetic test fixtures only.
            meaningful_assistance=False,
            assisted_input_equals_original=assisted == original_input,
            normalization_only=(
                not applied and assisted == normalized_input
                and normalized_input != original_input
            ),
        )
    except Exception:
        reason = "input_or_transformation_validation_failed"
        return AssistedInputResult(
            original_input=original_input,
            normalized_input=normalized_input,
            assisted_input=original_input,
            transformations=[],
            skipped_transformations=[
                *skipped,
                SkippedTransformation(operation="all", reason=reason),
            ],
            meaningful_assistance=False,
            assisted_input_equals_original=True,
            normalization_only=False,
            fallback=True,
            fallback_reason=reason,
        )
