# Architecture

The FastAPI backend exposes `GET /health`, `GET /ready`, and `POST /api/v1/analyze`. The analyze request accepts optional `translate: true`; omission or `false` preserves the analysis-only path. The pipeline runs request validation, whitespace normalization, tokenization, token-level language identification, selective transliteration, then ambiguity detection and contextual resolution. It preserves the original request; token offsets are start-inclusive/end-exclusive Python Unicode code-point positions in normalized text.

When configured, a selective transliteration stage follows language identification. It accepts only tokens whose existing label is `TELUGU_ROMANIZED`; every other label is skipped. Each token gets a trace record with original surface, index, offsets, language label, attempted flag, candidate (only when a valid result was returned), engine ID, status, and reason. Transliteration never replaces the original token or normalized input.

## Language identification

The baseline consumes tokenizer tokens independently and preserves index, surface text, and offsets. It applies deterministic punctuation and Unicode-number rules; detects Telugu-block letters/marks as `TELUGU_SCRIPT` (script evidence only); and uses small documented exact-match Romanized Telugu and English seed lexicons. Unsupported Latin words and abbreviations are `UNKNOWN`. It never uses sentence position to assign labels. It does not emit confidence for rules.

The optional IndicLID FastText adapter is disabled by default and only loads local artifacts explicitly configured through `BHASHABRIDGE_LID_PROVIDER=indic_lid`, `BHASHABRIDGE_INDICLID_FTN_PATH`, and `BHASHABRIDGE_INDICLID_FTR_PATH`. It does not download models. When selected, it submits each token separately to the respective native or roman FastText model, maps the resulting class and score, and abstains below 0.6. The model's returned FastText score is included only for model predictions; it is not a calibrated probability. Per-token application is an unvalidated adaptation of a sentence-level classifier.

Readiness distinguishes the implemented baseline from the optional model (`not_configured`, `configured`, `not_installed`, `available`, or `unavailable`). Overall readiness remains degraded because other pipeline stages are not implemented.

## Analyze API

Request JSON: `{"text":"nenu college ki vellanu"}`. Response retains `original_text`, `normalized_text`, `tokens`, and `modules`. Each token retains its previous fields and adds `language` with `label`, `method`, and `evidence`; `confidence` appears only for optional model output. See the endpoint OpenAPI schema for the complete response.

The response also includes transliterations, aligned one-to-one with tokens. Status values are skipped, disabled, succeeded, failed, and unavailable. The environment setting BHASHABRIDGE_TRANSLITERATION_ENABLED defaults to false. If enabled without an explicitly supplied verified offline engine, the module and eligible records report unavailable. Readiness reports configuration without constructing an engine or checking assets; this optional status does not determine API availability. Engine exceptions and invalid/empty candidates report failed without a candidate. Candidates are accepted only when every character is a Telugu-block letter or combining mark and at least one character is a letter. The project does not construct IndicXlit because its safe local-only initialization has not been verified in this environment.

## Translation integration

Translation is an optional final operation in the analyze pipeline and is implemented behind a provider protocol in `backend/app/services/translation.py`. The provider receives a `TranslationInput` containing the exact original request text, not normalized or ambiguity-adjusted text. The response records `input_text` only when a provider was invoked, along with its stable `provider_id` and returned text on success. This keeps the translation seam independent of upstream analysis so later experiments can compare direct and assisted inputs with the same provider.

`translation` response outcomes are: `disabled` when not requested; `unavailable` only when requested without an injected provider; `success` only for a nonblank typed provider result with a nonblank provider ID; and `failed` for provider-ID access/validation failures, provider exceptions, or invalid output. A provider-identification failure has a null `provider_id` and `provider_metadata_error`; other failures preserve a valid provider ID. Failure responses expose a safe `error_code`, not exception text or traces. Providers are injected through FastAPI application state/dependency overrides; the default application has no provider and no translation credential or model setting. `MockTranslationProvider` emits an explicit test-only marker and is never configured by default; it is not a linguistic translation. No real translation provider has been integrated, and no translation-quality or semantic-preservation result has been measured. Provider invocation is synchronous and has no explicit timeout or cancellation boundary. This is not an active external-provider failure because the default app has no external provider. Before adding a potentially slow network provider, define bounded execution time, timeout behavior, cancellation and resource cleanup, and safe mapping of timeout errors to the public failure contract.


The lexicons are deliberately small and hand-maintained; they are not a vocabulary or measured classifier. Telugu script may contain loanwords, transliterations, names, or other content. Romanized spellings are highly variable; outside the seed list, tokens remain unknown. Transliteration has not been experimentally evaluated. General Telugu-English contextual disambiguation, morphology, POS/NER, real translation, and meaning are not implemented; the limited illustrative fixture is described below.


## Phase 3: ambiguity and explainability

The additive ambiguities response field is an empty list when no configured candidate matches. The service runs after transliteration and preserves token labels, text, order, indices, offsets, and transliteration records. UNKNOWN means the language baseline could not classify a token; it is not an ambiguity record. A matched candidate record has status resolved when the exact rule selects a candidate, or abstained when anchors are missing or conflict. Abstention has a null selected_candidate.

Each record contains token_index, surface, normalized-text start/end, candidates with source provenance, status, selected_candidate, rule_id, and evidence. No confidence score is claimed. The sole centralized rule, fixture.english_bank_immediate_context.v1, applies only to the exact ENGLISH token bank. Its exact immediate configured account or loan anchor supports an illustrative financial sense; river or shore supports an illustrative river-edge sense. These fixture anchors are matched by exact case-folded configured surface strings, regardless of their LID labels; an anchor label is not independent linguistic verification (for example, river may remain UNKNOWN and still match). These are illustrative English fixture meanings and anchors, not a validated Telugu lexicon or Telugu-English contextual disambiguation. Failed/unavailable transliteration records never serve as semantic evidence; this fixture does not depend on transliteration.

Run tests from backend with python -m unittest discover -s tests -v. Only this deterministic fixture and the response contract are implemented and tested. General Telugu-English contextual disambiguation, a verified offline transliteration engine, a real translation provider, and empirical semantic-preservation evaluation are unsupported; fixture behavior awaits evaluation.

## Phase 4: dataset and annotation validation

Dataset authoring is separate from inference. Annotation records use `data/schema/annotation.schema.json` version 1.0 and JSONL, with original/normalized text, provenance, token labels and Python code-point offsets, optional nullable linguistic fields, and optional review metadata. The read-only `backend.app.services.dataset_validation` validator reuses project normalization/tokenization and validates JSONL lines, IDs, labels, spans, provenance/status consistency, ambiguity selection invariants, and optional translation/review types. Run `python backend/scripts/validate_dataset.py data/drafts/illustrative_examples.jsonl`. A successful structural check does not certify linguistic annotations or human review. The 16 records are synthetic machine-generated drafts; no reviewed benchmark or evaluation split exists. Future split policy is documented in `data/splits/README.md`.

## Phase 6D.1: evaluation protocol and readiness

See [the evaluation protocol](evaluation_protocol.md) for the paired study design, planned metrics, human semantic rubric, missingness reporting, and leakage policy. The optional read-only `backend/scripts/check_evaluation_readiness.py` reuses structural dataset validation and checks reviewed human-contributed references and intended meanings plus split/group metadata. Annotation version 1.0 accepts these additions optionally, so existing drafts remain structurally valid. The 16 drafts are not evaluation-ready. This phase does not score translations, add a provider, or claim research results; Phase 6D.2 remains future implementation and evaluation work.

## Phase 6B: assisted input and paired arms

The internal `app.services.experiment.run_paired_experiment` service runs two calls through the same injected text-only provider. Direct receives the exact original request, preserving whitespace and Unicode. Assisted reuses `analyze`, then calls the pure `build_assisted_input` service. It begins with the existing normalized text and applies only explicitly injected, versioned rules with provenance, evidence, source-token checks, and a non-entity confirmation. The production default supplies no rules. Transliteration candidates and ambiguity candidate IDs are trace-only and never become replacement strings. The illustrative English `bank` fixture is not a Telugu-English resource.

The typed in-memory pair records both exact provider inputs, outcomes, original/normalized input, analysis, applied and skipped transformations, and whether assistance was meaningful, normalization-only, identical, or fell back. Invalid spans/rules trigger all-or-nothing fallback to exact original input. Synthetic fixtures require explicit opt-in for tests. Requested target language defaults to English (`en`), but current provider protocol accepts only text: requested generation settings are not forwarded, and provider-confirmed model/target metadata remain null. This service is internal; `/api/v1/analyze` remains unchanged and does not invoke paired arms. Calls are synchronous with no timeout/cancellation boundary. Phase 6D.1 adds protocol and readiness tooling; controlled evaluation and results remain future Phase 6D.2 work.

### Phase 6B.1 contract and authorization

Pydantic result models enforce fallback, transformation, normalization-only, identity, and paired-arm consistency. Experiment arms cannot use the disabled outcome; unavailable and failed outcomes remain valid. Direct/assisted inputs and the analysis normalization must agree with the paired result. The text-only provider may confirm its ID only; target-language, model, and generation settings remain requested metadata and are not forwarded or provider-confirmed.

Caller-provided provenance/evidence strings and non-entity assertions are descriptive declarations, not proof. evidence_status="verified" is not sufficient authorization: production substitutions are always skipped until a future trusted, independently reviewed rule registry exists. Synthetic transformations can run only with the explicit test-fixture opt-in and are emitted as synthetic_fixture. This is not verified Telugu linguistic knowledge. A future trusted resource must also provide a real entity-review process; the current system has no NER.

Phase 6C supports direct_first (default) and assisted_first order and records attempted invocation order. No order randomization or provider-state control is implemented. Stateful, nondeterministic, or rate-limited providers may create order effects; additional experimental controls remain necessary before real paired results are interpreted.

Each arm stores intended_input separately from provider_input. provider_input is copied only from the existing TranslationResult.input_text and remains null when no invocation occurred. The arm schema rejects a mismatch between those values and the actual translation trace.

Synthetic edits remain visible in transformation records for mechanism tests, but they never set meaningful_assistance. That flag remains false until an independently reviewed production transformation mechanism exists; no such mechanism is currently configured.


### Phase 6C: execution order and attempt trace

ExperimentConfiguration.execution_order accepts direct_first (the backward-compatible default) or assisted_first. Arm identity is independent of order: the direct result always corresponds to exact original input and assisted to builder output. PairedExperimentResult.invocation_order records the arms in the order their provider translate() call was entered. Provider-ID failures and unconfigured providers have no input_text, so they are not recorded as invocations; provider-call failures retain the exact input and count as attempted. Each arm is still attempted independently.

The configured order is deterministic and recorded, but it does not make provider behavior deterministic or remove order effects from shared state, rate limits, transient failures, or provider-side behavior. The text-only provider remains synchronous, with no timeout/cancellation boundary.
