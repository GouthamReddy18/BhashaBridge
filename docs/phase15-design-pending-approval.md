# Phase 15 four-condition design and implementation status

**Status:** Approved cumulative design, implemented as a separate versioned contract. The legacy two-arm API and artifacts remain unchanged. The design is an execution protocol; it does not establish empirical findings.

## What the current methodology says

`docs/research_question.md` names direct translation, normalization plus translation, selective transliteration plus translation, and ambiguity-aware processing when compatible components exist. `docs/methodology.md` refers to four pipeline variants. These names do not specify whether the latter conditions are independent or cumulative, whether transliteration includes normalization, or what text/input an ambiguity decision contributes to translation.

That missing detail matters in the current implementation:

- The production normalization contract collapses whitespace; no reviewed linguistic normalization resource is configured. Whitespace normalization alone is not the explicit linguistic normalization named in the research question.
- No reviewed production transliteration resource or engine is available. The existing transliteration seam is optional and can report unavailable.
- The ambiguity service emits decision/evidence records. The sole bank rule is illustrative; candidate IDs/descriptions are not replacement text, and the translation provider accepts text rather than structured ambiguity context. There is no reviewed Telugu-English ambiguity resource.
- The current runner and evaluation report are explicitly two-arm contracts (direct and assisted). They cannot represent four independently configured variants or their per-variant and matched-pair populations without a new versioned artifact/report contract.

## Approved staged addition design

Use a **staged addition (sequential ablation) design**, with each condition adding one capability to the preceding condition:

| Stable ID | Proposed condition | Provider input | Increment represented |
|---|---|---|---|
| `direct_v1` | Direct baseline | Exact original source text | Baseline |
| `normalized_v1` | Reviewed linguistic normalization | Original text after only approved normalization rules | Normalization over baseline |
| `transliterated_v1` | Normalization plus selective transliteration | Normalized input with only eligible tokens changed by reviewed transliteration rules | Transliteration added after normalization |
| `ambiguity_aware_v1` | Normalization, selective transliteration, and contextual disambiguation | Prior condition's constructed text plus only independently reviewed context-dependent transformations explicitly authorized for provider input | Disambiguation added after the preceding stages |

This is a cumulative pipeline, not a factorial design. Its planned contrasts are `normalized_v1` versus `direct_v1`, `transliterated_v1` versus `normalized_v1`, `ambiguity_aware_v1` versus `transliterated_v1`, and the total `ambiguity_aware_v1` versus `direct_v1`. It does not estimate a transliteration effect without normalization, or an ambiguity effect without the preceding stages. Each comparison must use the same eligible example IDs and reference translations, with available-output and matched populations reported separately.

All variants would receive the same requested provider, target language, model/generation settings, timeout policy, and eligible source/reference set. Variant identity would be independent of invocation order. Requested and provider-confirmed settings would remain separate. A condition whose required reviewed resource is unavailable would be recorded as blocked/unavailable; it would not borrow another variant's input or use synthetic test rules. Ambiguity analysis alone, without an authorized input transformation or a provider interface for structured context, would not count as an executed ambiguity-aware translation condition.

The user approved the cumulative construction above. `backend/app/services/four_condition_experiment.py` implements exact-source baseline input and cumulative reviewed resource stages. A missing or ineligible stage blocks downstream variants; whitespace collapse alone never qualifies as linguistic normalization. Context decisions affect provider input only through explicit candidate-to-resource mappings. The current illustrative bank rule is rejected for research use.

The versioned artifact and evaluator live in `backend/app/schemas/four_condition.py` and `backend/app/services/four_condition_evaluation.py`. The evaluator reports per-condition successful output populations separately from ID-matched comparisons. It uses the project's fixed corpus BLEU/chrF implementation, does not create human ratings, and excludes test-fixture outputs from scoring. No production resources or genuinely eligible benchmark are currently available, so the framework is not evidence of system quality.

Run `python backend/scripts/run_four_condition_experiment.py --help`, `python backend/scripts/evaluate_four_condition_experiment.py --help`, and `python backend/scripts/validate_four_condition_report.py --help` for the local interfaces. Provider requests require an explicit flag. Artifact and report paths are exclusive-create. Never label synthetic fixture outputs as research evidence.
