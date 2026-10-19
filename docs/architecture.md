# Architecture (planned)

The target is a React/Vite client and modular FastAPI service. The pipeline will preserve original input and record observable transformations. Proposed stages: validation, tokenization, conservative normalization, token-level language identification, selective transliteration, supported linguistic analysis, ambiguity handling, translation, uncertainty, and trace generation.

Phase 1 implements only `/health` and `/ready`. Readiness lists each module with `configured`, `available`, or `not_implemented` status; a running API is not evidence that NLP models are ready. No analysis or translation endpoint is exposed yet.
