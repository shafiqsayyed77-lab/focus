"""
FocusFlow Root Application Entrypoint
Exports FastAPI app for ASGI servers, Uvicorn, and Vercel serverless detection.
"""
from app.main import app

if __name__ == "__main__":
    import uvicorn
    from app.config import HOST, PORT
    print(f"Starting FocusFlow on http://{HOST}:{PORT}")
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=True)
