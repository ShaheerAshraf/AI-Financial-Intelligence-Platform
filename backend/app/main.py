from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.db.database import engine
from app.api.transactions import router as transactions_router
from app.api.routes.anomalies import router as anomalies_router
from app.api.routes.categories import router as categories_router
from app.api.routes.companies import router as companies_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.invoices import router as invoices_router
from app.api.routes.reviews import router as reviews_router
from app.api.routes.vendors import router as vendors_router
from app.api.routes.workflows import router as workflows_router

app = FastAPI(
    title="AI Financial Intelligence API",
    description="Backend API for the AI Financial Intelligence Platform",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(transactions_router)
app.include_router(companies_router)
app.include_router(vendors_router)
app.include_router(categories_router)
app.include_router(invoices_router)
app.include_router(anomalies_router)
app.include_router(reviews_router)
app.include_router(dashboard_router)
app.include_router(workflows_router)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "financial-intelligence-api",
    }


@app.get("/health/database")
def database_health_check():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))

    return {
        "status": "ok",
        "database": "connected",
    }
