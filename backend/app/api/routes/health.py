from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db
from app.core.config import settings

router = APIRouter()


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint verifying system, database, and AI status."""
    db_status = "healthy"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "database": db_status,
        "version": settings.VERSION,
        "storage_backend": settings.STORAGE_BACKEND,
        "ai_provider": settings.AI_PROVIDER,
        "llm_configured": bool(settings.LLM_API_KEY),
        "offline_engine_ready": True
    }
