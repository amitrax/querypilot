import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from app.core.config import settings
from app.api.routes import api_router, health
from app.db.session import engine, Base
import app.models.models  # ensure models are registered with Base metadata

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("querypilot")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-create tables on startup (especially helpful for sqlite / zero-config dev)
    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("QueryPilot backend started successfully.")
    yield
    logger.info("QueryPilot backend shutting down.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# CORS Middleware
origins = settings.cors_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if "*" not in origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global Exception Handler to avoid leaking internal traces
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled server error on {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. Please try again later."},
    )


# Register API v1 routes
app.include_router(api_router, prefix=settings.API_V1_STR)

# Register health check at root (/health) in addition to /api/v1/health
app.include_router(health.router, include_in_schema=False)


@app.get("/")
def root():
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": f"{settings.API_V1_STR}/docs",
        "health": f"{settings.API_V1_STR}/health",
    }


@app.get("/docs", include_in_schema=False)
def docs_redirect():
    return RedirectResponse(url=f"{settings.API_V1_STR}/docs")


@app.get("/redoc", include_in_schema=False)
def redoc_redirect():
    return RedirectResponse(url=f"{settings.API_V1_STR}/redoc")


@app.get(settings.API_V1_STR, include_in_schema=False)
@app.get(f"{settings.API_V1_STR}/", include_in_schema=False)
def api_v1_root():
    return RedirectResponse(url=f"{settings.API_V1_STR}/docs")

