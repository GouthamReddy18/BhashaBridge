# BhashaBridge 2.0

An explainable research prototype for Telugu-English code-mixed language understanding, including Telugu written in Latin script. The backend implements conservative whitespace normalization, Unicode tokenization, token-level language identification, optional selective transliteration, and an opt-in translation-provider seam. No real translation provider is configured or bundled.

## Current status
Implemented: `GET /health`, `GET /ready`, and `POST /api/v1/analyze`; original-text preservation; normalization and token offsets; punctuation/number rules; Telugu script detection; small exact-match English and Romanized Telugu lexicons; unknown abstention; opt-in transliteration trace records. The optional IndicLID FastText adapter is disabled unless local model paths and configuration are provided. Transliteration is disabled by default and requires a verified offline engine supplied by the application.

Phase 3 adds a deterministic ambiguity framework after selective transliteration. Its only rule is an illustrative English bank fixture: the exact ENGLISH token bank is resolved only by immediate configured neighbors account/loan or river/shore; missing or conflicting anchors cause abstention. This is not a Telugu lexicon or validated code-mixed-language rule. The additive ambiguities response field includes token index, surface, offsets, candidate provenance, status (resolved or abstained), selected candidate, stable rule ID, and evidence. UNKNOWN remains language-identification uncertainty and does not itself mean ambiguity.

Not implemented: a bundled IndicXlit adapter, POS/NER, general Telugu-English contextual disambiguation, a real translation engine, or empirical semantic-preservation evaluation. Transliteration quality has not been experimentally evaluated; the ambiguity fixture is illustrative and awaits evaluation.

## Setup
Requires Python 3.10+. In PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
uvicorn app.main:app --app-dir backend --reload
```

Analyze requests have a fixed maximum length of 2,000 characters. Tests: `$env:PYTHONPATH='backend'; python -m unittest discover -s backend/tests -v`. API docs are at `/docs`.

## Optional IndicLID
No weights or extra dependencies are installed by default. Review [the model compatibility and limits](docs/references.md) before choosing whether to use local IndicLID FastText artifacts. Configuration and response semantics are described in [the architecture](docs/architecture.md).

## Selective transliteration
Set BHASHABRIDGE_TRANSLITERATION_ENABLED=true to opt in. Only tokens already labeled TELUGU_ROMANIZED are eligible. Until a verified offline engine is configured, analysis reports transliteration as unavailable without initializing an engine or attempting a download. Readiness reports this optional status separately from API availability. See the architecture documentation.
## Translation integration

`POST /api/v1/analyze` accepts `{"text":"...","translate":true}`. Translation is opt-in; omitted or false returns `disabled`; requested with no configured provider returns `unavailable`; and provider errors return `failed` with a safe category. The response records the exact original `input_text` only when the provider was invoked. Providers can be injected through FastAPI application state. An optional Google Cloud Translation Basic v2 adapter is available only when `BHASHABRIDGE_GOOGLE_TRANSLATE_ENABLED=true` and an API key is configured; it uses a bounded timeout and only receives text for an explicit translation request. Do not enable it or send research/private text until external transmission is authorized. Billing is usage based, and code-mixed Romanized Telugu quality is not established by the provider's native Telugu language support. The deterministic mock is test-only text, not a translation. No real-provider experiment or translation-quality result has been produced. See [the architecture](docs/architecture.md).

## Phase 4: annotation data foundation

Phase 4 adds versioned annotation guidance, a JSONL structural schema, 16 synthetic draft examples, and a read-only validator. Draft token labels are baseline suggestions for exercising the format; no record is human reviewed or ground truth. No evaluation split, Telugu-English accuracy, or semantic-preservation result exists. See [data/README.md](data/README.md) and [the annotation guidelines](data/guidelines/annotation_guidelines.md). Add records under `data/drafts/` and validate with `python backend/scripts/validate_dataset.py data/drafts/illustrative_examples.jsonl`. Once human-reviewed reference translations and source provenance exist, this format can support later translation comparisons. The current translation seam does not translate linguistically or evaluate quality.

## Phase 6B: controlled dual-arm experiment framework

Phase 6B adds an internal, in-memory experiment service; it does not change or automatically expand `POST /api/v1/analyze`. Arm A sends the exact request string to the provider. Arm B reuses the analysis pipeline, then sends the builder's exact output. The builder starts from whitespace-normalized text and applies only explicitly supplied, provenance-bearing rules. The default rule set is empty, so no verified linguistic substitutions currently occur. Normalization-only and no-op runs are not counted as meaningful assistance. Synthetic test fixtures require explicit opt-in and are not linguistic evidence.

The pair records original/normalized text, exact per-arm provider inputs, translation outcomes, analysis/transformation trace, and requested provider configuration. Legacy injected providers remain text-only. The optional configuration-aware Google adapter receives target/model settings, confirms the returned model when available, and rejects unsupported generation settings; its response does not confirm target language. Calls are bounded by a timeout but remain synchronous and cannot be cancelled. Deterministic fake providers are for tests only. Phase 9 adds a readiness-gated dataset runner and versioned paired JSONL artifacts; no real provider request or empirical quality result exists. Phase 6C execution controls are implemented; Phase 6D.1 defines the protocol and readiness checks, and Phase 6D.2 adds local evaluation infrastructure without establishing research results.

### Phase 6B.1 safeguards

The experiment schemas enforce input/arm alignment and require fallback results to preserve exact original input without applied transformations. Provider-confirmed model metadata is checked against requested model settings when available; target language remains requested metadata. Transformation provenance and entity-review strings are caller declarations, not independent verification. Production linguistic substitutions are disabled because there is no trusted reviewed rule registry. Synthetic rules are accepted only through explicit test-only opt-in and remain labeled synthetic. Phase 6C supports direct_first (default) and assisted_first order and records attempted invocation order. Stateful, nondeterministic, or rate-limited providers may still introduce order effects; counterbalanced order and provider-state controls remain future experimental safeguards. No empirical improvement is established.

Experiment arms distinguish the intended arm input from the actual provider input. If no provider call occurs (for example, no provider is configured or provider identification fails), the actual provider input is null; the exact intended input remains traceable separately.

Synthetic test transformations exercise the edit-and-trace mechanism only. They are not verified linguistic assistance and do not establish research efficacy; meaningful_assistance remains false until an independently reviewed production transformation mechanism exists.


Phase 6C experiment execution supports direct_first (default) and assisted_first order. Arm identity stays fixed; invocation_order records only provider calls actually entered, including calls that fail, while provider-unavailable or provider-identification failures produce no attempted invocation. This makes execution reproducible as configured, but cannot make a nondeterministic provider deterministic or eliminate state, rate-limit, transient-failure, and ordering effects. No real provider or empirical quality improvement is established.

### Phase 6D.1: evaluation protocol and dataset readiness

Phase 6D.1 documents the evaluation protocol and adds a read-only evaluation-readiness checker. Phase 6D.2 adds a callable scoring service and explicit-artifact CLI with project-versioned corpus BLEU/chrF reporting. The annotation schema accepts optional `intended_meaning`, `split`, and `split_group` fields; existing drafts remain valid. Run `python backend/scripts/check_evaluation_readiness.py data/drafts/illustrative_examples.jsonl` to see why the 16 unreviewed drafts are not benchmark-ready. Scoring infrastructure is not a research result: no reviewed benchmark, genuine human ratings, or real-provider outputs are available. Human annotation and review, references, licensing checks, and leakage-aware group assignments remain prerequisites. See [the evaluation protocol](docs/evaluation_protocol.md).

Phase 6D.3 adds a read-only validator for saved Phase 6D.2 JSON reports: `python backend/scripts/validate_evaluation_report.py path/to/report.json`. Exit codes are 0 for a structurally valid and internally consistent report, 1 for an invalid report, and 2 for unsupported schema/metric versions or input errors. A `VALID` report establishes consistency under the supported contract only; it does not authenticate provenance, verify source translations or metric calculations independently, or demonstrate semantic improvement. Synthetic fixtures remain software tests, not research evidence.

See [project engineering status](docs/project_status.md) for the current readiness audit, baseline verification, and proposed continuation stages. Engineering verification does not establish empirical research results.

The offline annotation workflow supports draft scaffolding, structural validation, readiness checks, hash-linked revision manifests, and safe export of complete eligible datasets: `python backend/scripts/annotation_workflow.py --help`. It never assigns review status or overwrites an existing output. See [annotation workflow guidance](data/guidelines/annotation_guidelines.md#offline-annotation-workflow).

Phase 8 adds a versioned linguistic-resource manifest contract and an offline validator: `python backend/scripts/validate_linguistic_resource.py <manifest.json>`. It records rule provenance, language coverage, applicability, evidence references, human review declarations, and entity-preservation status; its deterministic matcher abstains unless the exact source and language match and the caller confirms applicability/entity preservation. The declarations are not authenticated, no reviewed production resource is bundled, and the matcher is not enabled in experiment execution. Production transformations remain blocked.

Run `python backend/scripts/run_dataset_experiment.py --help` for the controlled Phase 9 runner. It checks dataset readiness before calling the configured Google provider, requires `--allow-provider-calls`, records per-example split/arm/invocation metadata, and writes a new artifact without replacing existing files. The illustrative drafts are ineligible, so no runner call was made against project data. Artifacts produced with synthetic test providers are test fixtures, not research evidence.

Phase 10 provides a manual semantic-rating task workflow. The human_rating_workflow.py create-tasks command creates source/intended-meaning/output stimuli and blank pending ratings, optionally blinded with a separate arm-mapping key; the aggregate command validates and summarizes completed 0–4 human judgments with rating distributions, coverage, and missingness. It creates no ratings. Keep the mapping file private to the coordinator. No ratings have been entered, and inter-rater agreement is not calculated.

Phase 11 adds assistance-category accounting to evaluation reports and a validated descriptive report composer: python backend/scripts/build_research_report.py --help. It accepts a validated eligible evaluation report and optionally a matching human-rating summary. It reports descriptive results and limitations without significance testing or causal conclusions. The illustrative drafts remain ineligible, so no research report has been generated.

### Phase 15: four-condition controlled experiment

Phase 15 adds a separate `four_condition.v1` cumulative experiment contract: exact-source `direct_v1`, reviewed linguistic normalization, normalization plus selective transliteration, and those stages plus a reviewed contextual transformation. Missing resources block that condition and its dependents. There are no reviewed production resources or eligible benchmark examples at present. Use `backend/scripts/run_four_condition_experiment.py`, `evaluate_four_condition_experiment.py`, and `validate_four_condition_report.py` for the explicit local workflow. External translation requires `--allow-provider-calls`; outputs and reports are never overwritten. Test fixtures are labeled and excluded from metric scoring. Per-condition available outputs and matched-ID contrasts have separate denominators. This framework produces no human ratings, significance tests, causal claims, or empirical findings. See [the approved Phase 15 design](docs/phase15-design-pending-approval.md).

The React/Vite frontend calls `POST /api/v1/analyze` and the read-only `GET /api/v1/research/readiness` endpoint. It displays token labels/evidence, normalization, transliteration status, ambiguity decisions, module status, provider configuration, four-condition blockers, and the outcome of an explicitly requested translation. Run the backend as above, then follow [frontend setup](frontend/README.md). Translation is unchecked by default; when enabled and a provider is configured, the API may send the sentence externally. Experiments, evaluation, and human ratings remain offline workflows; the frontend has no experiment controls or research score catalog.

## Pilot dataset and reviewer annotation workflow (Phases 28–29)

Phase 28 introduces a 28-example researcher-composed pilot draft corpus (`data/drafts/pilot_examples.jsonl`) covering 15 distinct Telugu–English code-mixed phenomena (e.g. basic code-mixing, borrowed technical terms, adverbialized adjectives, informal spellings, and negation). The dataset is registered in `data/pilot_v0.1_manifest.json`.

An independent bilingual reviewer workflow is defined in `data/guidelines/reviewer_handoff.md` and governed by the 5-stage checklist in `data/guidelines/annotation_promotion_checklist.md`.

Phase 29 adds the offline CLI `backend/scripts/import_annotations.py`:
- **Generate reviewer template**:
  ```powershell
  python backend/scripts/import_annotations.py generate-template --pilot data/drafts/pilot_examples.jsonl --output data/guidelines/reviewer_annotation_template.csv
  ```
- **Validate & merge reviewer annotations**:
  ```powershell
  python backend/scripts/import_annotations.py import --pilot data/drafts/pilot_examples.jsonl --csv completed_reviewer_annotations.csv --output-jsonl data/drafts/pilot_merged_draft.jsonl
  ```

Imported records preserve `draft` status until explicitly promoted after independent bilingual review.

## Optional IndicXlit transliteration adapter

`backend/app/services/indicxlit_adapter.py` provides an optional, lazy-loaded compatibility wrapper adhering to the project's transliteration contract (`engine_id` and `transliterate()`).
- Disabled by default (`BHASHABRIDGE_TRANSLITERATION_ENABLED=false`).
- Performs no network downloads or background initialization.
- Validates that outputs contain only valid Telugu script Unicode code points.
- Contains all inference exceptions safely.
- Real model weights and heavy dependencies require explicit separate installation and authorization. See [docs/optional_indicxlit_integration.md](docs/optional_indicxlit_integration.md).

## Classroom demonstration procedure

To demonstrate BhashaBridge safely in a classroom or review setting without incurrence of provider fees or fabrication of unverified research claims:

### 1. Verification of the backend test suite
Confirm software stability and integrity:
```powershell
$env:PYTHONPATH = "backend"
python -m unittest discover -s backend/tests -v
```
*Expected result:* 315 passing tests across all modules.

### 2. Dataset validation and readiness gates
Demonstrate research rigor by showing that draft datasets pass structure checks but fail evaluation readiness until reviewed:
```powershell
# Structural checks pass (format is valid):
python backend/scripts/validate_dataset.py data/drafts/pilot_examples.jsonl

# Readiness gate blocks benchmark execution (exit code 1, 224 blocking errors):
python backend/scripts/check_evaluation_readiness.py data/drafts/pilot_examples.jsonl
```

### 3. Reviewer annotation import CLI
Demonstrate the reviewer handoff and strict rejection of corrupted submissions:
```powershell
# Inspect import CLI help:
python backend/scripts/import_annotations.py --help
```

### 4. Interactive web application
Launch the local backend and frontend:
- **Terminal 1 (Backend):**
  ```powershell
  uvicorn app.main:app --app-dir backend --reload --port 8000
  ```
- **Terminal 2 (Frontend):**
  ```powershell
  npm run dev --prefix frontend
  ```
- **Explore in browser:**
  - Try example code-mixed sentences such as `nenu office ki veltunna` or `project deadline extend cheyyadam possible aa?`.
  - Inspect the token-level language identification, rule evidence, and character offsets.
  - View the **Readiness Dashboard** to inspect the 28-record pilot dataset and 16-record illustrative dataset blockers.
  - Notice that external translation remains disabled and unconfigured by default, preventing unintended API calls or charges.

## Current research status

The illustrative and pilot drafts are structurally valid but ineligible for genuine evaluation. No reviewed benchmark, qualified linguistic transformation resource, real-provider experiment output, or human semantic rating is available. The readiness endpoint reports these current blockers; it does not create evidence. See [the Phase 16 readiness audit](docs/phase16-research-readiness.md), [dataset review workflow](docs/dataset-acquisition-and-review.md), and [project status](docs/project_status.md). Project engineering work is complete through the interactive readiness dashboard, while research validation remains blocked on genuine reviewed inputs and outputs.
