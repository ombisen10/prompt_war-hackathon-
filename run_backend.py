"""Runner script to launch GuardianAI backend server on http://127.0.0.1:8000."""
import sys
import os

# Ensure backend folder is in sys.path
backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.main import app
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    host = os.environ.get("HOST", "127.0.0.1")
    print(f"Starting GuardianAI Backend on http://{host}:{port} ...")
    uvicorn.run(app, host=host, port=port)
