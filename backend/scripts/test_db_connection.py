import os
import sys
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

# Ensure backend directory is in sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.config import settings
from app.db.session import get_engine_config


def mask_url(raw_url: str) -> str:
    """Safely masks credentials in any database URL using SQLAlchemy make_url."""
    try:
        url_obj = make_url(raw_url)
        return url_obj.render_as_string(hide_password=True)
    except Exception:
        return "[INVALID OR UNPARSEABLE URL]"


def run_test():
    raw_effective_url = settings.effective_database_url
    masked_url = mask_url(raw_effective_url)
    
    is_sqlite = raw_effective_url.startswith("sqlite")
    
    print("=" * 60)
    print("QueryPilot - Database Connectivity & Schema Inspection")
    print("=" * 60)
    print(f"Active Precedence URL Source: {'SUPABASE_DB_URL' if settings.SUPABASE_DB_URL else 'DATABASE_URL'}")
    print(f"Masked Target URL:            {masked_url}")
    print(f"Engine Type:                  {'SQLite (Local Fallback)' if is_sqlite else 'PostgreSQL / Supabase'}")
    print("-" * 60)

    if is_sqlite:
        print("[INFO] No Supabase PostgreSQL URL configured. Current setting is SQLite.")
        print("[INFO] To connect to Supabase, update DATABASE_URL or SUPABASE_DB_URL in backend/.env.")
        return 0

    target_url, connect_args, engine_kwargs = get_engine_config(raw_effective_url)
    
    try:
        engine = create_engine(
            target_url,
            connect_args=connect_args,
            **engine_kwargs
        )
        
        with engine.connect() as conn:
            # Set session to READ ONLY for safety
            conn.execute(text("SET TRANSACTION READ ONLY;"))
            result = conn.execute(text("SELECT current_database(), current_user, version();")).fetchone()
            db_name = result[0]
            db_user = result[1]
            pg_version = result[2].split(",")[0]
            
            print("[SUCCESS] Connected successfully to Supabase PostgreSQL!")
            print(f"Connected Database:  {db_name}")
            print(f"Connected User:      {db_user}")
            print(f"PostgreSQL Version:  {pg_version}")
            print("-" * 60)
            
            # Check migration / table status
            tables_result = conn.execute(text(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;"
            )).fetchall()
            existing_tables = [row[0] for row in tables_result]
            
            print(f"Existing public tables ({len(existing_tables)}): {', '.join(existing_tables) if existing_tables else 'None (empty schema)'}")
            
            if "alembic_version" in existing_tables:
                rev_row = conn.execute(text("SELECT version_num FROM alembic_version;")).fetchone()
                current_rev = rev_row[0] if rev_row else "None"
                print(f"Current Alembic Revision: {current_rev}")
            else:
                print("Alembic Revision:     No alembic_version table found. Migrations are pending.")
                
        return 0
    except Exception as e:
        error_msg = str(e)
        # Ensure passwords or raw strings are not exposed
        for part in raw_effective_url.split("@"):
            if ":" in part and not part.startswith("http") and not part.startswith("postgres"):
                pw_candidate = part.split(":")[-1]
                if len(pw_candidate) > 3:
                    error_msg = error_msg.replace(pw_candidate, "******")
                    
        print("[ERROR] Connection failed to Supabase PostgreSQL:")
        print(f"Details: {error_msg}")
        return 1


if __name__ == "__main__":
    sys.exit(run_test())
