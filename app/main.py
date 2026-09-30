import os
import urllib.parse
from pathlib import Path
from fastapi import FastAPI, Request, Depends
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError

from app.database import init_db
from app.routes import (
    auth_routes,
    subject_routes,
    task_routes,
    session_routes,
    stats_routes,
    user_routes,
    ai_routes,
    mocktest_routes,
    exam_routes,
    revision_routes,
    resource_routes,
    search_routes
)
from app.auth import get_current_user
from app.models import DashboardStatsResponse, AIPlannerRequest, AIPlannerResponse

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="FocusFlow - Academic Productivity & Study Operating System",
    description="Professional full-stack productivity, roadmap, and examination preparation system for students.",
    version="2.0.0",
    redirect_slashes=False
)

class VercelPathRewriteASGI:
    """
    ASGI middleware ensuring Vercel rewrites preserve the target subpath
    (e.g. /api/auth/login) in the ASGI scope instead of /api/index.py.
    """
    def __init__(self, inner_app):
        self.inner_app = inner_app

    async def __call__(self, scope, receive, send):
        if scope.get("type") == "http":
            path = scope.get("path", "")
            qs = scope.get("query_string", b"").decode("utf-8", errors="ignore")
            params = urllib.parse.parse_qs(qs)

            real_path = None
            if "__vercel_path__" in params and params["__vercel_path__"]:
                real_path = params["__vercel_path__"][0]
                del params["__vercel_path__"]
                new_qs = urllib.parse.urlencode(params, doseq=True)
                scope["query_string"] = new_qs.encode("utf-8")

            if not real_path:
                headers = dict(scope.get("headers", []))
                for h in [b"x-matched-path", b"x-vercel-matched-path", b"x-forwarded-uri"]:
                    val = headers.get(h, b"").decode("utf-8", errors="ignore")
                    if val and val.startswith("/api"):
                        real_path = val
                        break

            if real_path:
                if "?" in real_path:
                    real_path, _ = real_path.split("?", 1)
                if not real_path.startswith("/"):
                    real_path = "/" + real_path
                if not real_path.startswith("/api"):
                    real_path = "/api" + real_path
                if len(real_path) > 1 and real_path.endswith("/"):
                    real_path = real_path.rstrip("/")
                scope["path"] = real_path
                scope["raw_path"] = real_path.encode("utf-8")
            elif path in ["/api/index.py", "/api/index.py/"]:
                scope["path"] = "/api/health"
                scope["raw_path"] = b"/api/health"

        await self.inner_app(scope, receive, send)

# Add Vercel path rewrite middleware
app.add_middleware(VercelPathRewriteASGI)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enforce fresh content (prevent aggressive browser caching of CSS/JS)
@app.middleware("http")
async def add_no_cache_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

# Friendly validation error handler
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    first_msg = errors[0].get("msg", "Invalid request input.") if errors else "Invalid request data."
    loc = " -> ".join([str(l) for l in errors[0].get("loc", [])]) if errors else ""
    return JSONResponse(
        status_code=422,
        content={"detail": f"{loc}: {first_msg}" if loc else first_msg}
    )

# Include all API routers
app.include_router(auth_routes.router)
app.include_router(user_routes.router)
app.include_router(subject_routes.router)
app.include_router(task_routes.router)
app.include_router(exam_routes.router)
app.include_router(revision_routes.router)
app.include_router(mocktest_routes.router)
app.include_router(session_routes.router)
app.include_router(resource_routes.router)
app.include_router(search_routes.router)
app.include_router(stats_routes.router)
app.include_router(ai_routes.router)

# Mount static assets safely (without attempting to mkdir in read-only environments)
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Initialize database schema safely
try:
    init_db()
except Exception as e:
    import logging
    logging.getLogger(__name__).warning(f"Database initialization deferred: {e}")

@app.on_event("startup")
def on_startup():
    try:
        init_db()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Startup database initialization error: {e}")

# Compatibility Aliases
@app.get("/api/dashboard/stats", response_model=DashboardStatsResponse, tags=["Dashboard & Stats"])
def api_dashboard_stats_alias(current_user: dict = Depends(get_current_user)):
    return stats_routes.get_dashboard_stats(current_user)

@app.post("/api/ai/study-plan", response_model=AIPlannerResponse, tags=["AI Study Assistant"])
async def api_ai_study_plan_alias(request: AIPlannerRequest, current_user: dict = Depends(get_current_user)):
    return await ai_routes.generate_study_plan(request, current_user)

def _read_index_html() -> str:
    candidates = [
        BASE_DIR / "public" / "index.html",
        BASE_DIR / "index.html",
        STATIC_DIR / "index.html",
        Path(__file__).resolve().parent.parent / "static" / "index.html"
    ]
    for p in candidates:
        if p.exists():
            try:
                return p.read_text(encoding="utf-8")
            except Exception:
                pass
    return "<!DOCTYPE html><html><head><title>FocusFlow</title></head><body><h1>FocusFlow is online.</h1></body></html>"

# Primary SPA Entrypoints
@app.get("/", response_class=HTMLResponse)
@app.get("/index.html", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
@app.get("/subjects", response_class=HTMLResponse)
@app.get("/roadmap", response_class=HTMLResponse)
@app.get("/planner", response_class=HTMLResponse)
@app.get("/exams", response_class=HTMLResponse)
@app.get("/revision", response_class=HTMLResponse)
@app.get("/mocktest", response_class=HTMLResponse)
@app.get("/timer", response_class=HTMLResponse)
@app.get("/ai", response_class=HTMLResponse)
@app.get("/analytics", response_class=HTMLResponse)
@app.get("/progress", response_class=HTMLResponse)
@app.get("/resources", response_class=HTMLResponse)
@app.get("/profile", response_class=HTMLResponse)
@app.get("/settings", response_class=HTMLResponse)
@app.get("/login", response_class=HTMLResponse)
@app.get("/signup", response_class=HTMLResponse)
async def serve_spa_page():
    return HTMLResponse(content=_read_index_html(), media_type="text/html")

@app.get("/dev/auth-relay", response_class=HTMLResponse)
def dev_auth_relay(token: str, redirect: str = "/#dashboard"):
    return HTMLResponse(f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Relaying...</title></head>
<body>
<script>
    localStorage.setItem('focusflow_token', '{token}');
    window.location.replace('{redirect}');
</script>
</body>
</html>""")

@app.get("/health")
@app.get("/api/health")
@app.get("/api")
@app.get("/api/")
def health_check():
    return {
        "status": "healthy",
        "app": "FocusFlow",
        "version": "2.0.0",
        "message": "FocusFlow Academic Productivity API is operational"
    }

# Catch-all route: serves static assets or SPA frontend without ever throwing 404 for pages
@app.get("/{full_path:path}")
async def catch_all_spa_and_static(full_path: str):
    # Static files fallback
    if full_path.startswith("static/"):
        rel_path = full_path[len("static/"):]
        for base in [STATIC_DIR, BASE_DIR / "public" / "static", BASE_DIR / "static"]:
            target = base / rel_path
            if target.exists() and target.is_file():
                ext = target.suffix.lower()
                content_types = {
                    ".css": "text/css; charset=utf-8",
                    ".js": "application/javascript; charset=utf-8",
                    ".json": "application/json; charset=utf-8",
                    ".png": "image/png",
                    ".jpg": "image/jpeg",
                    ".jpeg": "image/jpeg",
                    ".svg": "image/svg+xml",
                    ".ico": "image/x-icon",
                    ".wav": "audio/wav",
                    ".mp3": "audio/mpeg",
                    ".html": "text/html; charset=utf-8"
                }
                ct = content_types.get(ext, "application/octet-stream")
                if ext in [".css", ".js", ".json", ".html", ".svg"]:
                    return HTMLResponse(content=target.read_text(encoding="utf-8"), media_type=ct)
                else:
                    from fastapi.responses import Response
                    return Response(content=target.read_bytes(), media_type=ct)

    # API endpoints that do not exist return standard 404 JSON
    if full_path.startswith("api/"):
        return JSONResponse(status_code=404, content={"detail": f"API endpoint /{full_path} not found"})

    # All frontend route variations return index.html
    return HTMLResponse(content=_read_index_html(), media_type="text/html")
