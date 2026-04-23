"""
Start the FastAPI server from the project root, no matter where you invoke Python from.
Usage (from project root):
  python run_api.py
From frontend/:
  python ../run_api.py
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)

if __name__ == "__main__":
    raise SystemExit(
        subprocess.call(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "backend.main_api:app",
                "--reload",
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
            ],
            cwd=ROOT,
        )
    )
