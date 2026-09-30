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

# In serverless environments (Vercel / AWS Lambda), the code directory is read-only.
# Copy pre-seeded SQLite database to /tmp so all reads/writes succeed seamlessly.
is_serverless = bool(os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME") or os.getenv("VERCEL_ENV"))
if is_serverless:
    import shutil
    tmp_db = Path("/tmp/focusflow.db")
    seed_db = BASE_DIR / "focusflow.db"
    if not tmp_db.exists() and seed_db.exists():
        try:
            shutil.copy2(seed_db, tmp_db)
        except Exception:
            pass
    DATABASE_PATH = str(tmp_db)
else:
    DATABASE_PATH = str(BASE_DIR / os.getenv("DATABASE_PATH", "focusflow.db"))

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))
