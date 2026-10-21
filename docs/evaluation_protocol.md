# Phase 6D.1 Evaluation Protocol

## Status and objective

This document defines the protocol for a future paired evaluation of BhashaBridge's direct and assisted translation arms. It does not run an evaluation or calculate quality scores. The primary question is whether assisted translation preserves intended meaning better than direct translation on eligible, reviewed Telugu-English code-mixed examples. Improvement is a hypothesis, not an assumption.

For each source example, Arm A receives the exact original source text and Arm B receives the output of the existing assisted-input builder. A valid pair uses the same example ID, target-language requirement, and controlled provider configuration. Record requested settings separately from provider-confirmed settings. The current provider interface cannot confirm or accept target language, model, or generation settings; those values must not be represented as confirmed.

## Evaluation population and eligibility

The target population is Romanized Telugu-English code-mixed source text. A future test example must have:

- A stable unique ID, original text, project-normalized text, and structurally valid annotations.
- Explicit source and annotation provenance, a completed review record, and a human contribution to the reviewed annotation.
- A nonblank, human-reviewed English `reference_translation` with reviewed field provenance and a source reference.
- A reviewed `intended_meaning` with human-contributed field provenance and a source reference. This is the meaning raters should preserve; it is not a translation score.
- An annotation version and a valid `split` (`train`, `validation`, or `test`) plus a nonblank `split_group`.
- For `test` records, at least one `TELUGU_ROMANIZED` and one `ENGLISH` token under the project annotation scheme.

The existing annotation schema already supports source text, normalized text, token labels, annotation version, general provenance, review status/date/reviewer ID, optional ambiguity annotations, and a reviewed reference translation with field-level provenance. Phase 6D.1 adds optional `intended_meaning`, `split`, and `split_group` fields without requiring them for existing draft records. The readiness checker requires them for benchmark eligibility. The checker validates metadata consistency; it cannot authenticate a reviewer, prove permissions, or establish linguistic correctness.

Missing references, incomplete or disputed reviews, invalid records, duplicate IDs, missing/invalid split metadata, and inadequate intended-meaning metadata make records ineligible. Before freezing the benchmark, report candidate and eligible counts plus every exclusion reason; define eligibility before looking at provider outputs. Unreviewed illustrative drafts are never promoted automatically. Unsupported language/script patterns are excluded from the stated test population and must be reported as such before an evaluation is frozen.

Dataset ineligibility is distinct from provider execution failure. Once a dataset is frozen and eligible, provider failure or unavailability does not remove that example from the eligible denominator. Report the failure and completion counts. Identity-only assistance, whitespace-normalization-only assistance, fallback, and any future authorized linguistic assistance must be reported as separate categories. Synthetic test transformations are mechanism fixtures, not eligible linguistic assistance or evidence.

## Paired design and execution

Use identical eligible example IDs in both arms and hold provider, target-language requirement, and provider configuration constant. Preserve arm identity independently from execution order and record the configured and actual invocation order. The Phase 6C service supports `direct_first` and `assisted_first`; order control improves traceability but does not remove nondeterminism, state, rate-limit, transient-failure, or provider-side effects.

For nondeterministic providers, predefine and report the number of repeated trials per example and arm. Keep each trial paired by example ID, trial identifier, provider identity/configuration, and compatible execution conditions. Record successes, failures, unavailable calls, and incomplete pairs. Never treat two successful calls as a successful research outcome.

Do not expose reference translations or intended meanings to the translation provider. Keep final test references and labels out of prompt/rule development, model selection, and threshold tuning. Freeze the test set and evaluation procedure before inspecting test outputs. Report results separately by assistance category and ambiguity behavior, including resolution coverage and abstentions.

## Metric specifications (planned; not implemented)

### Reference-based translation quality

Corpus chrF is a preferred candidate metric for future exploration because character n-grams can be useful for morphologically varied and transliterated outputs. It has not been validated for this project or dataset. Corpus BLEU may be reported as a secondary reference-based metric with a fixed, published tokenization and normalization procedure. Neither metric replaces human judgment of meaning.

These metrics require frozen, reviewed English reference translations and consistent hypotheses. Interpret scores at corpus level; sentence-level scores are unstable and must not be treated as per-example judgments. Document the implementation/version, tokenization, case handling, punctuation handling, and normalization. Report arm-level metric coverage and paired coverage. Missing hypotheses receive no fabricated substitute: retain the example in operational denominators, report missing output rates, and calculate quality only on clearly identified available-output sets. Also show paired metric differences only for IDs with compatible outputs in both arms. If references are unavailable, report no score.

### Human semantic-preservation rubric

Independent raters compare each output with the source and reviewed intended meaning, without seeing which arm produced it where feasible. Use this ordinal scale:

| Score | Guidance |
| --- | --- |
| 0 | Meaning substantially incorrect: the central event, participants, polarity, or intent is wrong. |
| 1 | Major meaning loss or distortion: important propositions or relationships are missing or changed. |
| 2 | Meaning partially preserved: the gist is recognizable, but a material detail or relation is wrong or absent. |
| 3 | Meaning mostly preserved: only minor nuance, wording, or noncentral detail differs. |
| 4 | Intended meaning fully preserved: all material propositions and relevant nuance are conveyed. |

Raters should assess meaning rather than fluency alone, record uncertainty, and cite the affected span or proposition when scores differ. Use independent assessments where feasible; preserve raw ratings, adjudication decisions, and reasons. Report disagreements. Do not calculate inter-rater agreement statistics until actual independent ratings exist.

### Operational and behavior counts

Report eligible example count; attempted, successful, failed, and unavailable translations per arm; paired completion count; and incomplete-pair reasons. Separately report assisted-input category counts (identity, normalization-only, fallback, synthetic fixture, and any future authorized assistance), ambiguity-resolution coverage, resolved count, and abstention count. Operational completion is not translation quality or semantic preservation.

### Paired differences and missingness

For each metric, compare direct and assisted results only for compatible observations from the same example ID and comparable provider configuration/trial. State the sign convention (assisted minus direct), paired sample count, and missingness. Report arm-level coverage and all failures alongside any paired score. Explain every exclusion and denominator. Do not impute missing translations or conduct statistical significance testing in Phase 6D.1.

## Dataset governance and leakage controls

Assign a `split_group` before splitting. Group exact duplicates, known near-duplicates/paraphrases, source/conversation families, shared templates, generated variants, and repeated ambiguity contexts together. Every group must remain wholly within one split. Assign groups deterministically using a versioned mapping and record the method/seed outside the record as part of dataset release documentation. The readiness checker enforces group consistency and detects exact duplicate normalized source text crossing splits; it does not detect paraphrases, templates, or semantic near-duplicates.

Use training data only for fitting, if a trainable component is later introduced. Use validation data for development choices. Keep test data held out for final reporting. Freeze split assignments and annotation versions for a release; changes require a new version and documented impact review. Do not use final test examples, references, or ratings to create rules, prompts, or thresholds. Review normalization, transliteration, and linguistic resources for test-derived examples or annotations before release; do not tune them against final test outcomes.

The current 16 illustrative records remain unreviewed drafts. Do not assign them benchmark splits or convert them into evaluation data merely to make the readiness check pass. Build future splits only after annotation, review, provenance/licensing checks, and group assignment are complete.

## Readiness tooling and phase boundary

Run structural validation with `python backend/scripts/validate_dataset.py path/to/data.jsonl`. Run the separate future-benchmark eligibility check with `python backend/scripts/check_evaluation_readiness.py path/to/data.jsonl`. The readiness checker reuses structural validation and reports blocking errors separately from warnings; it reads but never changes the source dataset. A structurally valid draft dataset is expected to report `NOT READY`.

Phase 6D.1 implements this protocol and metadata-readiness checks only. Phase 6D.2 remains future work: acquiring and reviewing eligible data, selecting and pinning metric tooling, building controlled evaluation orchestration/reporting, and conducting human evaluation. No BLEU/chrF implementation, semantic score, significance test, real provider, benchmark split, or research result is provided here.
