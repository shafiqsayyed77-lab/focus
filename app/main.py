import os
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
    version="2.0.0"
)

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

# Page routes for direct browser navigation
@app.get("/")
@app.get("/dashboard")
@app.get("/subjects")
@app.get("/roadmap")
@app.get("/planner")
@app.get("/exams")
@app.get("/revision")
@app.get("/mocktest")
@app.get("/timer")
@app.get("/ai")
@app.get("/analytics")
@app.get("/progress")
@app.get("/resources")
@app.get("/profile")
@app.get("/settings")
@app.get("/login")
@app.get("/signup")
async def serve_spa_page():
    """Serves the primary Single Page Application interface."""
    root_file = BASE_DIR / "index.html"
    if root_file.exists():
        return FileResponse(str(root_file))
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "FocusFlow API is online."}

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
def health_check():
    return {"status": "healthy", "app": "FocusFlow", "version": "2.0.0"}
