# BhashaBridge frontend

The React/Vite interface calls the existing `POST /api/v1/analyze` backend route. It displays the API's token language labels and evidence, normalization, transliteration outcomes, ambiguity decisions, module readiness, and opt-in translation status. It does not run evaluation or imply that the illustrative ambiguity rule is validated.

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
