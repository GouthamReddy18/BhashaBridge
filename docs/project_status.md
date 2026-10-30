# Project engineering status

## Phase 30 — LipiPrism Rebranding & Observatory Architecture (2026-10-30)

Rebranded project presentation and visible interface from BhashaBridge to **LipiPrism** (*One utterance. Multiple linguistic dimensions.*), emphasizing the multi-dimensional examination of code-mixed text across morphological normalization, selective transliteration, and contextual disambiguation.
- Designed original SVG geometric prism brand mark with spectral ray dispersion.
- Rebranded frontend observatory components (`Header`, `Hero`, `Footer`, `LanguageLab`, `MethodologySection`).
- Updated project metadata and documentation while maintaining complete backward compatibility with `BHASHABRIDGE_*` environment variables, `bhashabridge.metrics v1.0.0`, and internal API/schema contracts.

## Phase 29 — Reviewer import CLI and multi-dataset readiness dashboard (2026-10-29)

Phase 29 completed the engineering recovery, audited uncommitted state, verified repository baseline, implemented the CLI entry point for reviewer annotation template generation and CSV import, expanded readiness diagnostics to cover both illustrative and pilot datasets, and verified the React frontend.

**Verification run on 2026-10-29:**
- Full backend test suite: exit 0; **315 tests** passed (313 prior + 2 new CLI import and pilot readiness tests).
- Illustrative draft structural validation: exit 0; 16 records, 0 errors, 16 warnings.
- Pilot draft structural validation (`data/drafts/pilot_examples.jsonl`): exit 0; 28 records, 0 errors, 28 warnings.
- Pilot evaluation readiness: exit 1 (`NOT READY`, 224 blockers, 28 warnings). Expected and correct.
- Report validator `--help`: exit 0.
- Four-condition evaluator `--help`: exit 0.
- Four-condition runner `--help`: exit 0.
- Reviewer annotation import CLI (`backend/scripts/import_annotations.py --help`): exit 0.
- Frontend production build (`npm run build --prefix frontend`): exit 0 (Vite v8.3.5, 0 errors).
- `git diff --check`: exit 0; no whitespace errors.

**Phase 29 deliverables:**
- `backend/scripts/import_annotations.py` — CLI supporting `generate-template` and `import` with merged JSONL output.
- `backend/app/services/project_readiness.py` & `backend/app/api/routes/research.py` — Additive multi-dataset inspection supporting both illustrative (16 records) and pilot (28 records) datasets without leaking filesystem paths.
- `frontend/src.jsx` — Updated interactive workspace with pilot sample utterances and multi-dataset readiness tabs.
- `backend/tests/test_annotation_import.py` & `backend/tests/test_project_readiness_api.py` — Regression tests for CLI and API behavior.

**Research readiness status: BLOCKED.** The pilot dataset remains in draft status pending independent human bilingual review. No fabricated results, credentials, or simulated human ratings were introduced.


Phase 28 implemented the dataset-curation and review workflow that Phase 27 identified as the critical blocker. See the files listed below.

**Verification run on 2026-10-28:**
- Full backend test suite: exit 0; **307 tests** passed (274 prior + 33 new Phase 28 regression tests).
- Illustrative draft structural validation: exit 0; 16 records, 0 errors, 16 warnings. Unchanged.
- Pilot structural validation (`data/drafts/pilot_examples.jsonl`): exit 0; **28 records, 0 errors, 28 draft warnings.** Expected.
- Pilot evaluation readiness: exit 1 (`NOT READY`, 224 blockers, 28 warnings). **Expected and correct.** No fabricated review or references.
- Report validator `--help`: exit 0.
- Four-condition evaluator `--help`: exit 0.
- `git diff --check`: exit 0; no whitespace errors.

**Phase 28 deliverables (all untracked — no commits made):**
- `data/drafts/pilot_examples.jsonl` — 28 researcher-composed draft examples covering 15 distinct code-mixed phenomena.
- `data/guidelines/reviewer_handoff.md` — Reviewer handoff package for an independent bilingual reviewer.
- `data/guidelines/annotation_promotion_checklist.md` — Staged promotion checklist (5 stages, draft → reviewed → split-assigned → eligible).
- `data/pilot_v0.1_manifest.json` — Versioned dataset manifest recording source categories, rights status (pending), limitations, and eligibility (not eligible).
- `backend/tests/test_phase28_dataset_curation.py` — 33 regression tests protecting the curation workflow.

**Research readiness status: BLOCKED.** The pilot is structurally valid but NOT READY. The research-readiness gate is preserved. No fabricated review, reference translation, or experimental output was introduced.

**Remaining blocker requiring a human:** An independent bilingual Telugu–English reviewer must perform Stage 2 of the promotion checklist before any record can become research-eligible.

## Phase 27 research resource audit (2026-10-27)

Phase 27 completed the research resource discovery, qualification, and dataset acquisition planning that was interrupted at the previous session boundary. See [the Phase 27 audit](phase27-resource-audit.md) for the full evidence-backed investigation.

**Verification run on 2026-10-27:**
- Full backend test suite: exit 0; **274 tests** passed.
- Draft structural validation: exit 0; 16 records, 0 errors, 16 unreviewed-draft warnings.
- Draft evaluation readiness: exit 1 (`NOT READY`, 144 blockers, 16 warnings). Expected; the illustrative draft was not modified.
- Report validator `--help`: exit 0.
- Four-condition evaluator `--help`: exit 0.
- `git diff --check`: exit 0; no whitespace errors.

No code was changed, no data was modified, and no external calls were made. The three local commits ahead of `origin/main` (`c0b1e70`, `477d6ef`, `d3a4f3a`) are Phase 26 engineering work; they have not been pushed and no new commits were made.

**Research summary from Phase 27 audit:**
- No confirmed public Telugu–English code-mixed corpus with sentence-level English references and a permissive license was found. ICON 2016 (language-identification corpus) is a plausible candidate but has unresolved licensing and does not include sentence-level English references. UD_Telugu-MTG is a native-script monolingual treebank (CC BY-SA 4.0), not applicable. No verified synthetic Telugu–English corpus with references was found.
- **Recommended acquisition strategy: Hybrid (Strategy C).** Compose 20–30 original code-mixed examples; have an independent bilingual reviewer write reference translations and intended meanings before any condition runs.
- Normalization, transliteration, and contextual disambiguation resources all remain unqualified. IndicXlit is a candidate transliteration resource; qualification requires authorization and human review.
- Google Cloud Translation Basic v2 remains disabled and unconfigured. Enabling it and making API calls requires explicit user/supervisor authorization.
- **Recommended next action:** Compose the original example set and begin the annotation and review workflow.

## Current checkpoint (Phases 16–26 engineering continuation)

The four-condition experiment and evaluator infrastructure is present, but the research is not ready for execution. Phase 17 documents dataset acquisition and review. The current frontend redesign exposes the analysis API and an additive read-only project-readiness API; it reports current blockers and does not run experiments or display fabricated results. The readiness API and UI are integration infrastructure only. No qualified linguistic resource, eligible benchmark, real provider outputs, or human ratings have been produced. See [research readiness](phase16-research-readiness.md), [dataset acquisition/review](dataset-acquisition-and-review.md), and [the report/presentation outline](academic-report-and-presentation-outline.md).

Remaining research gates are external to the software: obtain appropriately licensed source data, conduct documented human review and adjudication, qualify transformation resources, authorize/configure provider transmission, execute the preregistered evaluation, and collect human semantic ratings. Browser-based visual/device QA was unavailable in this environment, so usability still needs direct review.

## Current research-readiness checkpoint (Phase 16)

The four-condition framework is implemented, but a genuine evaluation is **not ready**. No reviewed evaluation dataset, qualified normalization/transliteration/context resource, real provider artifact, or human rating is present. The 16-row illustrative draft remains structurally valid and intentionally ineligible. Phase 16 records the resource inventory and fixes evaluator fixture-taint gaps; no linguistic resource, annotation, rating, or research result was created. See [Phase 16 audit](phase16-research-readiness.md). The prior status below is retained as a historical engineering checkpoint; its statement that the current experiment framework is only two-arm is superseded by Phase 15.

Phase 17 documents acquisition, rights review, annotation/adjudication, leakage controls, exclusions, and a promotion checklist in [the dataset acquisition and review guide](dataset-acquisition-and-review.md). The annotation schema remains at version 1.0; source/reference language scope is specified in release metadata because dedicated language-code fields are absent. No dataset records or review declarations were created.

**Status checked:** 2026-10-22\
**Checkpoint:** Phase 12 implementation commit `29aa426`; integration QA and delivery documentation verified on 2026-10-22.\
**Roadmap note:** No independent master implementation roadmap was found in the repository. The later phase labels in the continuation prompt are proposed engineering stages, not verified original roadmap labels.

## Historical readiness at the Phase 14 checkpoint

| Requirement | Status | Evidence and remaining work |
|---|---|---|
| Core analysis API | Implemented and verified | FastAPI health, readiness, and analysis endpoints; the complete 258-test backend suite passed on 2026-10-22. Rule-based labels and the narrow ambiguity example are not measured linguistic models. |
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
| Frontend | Implemented and build/integration verified | Calls the actual `/api/v1/analyze` workflow; translation stays explicit opt-in and evaluation/experiment controls remain absent. Exact dependencies are locked; local production build and Vite-to-API proxy passed. |

## Historical baseline verification at the Phase 6D.3 checkpoint

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

## Phase 12 frontend completion

The frontend now calls the existing analysis endpoint and shows the real response's original/normalized text, token labels and evidence, transliteration outcomes, ambiguity decisions, module status, and optional translation outcome. There are no experiment, evaluation, or research-results controls. The translation checkbox is unchecked by default and warns that an explicitly requested translation may send text to a configured provider and incur charges. Vite proxies the API route to the local backend; separate-origin deployment requires a configured API base URL and suitable reverse-proxy/CORS setup. Input counting uses Unicode code points, consistent with backend Python string length. Frontend dependencies are pinned and lockfile-backed.

Verification: `npm run build` passed with Node.js 22.15.0 and locked Vite 8.3.5 (exit 0). The first sandboxed build attempt could not traverse the system Node executable path; the same build passed after granting local process read access. No provider call or dataset transmission was made.

## Phase 13 integration QA and Phase 14 delivery record

The full backend suite passed 258 tests (exit 0). Draft structural validation passed with 16 records, 0 errors, and 16 expected unreviewed-draft warnings (exit 0); readiness remained `NOT READY` with 144 blockers and 16 warnings (expected exit 1). Evaluation, report-validator, research-report, and human-rating CLI help commands exited 0. `npm ci --offline` and `npm run build` exited 0. A local Vite-to-FastAPI smoke check returned HTTP 200 for the page and analysis route; the synthetic input returned four labeled tokens and `translation=disabled`. No evaluation artifact, provider request, human rating, or research result was produced. Frontend source checks found no credential patterns; root ignore rules cover `node_modules/` and `dist/`.

The methodology now states that the current runner supports only direct-versus-assisted pairs, while the broader four-variant comparison remains a design/implementation gap. Installation/API setup and workflow documentation are linked from the README, architecture, protocol, dataset, annotation, limitation, and status documents. Scientific validation remains pending genuine eligible examples, verified transformations, real provider output, and human semantic ratings. Browser/device usability review and richer four-variant experiment orchestration remain engineering limitations.
