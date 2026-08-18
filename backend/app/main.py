from fastapi import FastAPI
from sqlalchemy import text

from app.db.database import engine


app = FastAPI(
    title="AI Financial Intelligence API",
    description="Backend API for the AI Financial Intelligence Platform",
    version="0.1.0",
)


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