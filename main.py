import os
import sys

# Ensure root directory is in sys.path
root_dir = os.path.dirname(os.path.abspath(__file__))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import uvicorn

if __name__ == "__main__":
    print("=" * 60)
    print("  Kestrel Returns Intelligence Platform - Unified Server  ")
    print("=" * 60)
    print("Starting FastAPI + React UI on http://localhost:8000 ...")
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
