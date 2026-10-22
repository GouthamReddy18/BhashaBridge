# Project engineering status

**Status checked:** 2026-10-22\
**Checkpoint:** Phase 6D.3, `e59234b` (`feat: add evaluation report integrity validation`)\
**Roadmap note:** No independent master implementation roadmap was found in the repository. The later phase labels in the continuation prompt are proposed engineering stages, not verified original roadmap labels.

## Current readiness

| Requirement | Status | Evidence and remaining work |
|---|---|---|
| Core analysis API | Implemented and verified | FastAPI health, readiness, and analysis endpoints; the 211-test backend suite passes. Rule-based labels and the narrow ambiguity example are not measured linguistic models. |
| Annotation format and structural validation | Implemented and verified | Version 1.0 JSON Schema, annotation guidance, and read-only JSONL validator. Structural validity does not establish linguistic accuracy, permission to use a source, or actual review. |
| Dataset eligibility | Implemented; real reviewed data unavailable | Readiness checks require completed human review, human-contributed field provenance, references, intended meaning, and group-aware split metadata. The 16 illustrative drafts are structurally valid but not eligible. |
| Annotation and review workflow | Offline workflow implemented; human contribution required | `backend/scripts/annotation_workflow.py` scaffolds machine-labeled drafts, validates, checks readiness, records deterministic hash-linked revision manifests, and exports a whole ready dataset without overwriting. Human review/editing remains a manual task, and review claims are not authenticated. |
| Dataset quality safeguards | Partly implemented; real-data validation pending | Structural checks cover duplicate IDs, malformed and duplicate-key JSON, tokenizer spans, field provenance consistency, and value constraints. Readiness detects split-group conflicts and blocks exact normalized-source duplicates within and across splits. Paraphrase, shared-template, source-family, and semantic leakage still need human review and explicit group assignment. |
| English reference translations and intended meanings | Requires human contribution | The schema and readiness checker support them. No eligible reviewed examples are present. Machine suggestions are not references or reviewed meanings. |
| Dataset provenance and licensing | Requires human contribution | Provenance fields and guidance exist, but claims are not independently authenticated and source permissions have not been established for an evaluation corpus. |
| Paired experiment orchestration | Controlled runner implemented; real execution blocked | The dataset runner gates all calls on readiness, requires explicit call opt-in, records versioned ID/split/arm outcomes, and refuses to overwrite. The drafts are ineligible and there is no genuine eligible dataset. |
| Translation provider | Adapter implemented; unavailable until explicitly configured | Google Cloud Translation Basic v2 is behind an enable flag and environment API key, uses a fixed timeout, safe failure categories, and mocked tests. Requested settings and response-confirmed model metadata are recorded and incompatible model records are excluded. The default remains disabled and no credentials are configured. No real call was made. |
| Verified linguistic transformations | Resource workflow implemented; production use blocked | A versioned manifest schema, validator, and deterministic fail-closed matcher exist. Production substitutions are disabled; no reviewed Telugu-English transformation resource is available, and review declarations are not authenticated. |
| BLEU and chrF | Implemented and verified as software; empirical use pending | Phase 6D.2 implements project-versioned corpus metrics and a report CLI. Scores require eligible human-reviewed references and genuine provider outputs. These proxies do not measure semantic preservation by themselves. |
| Evaluation report integrity | Implemented and tested; provenance is not authenticated | Phase 6D.3 checks schema and internal consistency for saved reports. It does not authenticate source artifacts, independently recompute scores, or establish that provider output is genuine. |
| Human semantic-preservation judgments | Workflow implemented; ratings require human contribution | Versioned 0–4 task/rating schema, pending templates, optional blind labels with a separate mapping key, range/provenance validation, and coverage-aware aggregation are implemented. No actual ratings exist and no inter-rater agreement is calculated. |
| Statistical analysis and research conclusions | Deferred until genuine evidence exists | No eligible benchmark, paired real-provider outputs, or human judgments are available. No significance or causal-improvement claim is supported. |
| Frontend | Implemented for supported analysis only | React/Vite frontend is present. It must not imply that unavailable provider, experiment, or research-report capabilities are operational. Frontend build verification remains for integration QA or any frontend change. |

## Baseline verification at this checkpoint

Commands were run from the repository root on 2026-10-22:

| Command | Result |
|---|---|
| `python -m unittest discover -s backend/tests -v` with `PYTHONPATH=backend` and bytecode disabled | Exit 0; 211 tests passed. |
| `python backend/scripts/validate_dataset.py data/drafts/illustrative_examples.jsonl` | Exit 0; 16 records, 0 errors, 16 warnings that records are unreviewed drafts. |
| `python backend/scripts/check_evaluation_readiness.py data/drafts/illustrative_examples.jsonl` | Exit 1; `NOT READY`, 144 blocking errors, 16 draft warnings. This is expected; the draft dataset was not changed. |
| `python backend/scripts/validate_evaluation_report.py --help` | Exit 0. |
| `git diff --check` | Exit 0. |

## Engineering sequence

The following sequence is proposed from the actual repository state and the supplied continuation prompt:

1. **6E.1 Research readiness audit:** recorded here.
2. **6E.2 Annotation workflow:** implemented in the offline CLI; the tool does not assign review metadata.
3. **6E.3 Dataset quality safeguards:** exact duplicate normalized source text is now blocked within and across splits; paraphrase/template leakage still requires human review.
4. **Phase 7 Provider adapter:** Google Cloud Translation Basic v2 adapter implemented with configuration-aware paired calls, bounded timeout, and model confirmation; real calls still require explicit authorization.
5. **Phase 8 Verified linguistic assistance:** implement provenance-aware resource infrastructure; production substitutions stay blocked until reviewed resources exist.
6. **Phase 9 Reproducible experiment artifacts:** runner and versioned artifact output implemented; real run awaits eligible data and explicit external-call authorization.
7. **Phase 10 Human ratings:** pending task and rating workflow implemented; genuine human completion remains required.
8. **Phase 11 Research reporting:** report only validated eligible artifacts and avoid unsupported inference.
9. **Phase 12 Frontend completion:** expose only supported backend capabilities.
10. **Phase 13 Integration QA and Phase 14 delivery docs:** perform after the preceding engineering stages.

## Research status

The project has functioning evaluation software but no genuine eligible benchmark, verified linguistic transformation resource, real provider outputs, or human semantic-preservation judgments. Engineering verification is not empirical validation. Any research conclusion remains pending those inputs and the corresponding human review.

## Phase 6E.2 verification

The annotation workflow's focused suite passed 6 tests, and the full backend suite passed 217 tests (exit 0). Workflow CLI help exited 0. The illustrative dataset still validates structurally (exit 0; 16 draft warnings) and remains `NOT READY` (exit 1; 144 errors and 16 warnings). The added workflow did not change the dataset. `git diff --check` exited 0 before the checkpoint.

## Phase 6E.3 verification

The readiness checker now blocks exact duplicate normalized source text within a split as well as across splits. The readiness and evaluation focused suites passed 54 tests, and the complete backend suite passed 218 tests (exit 0). The illustrative dataset remains structurally valid (exit 0; 16 draft warnings) and `NOT READY` (exit 1; 144 errors and 16 warnings). `git diff --check` exited 0 before the checkpoint. Near-duplicate, template, source-family, and semantic leakage still require human review.

## Phase 7 provider integration

Google Cloud Translation Basic v2 was selected after reviewing its official REST contract, supported-language list, setup, pricing, API-key guidance, and data-usage terms. The adapter and its tests use a fake transport only. No key is configured, no provider request was sent, and real translation remains unavailable pending configuration and the user's explicit approval for external text transmission. The provider's Telugu support does not validate code-mixed Romanized Telugu translation quality. Its timeout and safe failure outcomes were exercised in provider-free tests.

The provider phase passed the full 233-test backend suite (exit 0). Dataset structural validation exited 0 for the 16 unreviewed drafts, readiness exited 1 with the expected 144 errors and 16 warnings, report-validator and annotation-workflow help exited 0, and `git diff --check` exited 0. The provider readiness probe returned `not_configured` and no provider object; no credential names were present in the environment scan, and only the commented `.env.example` template exists. The report validator continues to accept the legacy Phase 6D.3 failure-count shape.

## Phase 8 resource workflow

Added a versioned linguistic-resource schema, strict offline manifest loader/validator, blocked/readiness diagnostics, and deterministic exact-match matcher with applicability/entity-preservation abstention. No reviewed resource was authored or promoted, no production transform is enabled, and reviewer/evidence metadata cannot be independently authenticated. The Phase 8 infrastructure supports real review workflows but does not establish language correctness.

The full backend suite passed 240 tests (exit 0); the seven focused resource tests passed. A UTF-8-with-BOM synthetic pending manifest was rejected as blocked (CLI exit 1), and CLI help exited 0. Draft structural validation exited 0 (16 warnings); draft evaluation readiness exited 1 as expected (144 errors, 16 warnings). `git diff --check` exited 0.

## Phase 9 controlled execution

Added a dataset runner that requires structural and whole-dataset readiness, an explicit provider-call flag, a non-empty selected split, and a new output path. Version 1.0 JSONL rows preserve ID, split, arm identity, requested order, actual invocation order, and typed outcomes. Evaluation now rejects optional artifact split metadata that conflicts with its annotation row. The runner was exercised only with labeled synthetic unit-test data and a fake provider; no call was made to Google or any other external service. Documentation records output compatibility, provider nondeterminism, absence of retries, and the need for incomplete-pair reporting.

## Phase 10 human rating workflow

Implemented a versioned rating record and offline task/aggregation workflow reusing the protocol 0–4 rubric. It supports arm-specific entries, pending state, reviewer provenance, minimum independent-reviewer thresholds, missing output/rating counts, and optional blind A/B stimuli with a separate mapping key. It rejects mock.test outputs, invalid scores, duplicate reviewer judgments, and ratings for missing/failed translations. No human ratings were produced, no IAA is calculated, and the Phase 6D.2 report remains unchanged.

Phase 9 verification passed 245 backend tests (exit 0); structural draft validation exited 0, draft readiness exited 1 as expected, runner `--help` exited 0, and `git diff --check` exited 0. The four runner tests use only explicitly labeled synthetic data and a fake provider, including one failed arm with no retry.

Phase 10 verification passed 251 backend tests (exit 0); focused rating workflow tests passed 6/6. Rating CLI help exited 0 and git diff --check exited 0. Dataset structural validation exited 0; readiness exited 1 as expected for the unchanged 16 drafts. All ratings generated in tests were null templates or explicitly synthetic software fixtures; no human rating data was created.

8. **Phase 11 Research reporting:** denominator-checked assistance categories and validated descriptive report composition are implemented. No eligible artifacts or human ratings exist; no empirical conclusions are supported.

Phase 11 verification passed 258 backend tests (exit 0); evaluation, human-rating, and research-report focused suites passed. Research-report CLI help exited 0, draft structural validation exited 0, draft readiness exited 1 as expected, and git diff --check exited 0. Tests used only synthetic fixtures; no research report or human rating result was produced from project data.
