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
| Paired experiment orchestration | Implemented and tested with fixtures; real execution unavailable | Stable direct/assisted arm identity, execution order, and per-arm outcomes are represented. The default assisted path has no verified linguistic replacements. There is no persistence or genuine eligible dataset to execute. |
| Translation provider | Adapter implemented; unavailable until explicitly configured | Google Cloud Translation Basic v2 is behind an enable flag and environment API key, uses a fixed timeout, safe failure categories, and mocked tests. Requested settings and response-confirmed model metadata are recorded and incompatible model records are excluded. The default remains disabled and no credentials are configured. No real call was made. |
| Verified linguistic transformations | Blocked on reviewed resources | Rule tracing and opt-in synthetic fixtures exist. Production substitutions are disabled; no reviewed Telugu-English transformation resource is available. |
| BLEU and chrF | Implemented and verified as software; empirical use pending | Phase 6D.2 implements project-versioned corpus metrics and a report CLI. Scores require eligible human-reviewed references and genuine provider outputs. These proxies do not measure semantic preservation by themselves. |
| Evaluation report integrity | Implemented and tested; provenance is not authenticated | Phase 6D.3 checks schema and internal consistency for saved reports. It does not authenticate source artifacts, independently recompute scores, or establish that provider output is genuine. |
| Human semantic-preservation judgments | Requires human contribution; workflow pending | There are no ratings, rubric data, rating-entry or aggregation workflow, or inter-rater agreement results. BLEU/chrF must not be substituted for human judgments. |
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
6. **Phase 9 Reproducible experiment artifacts:** persist controlled runs only after eligibility and artifact safety requirements are met.
7. **Phase 10 Human ratings:** create an explicit pending-review workflow; never generate ratings.
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
