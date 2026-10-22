"""Fail-closed execution for the approved cumulative four-condition design."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError

from app.schemas.analysis import AnalyzeRequest
from app.schemas.four_condition import (
    ConditionExecution, ConditionResourceBinding, ConditionStageTrace,
    ConditionTransformation, FourConditionArtifact,
    FourConditionConfiguration, FourConditionExampleResult,
)
from app.services.ambiguity_resolution import resolve_ambiguities
from app.services.google_translation import PROVIDER_ID as VERIFIED_PROVIDER_ID
from app.services.linguistic_resources import resource_readiness
from app.services.pipeline import analyze
from app.services.preprocessing import normalize_whitespace
from app.services.translation import (
    TranslationConfiguration, TranslationProvider, translate_text,
)
from app.services.transliteration import _is_telugu_candidate


class FourConditionExecutionError(ValueError):
    pass


class ConditionDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    condition_id: Literal[
        "direct_v1", "normalized_v1", "transliterated_v1", "ambiguity_aware_v1",
    ]
    version: Literal["1.0"] = "1.0"
    order: int
    dependencies: tuple[str, ...]
    resource_kinds: tuple[Literal["normalizer", "transliterator", "contextual_transformer"], ...]
    purpose: str
    input_policy: str


CONDITION_REGISTRY = (
    ConditionDefinition(
        condition_id="direct_v1", order=0, dependencies=(), resource_kinds=(),
        purpose="Exact-source direct translation baseline.",
        input_policy="exact original source; no normalization or transformations",
    ),
    ConditionDefinition(
        condition_id="normalized_v1", order=1, dependencies=("direct_v1",), resource_kinds=("normalizer",),
        purpose="Incremental contribution of reviewed linguistic normalization.",
        input_policy="eligible reviewed linguistic normalizer applied to original source",
    ),
    ConditionDefinition(
        condition_id="transliterated_v1", order=2, dependencies=("normalized_v1",), resource_kinds=("normalizer", "transliterator"),
        purpose="Incremental contribution of selective transliteration after normalization.",
        input_policy="normalized output followed by eligible reviewed Romanized Telugu transliteration",
    ),
    ConditionDefinition(
        condition_id="ambiguity_aware_v1", order=3, dependencies=("transliterated_v1",), resource_kinds=("normalizer", "transliterator", "contextual_transformer"),
        purpose="Incremental contribution of reviewed context-conditioned transformations.",
        input_policy="transliterated output followed by an eligible contextual rule bound to a resolved decision",
    ),
)
CONDITION_IDS = tuple(item.condition_id for item in CONDITION_REGISTRY)


@dataclass(frozen=True)
class _Construction:
    text: str
    intermediate: dict[str, str]
    transformations: tuple[ConditionTransformation, ...]
    skipped: tuple[str, ...]
    stages: tuple[ConditionStageTrace, ...]
    resource_references: tuple[str, ...]
    intervention_applied: bool
    test_fixture: bool


def _resource_blocker(
    kind: str,
    binding: ConditionResourceBinding | None,
    *,
    allow_test_fixtures: bool,
) -> str | None:
    if binding is None:
        return f"resource_missing:{kind}"
    blockers = resource_readiness(binding.manifest)
    if blockers:
        return "resource_ineligible:" + ",".join(blockers)
    if binding.test_only and not allow_test_fixtures:
        return f"resource_test_only:{kind}"
    if kind == "contextual_transformer" and not binding.test_only and any(
        mapping.ambiguity_rule_id.startswith("fixture.")
        for mapping in binding.contextual_mappings
    ):
        return "resource_uses_illustrative_ambiguity_rule"
    return None


def _binding_ref(binding: ConditionResourceBinding) -> str:
    prefix = "test-only:" if binding.test_only else "resource:"
    return f"{prefix}{binding.kind}/{binding.manifest.resource_id}@{binding.manifest.resource_version}"


def _original_offset_map(value: str) -> list[int]:
    """Map code-point offsets in whitespace-normalized text back to source."""
    offsets: list[int] = []
    for match in re.finditer(r"\S+", value):
        if offsets:
            offsets.append(match.start())  # normalized separator; no token spans it
        offsets.extend(range(match.start(), match.end()))
    return offsets


def _apply_mapping_rules(
    input_text: str,
    binding: ConditionResourceBinding,
    *,
    context=None,
) -> tuple[str, tuple[ConditionTransformation, ...], tuple[str, ...], tuple]:
    analysis = analyze(AnalyzeRequest(text=input_text, translate=False), translation_provider=None)
    tokens_by_index = {token.index: token for token in analysis.tokens}
    offset_map = _original_offset_map(input_text)
    selected: dict[int, tuple[object, str | None, str | None]] = {}
    skipped: list[str] = []
    decisions = ()

    if binding.kind == "contextual_transformer":
        records = context if context is not None else resolve_ambiguities(
            normalized_text=analysis.normalized_text,
            tokens=analysis.tokens,
            transliterations=analysis.transliterations,
        )
        decisions = tuple(records)
        mappings = {item.rule_id: item for item in binding.contextual_mappings}
        manifest_rules = {item.rule_id: item for item in binding.manifest.rules}
        for decision in records:
            if decision.status != "resolved" or decision.selected_candidate is None:
                skipped.append(f"context_unresolved:{decision.rule_id}:{decision.token_index}")
                continue
            if decision.rule_id.startswith("fixture.") and not binding.test_only:
                skipped.append(f"illustrative_context_rejected:{decision.rule_id}")
                continue
            matches = [mapping for mapping in binding.contextual_mappings
                if mapping.ambiguity_rule_id == decision.rule_id
                and mapping.candidate_id == decision.selected_candidate]
            if len(matches) != 1:
                skipped.append(f"context_mapping_unavailable:{decision.rule_id}:{decision.selected_candidate}")
                continue
            mapping = matches[0]
            rule = manifest_rules[mapping.rule_id]
            token = tokens_by_index.get(decision.token_index)
            if token is None or token.text != rule.source_surface or token.language.label != rule.source_language:
                skipped.append(f"context_source_mismatch:{mapping.rule_id}")
                continue
            if rule.entity_preservation != "confirmed_non_entity":
                skipped.append(f"entity_preservation_unconfirmed:{mapping.rule_id}")
                continue
            selected[token.index] = (rule, decision.rule_id, decision.selected_candidate)
    else:
        by_surface: dict[tuple[str, str], list[object]] = {}
        for rule in binding.manifest.rules:
            by_surface.setdefault((rule.source_surface.casefold(), rule.source_language), []).append(rule)
        allowed = {"TELUGU_ROMANIZED", "ENGLISH"} if binding.kind == "normalizer" else {"TELUGU_ROMANIZED"}
        for token in analysis.tokens:
            label = token.language.label
            if label not in allowed:
                skipped.append(f"protected_language:{token.index}:{label}")
                continue
            rules = by_surface.get((token.text.casefold(), label), [])
            if len(rules) > 1:
                raise FourConditionExecutionError("resource_has_ambiguous_exact_match_rules")
            if not rules:
                skipped.append(f"no_rule_match:{token.index}")
                continue
            rule = rules[0]
            if binding.kind == "transliterator" and not _is_telugu_candidate(rule.replacement):
                skipped.append(f"invalid_transliteration_candidate:{rule.rule_id}")
                continue
            selected[token.index] = (rule, None, None)

    edits: list[tuple[int, int, str]] = []
    transformations: list[ConditionTransformation] = []
    for token_index, (rule, ambiguity_rule_id, candidate_id) in selected.items():
        token = tokens_by_index[token_index]
        if rule.replacement == token.text:
            skipped.append(f"unchanged_candidate:{rule.rule_id}")
            continue
        if token.end <= token.start or token.end > len(offset_map):
            raise FourConditionExecutionError("token offsets could not be mapped to original input")
        source_start = offset_map[token.start]
        source_end = offset_map[token.end - 1] + 1
        transformations.append(ConditionTransformation(
            operation=binding.kind,
            resource_id=binding.manifest.resource_id,
            resource_version=binding.manifest.resource_version,
            rule_id=rule.rule_id,
            rule_version=rule.rule_version,
            token_index=token.index,
            start=source_start,
            end=source_end,
            before=token.text,
            after=rule.replacement,
            evidence_references=rule.evidence_references,
            ambiguity_rule_id=ambiguity_rule_id,
            candidate_id=candidate_id,
            context_evidence=(
                next(record.evidence for record in decisions
                    if record.rule_id == ambiguity_rule_id
                    and record.selected_candidate == candidate_id
                    and record.token_index == token.index)
                if ambiguity_rule_id is not None else None
            ),
        ))
        edits.append((source_start, source_end, rule.replacement))

    output = input_text
    for start, end, replacement in sorted(edits, reverse=True):
        output = output[:start] + replacement + output[end:]
    return output, tuple(transformations), tuple(sorted(skipped)), decisions


def _blocked_condition(
    condition: ConditionDefinition,
    original_input: str,
    reason: str,
    *,
    intermediate: dict[str, str] | None = None,
    stages: tuple[ConditionStageTrace, ...] = (),
    transformations: tuple[ConditionTransformation, ...] = (),
    skipped: tuple[str, ...] = (),
    resource_references: tuple[str, ...] = (),
    research_eligible: bool = False,
) -> ConditionExecution:
    return ConditionExecution(
        condition_id=condition.condition_id,
        dependencies=condition.dependencies,
        status="blocked",
        blocked_reason=reason,
        original_input=original_input,
        intermediate_inputs=intermediate or {},
        intended_provider_input=None,
        provider_call_attempted=False,
        translation=None,
        resource_references=resource_references,
        transformations=transformations,
        skipped_transformations=skipped,
        stages=stages,
        intervention_applied=bool(transformations),
        research_eligible=research_eligible,
    )


def _build_conditions(
    original_input: str,
    configuration: FourConditionConfiguration,
    *,
    allow_test_fixtures: bool,
    contextual_decisions=None,
) -> tuple[ConditionExecution, ...]:
    built: dict[str, _Construction] = {}
    records: dict[str, ConditionExecution] = {}

    for definition in CONDITION_REGISTRY:
        if not definition.dependencies:
            built[definition.condition_id] = _Construction(
                text=original_input, intermediate={"original": original_input},
                transformations=(), skipped=(), stages=(), resource_references=(),
                intervention_applied=False, test_fixture=False,
            )
            records[definition.condition_id] = ConditionExecution(
                condition_id=definition.condition_id, dependencies=(), status="completed",
                original_input=original_input,
                intermediate_inputs={"original": original_input},
                intended_provider_input=original_input,
                provider_call_attempted=False,
                translation=None,
                research_eligible=True,
            )
            continue

        previous_id = definition.dependencies[0]
        previous = built.get(previous_id)
        if previous is None:
            earlier = records.get(previous_id)
            records[definition.condition_id] = _blocked_condition(
                definition, original_input, f"dependency_blocked:{previous_id}",
                intermediate=earlier.intermediate_inputs if earlier else None,
                stages=earlier.stages if earlier else (),
                transformations=earlier.transformations if earlier else (),
                skipped=earlier.skipped_transformations if earlier else (),
                resource_references=earlier.resource_references if earlier else (),
            )
            continue

        requirements = definition.resource_kinds
        missing = next((kind for kind in requirements if kind not in configuration.resources), None)
        if missing:
            records[definition.condition_id] = _blocked_condition(
                definition, original_input, f"resource_missing:{missing}",
                intermediate=previous.intermediate,
                stages=previous.stages,
                transformations=previous.transformations,
                skipped=previous.skipped,
                resource_references=previous.resource_references,
            )
            continue
        blockers = [
            (kind, _resource_blocker(kind, configuration.resources[kind], allow_test_fixtures=allow_test_fixtures))
            for kind in requirements
        ]
        blocker = next(((kind, reason) for kind, reason in blockers if reason), None)
        if blocker:
            kind, reason = blocker
            records[definition.condition_id] = _blocked_condition(
                definition, original_input, reason or f"resource_ineligible:{kind}",
                intermediate=previous.intermediate,
                stages=previous.stages,
                transformations=previous.transformations,
                skipped=previous.skipped,
                resource_references=previous.resource_references,
            )
            continue

        stage_kind = requirements[-1]
        binding = configuration.resources[stage_kind]
        source = previous.text
        try:
            if contextual_decisions is not None and stage_kind == "contextual_transformer" and not binding.test_only:
                raise FourConditionExecutionError("injected_context_decisions_are_test_only")
            transformed, applied, skipped, decisions = _apply_mapping_rules(
                source, binding, context=contextual_decisions if stage_kind == "contextual_transformer" else None,
            )
        except FourConditionExecutionError:
            records[definition.condition_id] = ConditionExecution(
                condition_id=definition.condition_id, dependencies=definition.dependencies,
                status="failed", original_input=original_input,
                intermediate_inputs=previous.intermediate,
                intended_provider_input=None, provider_call_attempted=False,
                translation=None,
                resource_references=previous.resource_references + (_binding_ref(binding),),
                transformations=previous.transformations,
                skipped_transformations=previous.skipped + ("input_construction_failed",),
                stages=previous.stages,
                intervention_applied=False,
                research_eligible=False,
            )
            continue
        ref = _binding_ref(binding)
        stage_trace = ConditionStageTrace(
            stage=stage_kind,
            input_text=source,
            output_text=transformed,
            status="completed",
            resource_id=binding.manifest.resource_id,
            resource_version=binding.manifest.resource_version,
            resource_fingerprint=binding.fingerprint,
            changed=transformed != source,
            applied_transformations=len(applied),
            skipped_reasons=skipped,
            ambiguity_decisions=decisions,
        )
        intermediate = dict(previous.intermediate)
        intermediate[stage_kind] = transformed
        reference_list = previous.resource_references + (ref,)
        transforms = previous.transformations + applied
        skipped_all = previous.skipped + skipped
        test_fixture = previous.test_fixture or binding.test_only
        research_eligible = not test_fixture and all(
            configuration.resources[kind] is not None for kind in requirements
        )
        construction = _Construction(
            text=transformed,
            intermediate=intermediate,
            transformations=transforms,
            skipped=skipped_all,
            stages=previous.stages + (stage_trace,),
            resource_references=reference_list,
            intervention_applied=previous.intervention_applied or bool(applied),
            test_fixture=test_fixture,
        )
        built[definition.condition_id] = construction
        records[definition.condition_id] = ConditionExecution(
            condition_id=definition.condition_id,
            dependencies=definition.dependencies,
            status="completed",
            original_input=original_input,
            intermediate_inputs=intermediate,
            intended_provider_input=transformed,
            provider_call_attempted=False,
            translation=None,
            resource_references=reference_list,
            transformations=transforms,
            skipped_transformations=skipped_all,
            stages=construction.stages,
            intervention_applied=construction.intervention_applied,
            research_eligible=research_eligible,
        )

    return tuple(records[key] for key in CONDITION_IDS)


def run_four_condition_experiment(
    example_id: str,
    original_input: str,
    *,
    configuration: FourConditionConfiguration,
    provider: TranslationProvider | None,
    allow_provider_calls: bool = False,
    allow_test_fixtures: bool = False,
    contextual_decisions=None,
) -> FourConditionArtifact:
    """Build all four cumulative conditions and attempt each executable call.

    Resource-blocked conditions are retained as blocked records. Test-only
    resources and the mock provider taint the artifact so research evaluation
    can reject them; they are never promoted to eligible results.
    """
    if not isinstance(original_input, str) or not original_input.strip():
        raise FourConditionExecutionError("original_input must be a nonblank string")
    if not example_id.strip():
        raise FourConditionExecutionError("example_id must be nonblank")
    if provider is not None and allow_provider_calls is not True:
        raise FourConditionExecutionError("provider calls require explicit authorization")
    provider_id = None
    if provider is not None:
        try:
            provider_id = provider.provider_id
        except Exception:
            provider_id = None
    # Only the configured project adapter is currently recognized as a
    # research provider. Unknown/injected providers remain usable for tests,
    # but their artifacts are visibly tainted and cannot be scored.
    test_fixture = (
        allow_test_fixtures
        or (provider is not None and provider_id != VERIFIED_PROVIDER_ID)
    )
    model = getattr(provider, "requested_model", None) if provider is not None else None
    if configuration.requested_model is None and isinstance(model, str) and model.strip():
        configuration = configuration.model_copy(update={"requested_model": model})
    records = list(_build_conditions(
        original_input, configuration, allow_test_fixtures=allow_test_fixtures,
        contextual_decisions=contextual_decisions,
    ))
    invocation_order: list[str] = []
    translation_config = TranslationConfiguration(
        target_language=configuration.target_language,
        requested_model=configuration.requested_model,
        generation_settings=configuration.requested_generation_settings,
    )
    by_id = {item.condition_id: index for index, item in enumerate(records)}
    for condition_id in configuration.execution_order:
        index = by_id[condition_id]
        record = records[index]
        if record.status != "completed" or record.intended_provider_input is None:
            continue
        outcome = translate_text(
            record.intended_provider_input,
            requested=True,
            provider=provider,
            configuration=translation_config,
        )
        attempted = outcome.input_text is not None
        if attempted:
            invocation_order.append(condition_id)
        records[index] = record.model_copy(update={
            "provider_call_attempted": attempted,
            "provider_input": outcome.input_text,
            "translation": outcome,
        })
    result_is_test_fixture = test_fixture or any(
        ref.startswith("test-only:") for record in records for ref in record.resource_references
    )
    if result_is_test_fixture:
        records = [record.model_copy(update={"research_eligible": False}) for record in records]
    result = FourConditionExampleResult(
        original_input=original_input,
        configuration_fingerprint=configuration.fingerprint,
        conditions=tuple(records),
        invocation_order=tuple(invocation_order),
        test_fixture=result_is_test_fixture,
    )
    return FourConditionArtifact(
        schema_version="1.0", example_id=example_id,
        split=configuration.split, configuration=configuration, result=result,
    )


def load_condition_resource(path: str | Path) -> ConditionResourceBinding:
    """Load a UTF-8 JSON resource binding without accepting duplicate keys."""
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8-sig"), object_pairs_hook=unique)
        return ConditionResourceBinding.model_validate(value)
    except (OSError, UnicodeError, json.JSONDecodeError, ValidationError, ValueError):
        raise FourConditionExecutionError("condition resource could not be loaded or validated") from None
