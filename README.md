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

`POST /api/v1/analyze` accepts `{"text":"...","translate":true}`. Translation is opt-in; omitted or false returns `disabled`; requested with no injected provider returns `unavailable`; and a configured provider with ID-identification, execution, or output failures returns `failed` with a safe error code. The response records the exact original `input_text` only when a provider was invoked. Providers can be injected through FastAPI application state; the default app has none. The deterministic mock is test-only text, not a translation. No real provider or translation-quality evaluation is included. The provider call is synchronous with no explicit timeout or cancellation boundary; before adding a slow network provider, define bounded execution, cleanup, and safe timeout-error mapping. See [the architecture](docs/architecture.md).

## Phase 4: annotation data foundation

Phase 4 adds versioned annotation guidance, a JSONL structural schema, 16 synthetic draft examples, and a read-only validator. Draft token labels are baseline suggestions for exercising the format; no record is human reviewed or ground truth. No evaluation split, Telugu-English accuracy, or semantic-preservation result exists. See [data/README.md](data/README.md) and [the annotation guidelines](data/guidelines/annotation_guidelines.md). Add records under `data/drafts/` and validate with `python backend/scripts/validate_dataset.py data/drafts/illustrative_examples.jsonl`. Once human-reviewed reference translations and source provenance exist, this format can support later translation comparisons. The current translation seam does not translate linguistically or evaluate quality.

## Phase 6B: controlled dual-arm experiment framework

Phase 6B adds an internal, in-memory experiment service; it does not change or automatically expand `POST /api/v1/analyze`. Arm A sends the exact request string to the provider. Arm B reuses the analysis pipeline, then sends the builder's exact output. The builder starts from whitespace-normalized text and applies only explicitly supplied, provenance-bearing rules. The default rule set is empty, so no verified linguistic substitutions currently occur. Normalization-only and no-op runs are not counted as meaningful assistance. Synthetic test fixtures require explicit opt-in and are not linguistic evidence.

The pair records original/normalized text, exact per-arm provider inputs, translation outcomes, analysis/transformation trace, and requested target language (`en`). The current text-only provider protocol cannot accept target-language/model/generation settings; they are recorded as requested configuration and are not represented as provider-confirmed. Deterministic fake providers are for tests only. No real translation provider, evaluation score, persistence, or quality result exists. Provider calls remain synchronous without an explicit timeout/cancellation boundary. Phase 6C is intended for experiment persistence/design; Phase 6D for controlled evaluation, neither is implemented.

### Phase 6B.1 safeguards

The experiment schemas enforce input/arm alignment and require fallback results to preserve exact original input without applied transformations. The current text-only provider cannot confirm a target language or model configuration; requested settings remain requests only. Transformation provenance and entity-review strings are caller declarations, not independent verification. Production linguistic substitutions are disabled because there is no trusted reviewed rule registry. Synthetic rules are accepted only through explicit test-only opt-in and remain labeled synthetic. Phase 6C supports direct_first (default) and assisted_first order and records attempted invocation order. Stateful, nondeterministic, or rate-limited providers may still introduce order effects; counterbalanced order and provider-state controls remain future experimental safeguards. No empirical improvement is established.

Experiment arms distinguish the intended arm input from the actual provider input. If no provider call occurs (for example, no provider is configured or provider identification fails), the actual provider input is null; the exact intended input remains traceable separately.

Synthetic test transformations exercise the edit-and-trace mechanism only. They are not verified linguistic assistance and do not establish research efficacy; meaningful_assistance remains false until an independently reviewed production transformation mechanism exists.


Phase 6C experiment execution supports direct_first (default) and assisted_first order. Arm identity stays fixed; invocation_order records only provider calls actually entered, including calls that fail, while provider-unavailable or provider-identification failures produce no attempted invocation. This makes execution reproducible as configured, but cannot make a nondeterministic provider deterministic or eliminate state, rate-limit, transient-failure, and ordering effects. No real provider or empirical quality improvement is established.
