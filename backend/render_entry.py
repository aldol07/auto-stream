"""
Render start command: fixes sys.path so `backend` imports work on Render.

Use in Render **Start Command** (pick one):

- Root directory = **repo root** (recommended, leave blank / `.`):
    python backend/render_entry.py

- Root directory = **backend** (subfolder):
    python render_entry.py

Do not use `uvicorn backend.main_api:app` alone if Render’s working directory
omits the repo root — it causes: ModuleNotFoundError: No module named 'backend'.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# This file is backend/render_entry.py → repo root is parent
BACKEND_DIR = Path(__file__).resolve().parent
ROOT = BACKEND_DIR.parent

os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(
        "backend.main_api:app",
        host="0.0.0.0",
        port=port,
        proxy_headers=True,
    )


if __name__ == "__main__":
    main()
