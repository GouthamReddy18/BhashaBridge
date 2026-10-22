# BhashaBridge frontend

The React/Vite research interface calls `POST /api/v1/analyze` for interactive token analysis and `GET /api/v1/research/readiness` for the current local readiness summary. It displays token labels and evidence, normalization, transliteration outcomes, ambiguity decisions, module readiness, opt-in translation status, dataset eligibility, provider configuration, and the four-condition blockers. The report section is an honest empty state because there is no persistent report catalog. The app does not run experiments, generate research scores, or imply that illustrative rules or examples are validated.

## Run locally

Use Node.js `^20.19.0` or `>=22.12.0`. Install the locked frontend dependencies with `npm ci`, then start the backend from the repository root:

```powershell
$env:PYTHONPATH='backend'
uvicorn app.main:app --app-dir backend --reload
```

In a second terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Vite proxies `/api` to `http://127.0.0.1:8000` during development. For a deployment with a separately hosted API, set `VITE_API_BASE_URL` to its base URL and configure that API's deployment/reverse proxy to permit the frontend origin. The backend does not enable cross-origin browser access by default.

The translation checkbox is off by default. When selected, an explicitly configured backend provider may receive the sentence and may incur charges. Without a provider, the API returns `unavailable` without sending the sentence externally. No credentials belong in frontend code or environment variables exposed to Vite.

The example inputs are explicitly illustrative. Readiness information is fetched once when the page loads; if the endpoint is unavailable, the UI reports that state and keeps analysis usable. Evaluation and human-rating workflows remain offline CLIs. See [the project architecture](../docs/architecture.md), [evaluation protocol](../docs/evaluation_protocol.md), and [dataset acquisition and review guide](../docs/dataset-acquisition-and-review.md).
