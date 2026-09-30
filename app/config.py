import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("SECRET_KEY", "focusflow_default_secret_key_development_only_2026")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

def _resolve_database_path() -> str:
    env_db = os.getenv("DATABASE_PATH")
    if env_db and (env_db.startswith("/") or ":" in env_db):
        return env_db

    # Check if running in Vercel, AWS Lambda, or a read-only filesystem
    is_cloud = bool(
        os.getenv("VERCEL") or 
        os.getenv("AWS_LAMBDA_FUNCTION_NAME") or 
        os.getenv("VERCEL_ENV") or
        not os.access(str(BASE_DIR), os.W_OK)
    )

    if is_cloud:
        import shutil
        tmp_dir = Path("/tmp")
        try:
            tmp_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        tmp_db = tmp_dir / "focusflow.db"
        seed_db = BASE_DIR / "focusflow.db"
        if not tmp_db.exists() and seed_db.exists():
            try:
                shutil.copy2(str(seed_db), str(tmp_db))
            except Exception:
                pass
        return str(tmp_db)

    return str(BASE_DIR / (env_db or "focusflow.db"))

DATABASE_PATH = _resolve_database_path()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))
