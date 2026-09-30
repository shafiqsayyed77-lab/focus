import sys
import traceback
import urllib.parse
from pathlib import Path

# Add project root directory to Python path for serverless imports
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from app.main import app as fastapi_app

    class VercelServerlessEntry:
        """
        Serverless entrypoint wrapper ensuring Vercel rewrites to /api/index.py
        preserve the target subpath (e.g. /api/auth/login) in the ASGI scope.
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

    app = VercelServerlessEntry(fastapi_app)

except Exception as e:
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse

    err_trace = traceback.format_exc()
    app = FastAPI(title="FocusFlow Diagnostic Mode")

    @app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"])
    async def diagnostic_handler(full_path: str):
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "FocusFlow Serverless Initialization Failed",
                "detail": str(e),
                "traceback": err_trace
            }
        )

