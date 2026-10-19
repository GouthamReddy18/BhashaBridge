# BhashaBridge 2.0

An explainable research prototype for Telugu-English code-mixed language understanding, including Telugu written in Latin script. The backend implements conservative whitespace normalization, Unicode tokenization, token-level language identification, and an optional selective transliteration stage. It does not translate input.

## Current status
Implemented: `GET /health`, `GET /ready`, and `POST /api/v1/analyze`; original-text preservation; normalization and token offsets; punctuation/number rules; Telugu script detection; small exact-match English and Romanized Telugu lexicons; unknown abstention; opt-in transliteration trace records. The optional IndicLID FastText adapter is disabled unless local model paths and configuration are provided. Transliteration is disabled by default and requires a verified offline engine supplied by the application.

Phase 3 adds a deterministic ambiguity framework after selective transliteration. Its only rule is an illustrative English bank fixture: the exact ENGLISH token bank is resolved only by immediate configured neighbors account/loan or river/shore; missing or conflicting anchors cause abstention. This is not a Telugu lexicon or validated code-mixed-language rule. The additive ambiguities response field includes token index, surface, offsets, candidate provenance, status (resolved or abstained), selected candidate, stable rule ID, and evidence. UNKNOWN remains language-identification uncertainty and does not itself mean ambiguity.

Not implemented: a bundled IndicXlit adapter, POS/NER, general Telugu-English contextual disambiguation, translation, or empirical semantic-preservation evaluation. Transliteration quality has not been experimentally evaluated; the ambiguity fixture is illustrative and awaits evaluation.

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
## Phase 4: annotation data foundation

Phase 4 adds versioned annotation guidance, a JSONL structural schema, 16 synthetic draft examples, and a read-only validator. Draft token labels are baseline suggestions for exercising the format; no record is human reviewed or ground truth. No evaluation split, Telugu-English accuracy, or semantic-preservation result exists. See [data/README.md](data/README.md) and [the annotation guidelines](data/guidelines/annotation_guidelines.md). Add records under `data/drafts/` and validate with `python backend/scripts/validate_dataset.py data/drafts/illustrative_examples.jsonl`. Once human-reviewed reference translations and source provenance exist, this format can support later translation comparisons; it does not implement or evaluate translation.
