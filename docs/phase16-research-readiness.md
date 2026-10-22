# Phase 16 research-readiness audit

**Audit date:** 2026-10-22
**Repository checkpoint:** `c50372a` (`main`, initially synchronized with `origin/main`)
**Conclusion:** The software framework is implemented; a genuine four-condition research evaluation is not ready. No eligible dataset, qualified cumulative linguistic resources, real provider output artifacts, or human ratings are present.

## Scope and evidence boundary

This audit reviewed the four-condition schemas, runner, evaluator and report validator; the legacy paired evaluator and human-rating workflow; provider and linguistic service implementations; dataset schemas, draft data and readiness checks; metric code; existing tests; and project documentation. The repository's 16-row illustrative draft, configured environment state, source tree and generated-file locations were inspected. No external provider was called, no resource was downloaded, and no draft data or public API contract was changed. `.vscode/` was already untracked and was preserved.

The resource and review declarations are repository metadata. They are not independently authenticated. Passing structural or report validation does not establish that a claimed review, provider output, license, or linguistic decision is genuine.

## Resource inventory

| Capability | Implemented code/interface | Configured or present resource | Review/validation and use | Current research status |
|---|---|---|---|---|
| Code-mixed normalization | Four-condition normalization stage and resource binding; generic whitespace helper | No qualified Telugu-English normalizer found. Whitespace collapse is generic formatting, not linguistic normalization. | No reviewed resource. Required resource binding prevents the stage from becoming eligible without a declared resource. | Not configured, not validated, not reviewed, not research eligible, unused in research. |
| Romanized Telugu normalization | No qualified implementation/resource found | None | No language-specific validation or review evidence. | Not available. |
| Transliteration | Selective transliteration service seam; disabled unless a verified engine is injected | No engine or weights bundled/configured. No automatic download. | Tests cover interface and synthetic inputs only; no reviewed Romanized Telugu transliteration resource. | Not configured, not validated, not reviewed, not research eligible, unused in research. |
| Language identification | Token/script heuristics and optional IndicLID/FastText branch | Baseline heuristics are present; optional local model is `not_configured`; no local weights found | Heuristics are not accuracy-validated. Optional upstream sentence task is adapted token-by-token and is unvalidated. | Implemented baseline only; no qualified research resource. |
| Contextual ambiguity | Exact-match rule service and transformation metadata | One illustrative English `bank` fixture; no reviewed Telugu-English rule resource | The fixture tests mechanics, not validated Telugu-English ambiguity. Metadata-only decisions do not transform input. | Test/example only; no research-eligible rules. |
| English reference translation | Annotation field and metric pipeline | 16 illustrative draft references; no reviewed benchmark references | Dataset readiness rejects current draft as unreviewed/ineligible. Source rights and linguistic correctness are not established. | No eligible reference set. |
| Human semantic judgments | Versioned pending-task/rating workflow and descriptive aggregation | No human ratings found | Workflow creates pending rows only; reviewer declarations are unauthenticated; no inter-rater statistic or rating result exists. | No judgment data or human score. |
| Translation provider | Google Cloud Translation Basic v2 adapter | Adapter reports `not_configured`; disabled by default; API key absent | Adapter tests use fakes. Romanized Telugu/code-mixed suitability is not established. No call was made. | Only registered provider adapter; currently unavailable for research runs. |

These statuses deliberately distinguish code, configuration, validation, review, eligibility and actual experimental use. A resource manifest's declared review fields do not authenticate the reviewer, source, or license.

## Four-condition contract audit

| Condition | Implementation state | Resource eligibility | Research eligibility now |
|---|---|---|---|
| `direct_v1` | Implemented; sends exact source string and records invocation input | No transformation resource required | The software condition can run only with the configured provider; none is configured, and no reviewed dataset exists. No research result is available. |
| `normalized_v1` | Implemented cumulative stage | Requires a declared eligible normalization resource; whitespace collapse cannot satisfy it | Blocked: no qualified resource. |
| `transliterated_v1` | Implemented cumulative stage | Requires normalization prerequisite and eligible transliteration resource; unsupported tokens are preserved | Blocked: no qualified normalization or transliteration resources. |
| `ambiguity_aware_v1` | Implemented cumulative stage | Requires all prior resources and an authorized mapped contextual transformation | Blocked: no eligible resources or contextual rules. The illustrative `bank` fixture is not research evidence. |

The audit found schema-level gaps that let manually constructed artifacts claim completed stages without eligible resources, let a missing `test_only` declaration default to false, and let downstream stages appear complete when prerequisites were not. Validation now checks resource/stage identity, version and fingerprints, required resources, stage output reconstruction and dependency completion. Ambiguity metadata by itself cannot claim an applied transformation. Test-only/unverified resources and non-registered provider identities taint artifacts and make them ineligible. The evaluator revalidates in-memory Pydantic artifacts to avoid trusting models mutated after initial construction.

The annotation guidance at `data/guidelines/annotation_guidelines.md` documents exact source preservation, normalization and Unicode offsets, conservative language labels, provenance, references, ambiguity abstention, disagreement handling and group-aware splits. It explicitly marks its proposed semantic-rating dimensions as requiring pilot testing. It does not supply a qualified annotator pool, source license, gold labels, adjudication record or validated rating instrument.

## Test-fixture taint and evaluation populations

The four-condition evaluator previously had an `allow_test_fixtures` escape hatch and trusted a caller-set eligibility flag in some cases. The escape hatch is removed; a successful output on any research-ineligible artifact is never scored. The evaluator now checks provider-forwarding metadata consistently across invocations and across eligible examples. The CLI no longer exposes `--allow-test-fixtures`.

The legacy evaluator and rating workflow previously recognized only the literal `mock.test` ID. An injected fake provider using another ID could be scored or enter a human-rating packet. The legacy evaluator and report validator now accept only the repository's currently registered Google adapter ID as a scorable provider; the human-rating task workflow rejects other successful provider IDs. Unknown and mock-provider successes are counted invalid, not successful. This identity policy does not authenticate manually forged artifacts; the limitation is explicit.

For the four-condition report, each arm's available-output population consists of successful, nonblank outputs available for that arm. Each of the five fixed comparisons uses only the intersection of the two arms' eligible successful example IDs and the same reference for each ID. Missing, failed, disabled, unavailable, mock, invalid, test-only or ineligible outputs never become metric values. Operational denominators retain eligible examples and explicit statuses/exclusions; there is no failure imputation. This distinction also holds for legacy paired comparisons.

No human scores are generated by either evaluator. Human-rating task creation writes pending rating rows; it does not invent judgments. Report validators check structure and internal consistency, not authenticity or scientific eligibility in the absence of source artifacts.

## Metric configuration

The code implements project metric package `bhashabridge.metrics` version `1.0.0` without adding dependencies. Both metrics NFC-normalize and collapse whitespace, are case-sensitive, use one reference per example, and score on a 0–100 scale.

- **BLEU:** corpus BLEU-4; whitespace tokenization with punctuation attached; clipped corpus n-gram counts; exponential zero-count smoothing with the multiplier doubled for each zero-match order; effective order; standard brevity penalty.
- **chrF:** corpus character n-grams orders 1–6; beta 2; word order 0 (not chrF++); whitespace removed for character n-grams; clipped counts pooled per order, then macro precision/recall over active orders.

These are project-specific configurations, not SacreBLEU output. Scores cannot be assumed comparable to another implementation/configuration without a compatibility study. BLEU and chrF are reference-based proxies, not semantic-preservation judgments.

## Reproducibility, safety and blockers

Evaluation JSON is emitted deterministically for identical inputs; no timestamp or random seed is introduced into the deterministic metric pipeline. Artifacts retain condition/resource identifiers, versions, configuration fingerprints, input traces, invocation order, outcomes and provider metadata where available. Provider model metadata may be absent; the adapter does not expose a remote immutable revision or request identity. The project does not record repeat-trial identifiers, endpoint revision, hardware/runtime lock, or independently authenticated output provenance. There is no basis for statistical power/sample-size claims; those require a defined target effect and variance assumptions from a legitimate pilot.

CLI output creation uses exclusive creation or an explicit overwrite option, validates source/output path separation, and avoids writing over existing files by default. Provider metadata is constrained/sanitized; credentials are not written to reports. These controls reduce accidental overwrite and disclosure risk but do not authenticate caller-supplied JSON artifacts.

**Blocking facts:** no reviewed dataset or rights/license evidence; no qualified normalizer, transliterator or contextual resource; provider disabled/unconfigured; no real provider outputs; no human ratings. Do not interpret illustrative fixtures, test results, schema status, or a `VALID` report as research results.

## Smallest legitimate route to a first experiment

1. Obtain a rights-cleared Telugu-English code-mixed source collection and document provenance and license.
2. Have qualified annotators independently establish normalized source, token labels, reference translation and intended meaning; adjudicate disagreements and document review.
3. Group related examples and leakage risks before assigning frozen train/validation/test splits; run readiness checks on the complete release.
4. Qualify and document versioned normalization and transliteration resources, then contextual rules, with evidence and review appropriate to each resource. Keep test references out of development.
5. Configure and document an approved provider, target-language and model settings; make explicit any data-transmission decision. Run a small operational pilot before choosing a sample-size/power plan.
6. Freeze protocol, outputs, repeated-trial plan if needed, and analysis before evaluating held-out test data. Collect independent human semantic ratings separately and report coverage and disagreement.

No sample size, provider result, linguistic resource, rating, or improvement claim is supplied by this audit.

## Dataset acquisition and annotation plan

- Collect naturally occurring or properly licensed Telugu-English code-mixed utterances with enough context to resolve the intended meaning. Preserve the original text and document the source, collection method, consent/permission and permitted reuse; exclude material without clear rights.
- Have annotators record the source exactly, canonical `normalized_text`, tokenizer-derived token boundaries, evidence-based language labels, uncertainty, and any defensible Romanized interpretation or script equivalent with field-level provenance.
- Obtain independent English reference translations from qualified annotators. Record source/reference identifiers and origin; separately record the intended meaning used for semantic review. Do not use machine suggestions as reviewed references.
- Keep new entries as drafts until the actual reviewer has checked source fidelity, normalization, tokenization, labels, optional annotations, references and intended meaning. Record reviewer identifier/pseudonym, date, field review and evidence only after that work occurs.
- Preserve disagreement and uncertainty. A designated adjudicator records evidence, date and outcome; unresolved items remain disputed/abstained and are excluded from evaluation rather than silently majority-voted.
- Assign stable groups for source families, templates, paraphrases, duplicates and repeated ambiguity contexts before deterministic split assignment. Freeze/version the mapping. Run manual near-duplicate and template checks because the readiness checker catches exact normalized-text duplicates and group leakage only.
- Keep every eligible example in the operational denominator. Report failed, missing, unavailable, blocked and blank outputs explicitly; metric populations include only valid successful nonblank outputs, with paired metrics using common IDs.
- Before scoring, run structural validation and whole-dataset readiness on the frozen release, inspect diagnostics and provenance/license records, and confirm all required fields and groups. The checker validates structure and declarations, not truth or rights.

No minimum dataset size is prescribed. A small pilot can expose workflow problems, but any powered study size requires a predeclared outcome, target effect and defensible variance assumptions.

## Prioritized follow-up

- **P0 — correctness:** fixed in this phase: completed-stage/resource/dependency consistency, required taint metadata, in-memory artifact revalidation, unconditional exclusion of ineligible outputs, incompatible provider-forwarding exclusion, and unknown fake-provider scoring/rating gaps.
- **P1 — research prerequisites:** rights-cleared source collection; qualified human annotation, references and adjudication; frozen leak-aware splits; qualified normalizer, transliterator and contextual resource; documented/configured suitable provider; independent semantic ratings.
- **P2 — useful later work:** retain more provider revision/request metadata where available, record run identifiers and repeated-trial plans if needed, add manual near-duplicate review support, and validate a semantic-rating rubric after a pilot. These are not blockers that this phase can solve without legitimate research inputs.

## Files changed in Phase 16

Source and tests: four-condition schema, experiment service, evaluation service and CLI; legacy paired evaluation and report validation; human-rating task workflow; their regression tests. Documentation: `data/schemas/README.md`, `docs/evaluation_protocol.md`, `docs/limitations.md`, `docs/project_status.md`, and this report. No draft/example data, frontend, public API routes, or `.vscode/` files were changed.

## Verification record

Baseline before Phase 16 edits: backend unittest discovery passed (264 tests, exit 0); illustrative draft structural validation passed (exit 0); evaluation readiness returned `NOT READY` with 144 blocking errors and 16 warnings (exit 1, expected); four-condition and legacy CLI `--help` commands passed (exit 0). Initial frontend build attempt exited 1 because the sandbox denied traversal to `C:\Users\ADMIN` while resolving Node (`EPERM`); no frontend source was changed.

Final verification on 2026-10-22: `python -m unittest discover -s backend/tests -v` exited 0 (272 tests); the focused evaluator/rating/four-condition suite exited 0 (56 tests); draft structural validation exited 0 (16 records, 0 errors, 16 warnings); readiness exited 1 (`NOT READY`, 144 blockers, 16 warnings; expected); all seven four-condition/legacy/research/human-rating `--help` commands exited 0; and `git diff --check` exited 0. The four-condition synthetic CLI round-trip is covered by the explicitly labeled synthetic-fixture unittest and exits successfully as a test; it produces no research-eligible report. The frontend build was attempted at baseline and exited 1 from sandbox `EPERM` traversing `C:\Users\ADMIN` to resolve Node. Frontend files were not changed, so no frontend rebuild was needed after implementation.
