# AI Financial Intelligence Platform

An open-source financial intelligence system that combines **PostgreSQL**, **ML anomaly detection**, and a **multi-agent Gemini pipeline** with a **human-in-the-loop review dashboard**.

```
                         PostgreSQL
                             │
                    ┌────────┴────────┐
                    │                 │
               Transactions        Invoices
                    │                 │
                    ▼                 ▼
             Anomaly Model      OCR Extraction
                    │                 │
                    ▼                 ▼
             anomaly_results     invoices
                    │                 │
                    ▼                 ▼
                Agent 1           Agent 2
                    │                 │
                    ▼                 ▼
          transaction_analyses invoice_verifications
                    │                 │
                    └────────┬────────┘
                             ▼
                          Agent 3
                             │
                             ▼
                    financial_reviews
                             │
                             ▼
                     React Dashboard
```

## Repository layout

| Path | Description |
|------|-------------|
| [`backend/`](backend/) | FastAPI API, SQLAlchemy models, Gemini agents, Alembic migrations |
| [`frontend/`](frontend/) | React dashboard (Vite + TypeScript) |
| [`ml/`](ml/) | Isolation Forest training pipeline |

## Quick start

### 1. Database

```bash
cp .env.example .env          # root — Postgres + GEMINI_API_KEY
cp backend/.env.example backend/.env
docker compose up -d
cd backend && alembic upgrade head
```

### 2. Seed & ML

```bash
cd backend
python -m app.scripts.seed_data
python -m app.scripts.seed_invoices

cd ..
python ml/train.py
```

### 3. API

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### 4. Dashboard

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173)

## Agent pipelines (CLI)

Run from `backend/`:

```bash
python -m app.scripts.run_transaction_agent --status HIGH --limit 5
python -m app.scripts.run_invoice_extraction --limit 5
python -m app.scripts.run_invoice_agent --limit 5
python -m app.scripts.run_financial_review_agent --limit 5

# LangGraph — full orchestrated pipeline for one transaction
python -m app.scripts.run_financial_workflow --transaction-id 716
```

## Key API endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /api/companies` | List companies (names for UI) |
| `GET /api/vendors?company_id=` | List vendors |
| `GET /api/categories?company_id=` | List categories |
| `POST /api/transactions` | Create transaction (IDs from dropdowns) |
| `POST /api/transactions/import` | CSV import by company/vendor/category **names** |
| `GET /api/transactions/import/template` | Download CSV template |
| `POST /api/invoices` | Attach invoice OCR text + optional extraction |
| `GET /api/dashboard/overview` | Dashboard metrics + charts |
| `GET /api/anomalies` | Paginated anomaly list with filters |
| `GET /api/reviews/{transaction_id}` | Full financial investigation |
| `POST /api/reviews/{transaction_id}/human-decision` | Human approve/reject/escalate |
| `POST /api/workflows/transactions/{transaction_id}/analyze` | LangGraph end-to-end workflow |

## Environment variables

**Root `.env`**

- `POSTGRES_*` — Docker PostgreSQL credentials
- `GEMINI_API_KEY` — Google Gemini API key

**`backend/.env`**

- `DATABASE_URL` — SQLAlchemy connection string

**`frontend/.env`** (optional, production)

- `VITE_API_URL` — API origin when not using Vite dev proxy

> Never commit `.env` files. Only `.env.example` templates are tracked.

## Human-in-the-loop review

The dashboard investigation page lets finance users **Approve**, **Reject**, or **Escalate** after Agent 3 produces an AI recommendation. Decisions are stored on `financial_reviews` (`review_status`, `reviewed_by`, `reviewed_at`, `review_comment`).


