# BhashaBridge 2.0 — The Language Observatory Frontend

A presentation-quality computational linguistics research interface and interactive language observatory for Telugu–English code-mixed natural language processing. Built with React 19 and Vite 8.

The interface connects directly to the FastAPI backend:
- `POST /api/v1/analyze`: Real-time token analysis, Unicode offsets, conservative language identification, transliteration suggestions, and contextual ambiguity inspection.
- `GET /api/v1/research/readiness`: Real-time telemetry monitoring dataset evaluation readiness, four-condition experiment gates, and transformation resource inventory.

## Design Concept & Architecture

**The Language Observatory** conceptualizes code-mixed NLP as a bridge between multiple linguistic representations: Romanized Telugu, native Telugu script, syntax, and English semantic meaning.

### Visual Foundations
- **Color Palette:** Deep charcoal/forest surfaces (`#0D1312`, `#182321`), warm ivory text (`#E8E9DB`), electric lime highlights (`#D5F36A`), restrained coral alerts (`#FF7856`), and accent teal (`#82C9C0`).
- **Typography:** Modern editorial display with bilingual Telugu script support (`Plus Jakarta Sans`, `Space Grotesk`, `Noto Sans Telugu`, `JetBrains Mono`).
- **Telemetry Aesthetics:** Mathematical coordinate grids, crosshairs, stream telemetry indicators, and glowing status pills.

### Component Structure
```text
frontend/
├── index.html                  # HTML entry point with Google Fonts preconnect
├── vite.config.js              # Vite configuration with /api backend proxy
├── package.json                # Locked dependencies (React 19, Vite 8)
├── src.jsx                     # Root React application mount
├── style.css                   # Comprehensive observatory stylesheet
└── src/
    ├── api.js                  # Typed API fetch client with timeout & error handling
    ├── constants.js            # Exemplar phenomena, pipeline stages, condition metadata
    ├── App.jsx                 # Top-level orchestrator & global toast notifications
    └── components/
        ├── Header.jsx          # Sticky observatory navigation with live pulse telemetry
        ├── Hero.jsx            # Bilingual headline & interactive word-stream morpher
        ├── LanguageLab.jsx     # Utterance console, token stream journey & inspector
        ├── PipelineExplorer.jsx# 8-stage interactive laboratory pipeline blueprint
        ├── ResearchObservatory.jsx # Live readiness monitor (pilot vs illustrative toggle)
        ├── MethodologySection.jsx  # Research question, BLEU/chrF caveats & limits
        ├── Footer.jsx          # Observatory telemetry, coords, and repository links
        └── ui/
            └── Badge.jsx       # Reusable status badges, script pills & coordinate chips
```

### Component Inspiration & Attribution
- Interactive retro grid, word morphing streams, and glowing border primitives adapted from [React Bits](https://github.com/DavidHDev/react-bits) (MIT License) and [Magic UI](https://github.com/magicuidesign/magicui) (MIT License).
- Bento grid modular card layouts and badge primitives adapted from [shadcn/ui](https://github.com/shadcn-ui/ui) (MIT License).

## Running Locally

Requires Node.js `^20.19.0` or `>=22.12.0`.

1. Start the FastAPI backend from the repository root:
   ```powershell
   $env:PYTHONPATH='backend'
   uvicorn app.main:app --app-dir backend --reload --port 8000
   ```

2. Start the Vite development server in the `frontend` folder:
   ```powershell
   cd frontend
   npm ci
   npm run dev
   ```

3. Build for production:
   ```powershell
   npm run build
   ```

## Scientific Integrity Safeguards
- **Honest Gates:** The Research Observatory never fabricates BLEU-4 or chrF scores; evaluation status is visibly displayed as `RESEARCH EVALUATION IS STRICTLY BLOCKED` until verified human references are supplied.
- **Local Isolation:** Machine translation requests are disabled by default. Sentences stay inside the local API boundary unless the user explicitly checks the translation opt-in box.
