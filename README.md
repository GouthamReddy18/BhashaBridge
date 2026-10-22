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
