# AI Financial Intelligence — Frontend

React dashboard for the [AI Financial Intelligence Platform](../README.md). It surfaces ML anomaly detection, multi-agent Gemini analysis, and human-in-the-loop financial review workflows.

## Features

- **Dashboard** — live metrics, anomaly trend, risk distribution, recent high-risk transactions and reviews
- **Transactions** — paginated ledger with links to investigations
- **Anomalies** — filterable Isolation Forest results (status, vendor, category, date)
- **Reviews** — Agent 3 output with human review status
- **Investigation** — full pipeline view (ML → Agent 1 → Agent 2 → Agent 3 → human decision)

## Tech stack

- React 19 + TypeScript
- Vite 8
- React Router 7
- No UI framework — lightweight custom CSS for a public, easy-to-audit codebase

## Prerequisites

- Node.js 20+
- Backend API running (see [backend README](../backend/README.md) or project root README)

## Quick start

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

In development, Vite proxies `/api` and `/health` to `http://127.0.0.1:8000`.

### Start the API (separate terminal)

```bash
cd backend
uvicorn app.main:app --reload
```

## Environment variables

Copy `.env.example` to `.env` when deploying the frontend separately from the API:

```bash
cp .env.example .env
```

| Variable | Description |
|----------|-------------|
| `VITE_API_URL` | API origin for production builds. Leave empty in dev to use the Vite proxy. |

## Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start dev server on port 5173 |
| `npm run build` | Type-check and build for production |
| `npm run preview` | Preview production build locally |
| `npm run lint` | Run Oxlint |

## Project structure

```
frontend/
├── public/              Static assets
├── src/
│   ├── components/      Layout + reusable UI
│   ├── hooks/           Data fetching + API health
│   ├── lib/             API client + formatters
│   ├── pages/           Route-level views
│   └── types/           TypeScript API contracts
├── .env.example
├── index.html
└── vite.config.ts
```

## Demo investigation

After running the backend agent pipelines, open:

```
/investigation/716
```

This page demonstrates the complete intelligence pipeline and human review workflow (Approve / Reject / Escalate).

## Production build

```bash
npm run build
```

Static files are emitted to `dist/`. Serve them with any static host (Nginx, Vercel, Netlify, S3, etc.) and set `VITE_API_URL` to your deployed FastAPI origin.

## License

Same as the parent repository.
