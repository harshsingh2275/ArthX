from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from database import engine, Base
import models  # registers all ORM models with Base.metadata

# Create tables on startup if they don't exist yet
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ArthX Financial Intelligence Platform API",
    description="Explainable AI cash flow forecasting and fraud anomaly detection",
    version="0.1.0"
)

# CORS configured from settings (.env)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register route modules
from routes.data import router as data_router
from routes.transactions import router as transactions_router
from routes.invoices import router as invoices_router
from routes.analysis import router as analysis_router

app.include_router(data_router)
app.include_router(transactions_router)
app.include_router(invoices_router)
app.include_router(analysis_router)

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "ArthX Backend",
        "version": "0.1.0",
        "environment": settings.ENVIRONMENT,
        "database_configured": bool(settings.DATABASE_URL),
        "gemini_api_key_configured": settings.has_gemini_key,
        "explainability_mode": settings.EXPLAINABILITY_MODE,
        "allowed_cors_origins": settings.cors_origins_list,
    }

@app.get("/")
def root():
    return {
        "message": "Welcome to ArthX API",
        "health": "/api/health",
        "docs": "/docs",
        "environment": settings.ENVIRONMENT,
    }
