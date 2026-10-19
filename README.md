# BhashaBridge 2.0

An explainable research prototype for Telugu?English code-mixed language understanding, including Telugu written in Latin script. Phase 1 establishes a truthful, testable foundation; it does not yet translate input.

## Motivation
Telugu speakers mix Telugu and English in conversation, and Telugu words may be written in native or Romanized script. Spelling variation, code-switching, context-dependent meanings, and informal grammar make direct translation difficult.

## Research question
Can modular preprocessing and context-aware ambiguity resolution improve semantic preservation and translation quality for Romanized Telugu?English code-mixed sentences compared with direct translation? This is an empirical question, not an assumed result.

## Proposed contribution
A documented integration of conservative normalization, token-level language identification, selective transliteration, ambiguity handling, translation, and an inspectable processing trace, evaluated against baselines. This project does not claim these component tasks are novel.

## Architecture
- `backend/`: FastAPI health/readiness foundation. NLP modules are explicitly marked as not implemented.
- `frontend/`: reserved for the React/Vite interface (scaffold availability noted below).
- `data/samples/`: illustrative examples and schema, not benchmark data.
- `docs/`: problem, research, methodology, architecture, references, and limitations.

## Phase 1 setup
Requires Python 3.10+ (developed with 3.13.1). In PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
uvicorn app.main:app --app-dir backend --reload
```

Check `GET http://127.0.0.1:8000/health` and `/ready`. API docs are at `/docs`. Run tests with `python -m unittest discover -s backend/tests -v`.

Node.js 22.15.0 and npm 10.9.2 were available at scaffold time. The frontend is a minimal Vite/React shell; from `frontend/`, run `npm install` then `npm run dev`. No package install or model download is performed by this repository setup.

## Honest status
Working: health endpoint, readiness reporting, frontend shell, illustrative sample schema. Scaffolded/not implemented: NLP, translation, model adapters, evaluation, and explainability trace. See [limitations](docs/limitations.md).

## Risks and next steps
Model compatibility with mixed Romanized input is unverified. Install and test optional models only after interface and license review. Next: (1) implement conservative preprocessing/tokenization and annotation schema validation; (2) annotate a small development set and evaluate a token-level LID baseline; (3) test selective transliteration and document compatibility before adding translation.
