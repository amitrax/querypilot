from urllib.parse import urlparse, parse_qs
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import settings

class Base(DeclarativeBase):
    pass


def normalize_database_url(url: str) -> str:
    """
    Normalizes PostgreSQL / Supabase URLs for SQLAlchemy psycopg2 dialect.
    Converts 'postgres://' or 'postgresql://' to 'postgresql+psycopg2://'.
    """
    if not url:
        return "sqlite:///./querypilot.db"
    
    clean_url = url.strip()
    if clean_url.startswith("postgres://"):
        clean_url = "postgresql+psycopg2://" + clean_url[len("postgres://"):]
    elif clean_url.startswith("postgresql://") and not clean_url.startswith("postgresql+"):
        clean_url = "postgresql+psycopg2://" + clean_url[len("postgresql://"):]
    
    return clean_url


def get_engine_config(url: str | None = None) -> tuple[str, dict, dict]:
    """
    Resolves normalized DB URL, connect_args, and engine_kwargs with
    full support for Supabase PostgreSQL (direct & transaction poolers) and SQLite.
    """
    target_url = normalize_database_url(url or settings.effective_database_url)
    connect_args: dict = {}
    engine_kwargs: dict = {
        "pool_pre_ping": True,
        "echo": False,
    }

    if target_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    else:
        # PostgreSQL / Supabase
        parsed = urlparse(target_url)
        query_params = parse_qs(parsed.query)

        # Enforce SSL for Supabase hosts or when DB_SSL_REQUIRE is enabled
        hostname = (parsed.hostname or "").lower()
        is_supabase = "supabase.co" in hostname or "supabase.com" in hostname
        if (is_supabase or settings.DB_SSL_REQUIRE) and "sslmode" not in query_params:
            connect_args["sslmode"] = "require"

        # Safe connection pooling for cloud PostgreSQL & PgBouncer poolers
        engine_kwargs["pool_recycle"] = settings.DB_POOL_RECYCLE
        engine_kwargs["pool_size"] = settings.DB_POOL_SIZE
        engine_kwargs["max_overflow"] = settings.DB_MAX_OVERFLOW

    return target_url, connect_args, engine_kwargs


db_url, connect_args, engine_kwargs = get_engine_config()
engine = create_engine(
    db_url,
    connect_args=connect_args,
    **engine_kwargs
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI dependency for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
