import uvicorn
from app.config import HOST, PORT

if __name__ == "__main__":
    print(f"Starting FocusFlow on http://{HOST}:{PORT}")
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=False)
