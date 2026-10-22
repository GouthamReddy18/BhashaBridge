# Phase 6D.1 Evaluation Protocol

## Status and objective

This document defines the protocol and tooling for a future empirical paired evaluation of BhashaBridge's direct and assisted translation arms. The local evaluator can calculate reference-based proxy scores from explicitly supplied artifacts, but no real benchmark evaluation or research result is reported here. The primary question is whether assisted translation preserves intended meaning better than direct translation on eligible, reviewed Telugu-English code-mixed examples. Improvement is a hypothesis, not an assumption.

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

## Phase 6D.2 metric implementation

### Reference-based translation quality

Phase 6D.2 implements corpus BLEU-4 and corpus chrF using the versioned in-project implementation `bhashabridge.metrics` 1.0.0. No metric package was installed in the project environment, so this implementation is explicitly versioned and tested locally rather than being represented as SacreBLEU output. Scores from this implementation must not be compared with values from another implementation or configuration without a compatibility study. Neither metric replaces human judgment of meaning.

Both metrics first normalize each reference and hypothesis to Unicode NFC and collapse all whitespace runs to one ASCII space. Matching is case-sensitive. BLEU splits only on whitespace, leaving punctuation attached to its token. It uses one reference per example, clipped corpus n-gram counts through order 4, exponential zero-count smoothing (the smoothing factor doubles for each zero-match order), effective order (orders with no possible hypothesis n-grams are omitted), the standard brevity penalty, and a geometric mean over active orders. Scores are on a 0–100 scale.

chrF uses character n-grams of orders 1–6, beta 2, and word order 0 (chrF, not chrF++). Whitespace is removed before character n-gram extraction; Unicode code points are counted after NFC normalization. Clipped counts are accumulated by order across the corpus, precision and recall are macro-averaged over orders with at least one reference or hypothesis n-gram, and the corpus F-beta score is reported on a 0–100 scale. Empty corpora have no score. Blank references or hypotheses are rejected by the metric functions; the evaluator never passes missing or failed outputs to them.

Scores are corpus-level. Optional sentence-level proxy comparisons are available only with `--include-per-example`; they are exploratory, unstable for small corpora, and are not individual meaning judgments. The report always gives each arm's available-success population and both arms' identical matched-success population. It calculates the paired aggregate difference as the assisted corpus score minus the direct corpus score on the matched IDs; this is not the average of sentence-level differences. Failed, unavailable, disabled, missing, and invalid results stay visible in operational outcome counts. A failure is never converted to a score. If the dataset readiness gate fails, scoring is suppressed.

### Human semantic-preservation rubric

This rubric is a proposed protocol only. The repository does not yet define a genuine human-rating artifact schema, and Phase 6D.2 does not accept or aggregate ratings. No ratings or semantic-preservation score are created by the evaluator. When a compatible schema is approved, independent raters should compare each output with the source and reviewed intended meaning, without seeing which arm produced it where feasible, using this ordinal scale:

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

## Paired artifact and CLI

The annotation input is the existing UTF-8 JSONL format. The paired-results input is UTF-8 JSONL with one object per example: `schema_version` must be `"1.0"`, `example_id` joins to the annotation `id`, and `result` is the serialized existing `PairedExperimentResult` model (including `original_input`, `configuration`, `direct`, `assisted`, `assisted_input`, `analysis`, `same_provider_instance_supplied`, `invocation_order`, and provider protocol metadata). Each arm carries its `arm`, `intended_input`, optional actual `provider_input`, typed `translation` outcome, and `provider_confirmed` metadata. The result model validates arm identity and invocation invariants. Duplicate result IDs and malformed/schema-invalid rows are rejected. A pair whose original input does not exactly match the annotation source is counted as invalid for both arms. The two JSONL inputs are read-only.

Example invocation (supply real reviewed annotation and real provider artifacts explicitly):

```powershell
python backend/scripts/evaluate_paired_experiment.py `
  --annotations path/to/reviewed_annotations.jsonl `
  --paired-results path/to/paired_results.jsonl `
  --split test `
  --output path/to/evaluation_report.json
```

The CLI runs structural validation and the Phase 6D.1 readiness check on the supplied annotation file. Any blocking readiness error makes the file ineligible and suppresses all scores; an empty requested split or no successful output population is also a nonzero result. Rows outside the requested split are excluded from the scoring denominator. Within a ready split, missing pair artifacts and all provider outcomes remain in the operational denominator. The report is deterministic for identical inputs and has no timestamp. It omits full source/translation text and provider exception details; provider IDs are included only when they match a conservative safe-identifier pattern. `--include-per-example` opts into example IDs and sentence-level proxy scores. Existing report files are preserved unless `--overwrite` is given.

In the JSON report, `records_discovered` counts annotation rows in the supplied file; `eligible_records` counts records in the requested split after the dataset-wide readiness gate passes, before considering paired-output availability; `excluded_records` counts rows excluded by the readiness gate or requested split. Exclusion-reason counts can overlap when one record has multiple readiness issues. `invalid_pair_records` counts joined results excluded for source or provider/configuration incompatibility, and `orphan_pair_results` counts result IDs absent from the annotation file. Each arm's outcome-count denominator is `eligible_records`; status counts include success, failed, unavailable, disabled, missing, and invalid. `attempted_invocations`, pre-invocation failures, configured execution-order counts, and actual invocation-trace counts are reported separately. Runs with different requested model/settings or conflicting confirmed provider IDs are marked invalid rather than mixed into a corpus. An `invalid_provider_output` failure code is a failed provider call; it is not scored. The current paired-result schema does not permit disabled arm results, so valid artifacts report zero disabled outcomes. The project's `mock.test` provider is explicitly classified invalid and is never scored.

The current experiment schema models requested translation outcomes, so its provider-free outcome is `unavailable`; `disabled` is not a valid completed paired-arm result and is reported as zero for valid artifacts. Invalid artifact schemas are fatal input errors rather than silently repaired records. Human semantic-preservation aggregation is deferred because the repository has no genuine human-rating artifact schema. The report identifies this as deferred and emits no human score.

Phase 6D.1 implements the protocol and metadata-readiness checks. Phase 6D.2 implements local scoring and reporting infrastructure only. It does not acquire/review eligible data, run a real provider, add a human-rating schema, or establish a research result. No significance test is performed.

## Phase 6D.3 evaluation-report validation

Validate a saved Phase 6D.2 report with `python backend/scripts/validate_evaluation_report.py path/to/report.json`. The CLI is read-only. Exit code 0 means the report has supported schema and metric versions and passes structural and cross-field integrity checks; exit code 1 means malformed JSON or an invalid report; exit code 2 means an unsupported version or input/usage error. Diagnostics have stable codes and field locations and do not echo raw report values.

The validator requires explicit schema and metric configuration, strictly typed finite numbers, supported field values, and the project BLEU/chrF configuration. It checks that eligible plus excluded records equal discovered records; each arm's outcomes sum to the eligible denominator; successful outcomes equal that arm's available-output population; and matched population counts agree with the paired count and do not exceed either arm's available population. It also checks zero-population null scores, score ranges, assisted-minus-direct matched-corpus differences, execution/invocation counts, readiness/status consistency, exclusion summaries, and complete optional per-example diagnostics. The comparison tolerance is 1e-9 relative and absolute; the report's corpus metrics are not recomputed from aggregate values.

The report is valid only as a serialized artifact under schema 1.0 and `bhashabridge.metrics` 1.0.0. Optional diagnostic lists may be omitted; when present they must cover the full matched population. The validator rejects claims of human semantic-preservation scores because this report contract supports only deferred ratings. Dataset readiness remains a separate check on annotation inputs. **A VALID report establishes structural and internal consistency under the supported contract. It does not authenticate dataset provenance, independently verify the original translation outputs, prove metric correctness from absent source artifacts, or establish semantic improvement.** BLEU/chrF remain reference-based proxies; no statistical inference or research conclusion is produced by report validation.
