"""Vercel serverless function entry point.

Exposes the FastAPI ASGI app for Vercel's Python runtime.
"""

import sys
import traceback
from pathlib import Path

# Ensure the src directory is on the Python path so imports resolve
_src = Path(__file__).resolve().parent.parent / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

try:
    from immigration_compliance.api.app import app  # noqa: E402, F401
except Exception:
    # If the app fails to import, create a minimal ASGI app that returns the traceback
    # so the error is visible in the browser/logs instead of a generic 500.
    _tb = traceback.format_exc()
    print("IMPORT ERROR:\n" + _tb, file=sys.stderr)

    from fastapi import FastAPI
    from fastapi.responses import PlainTextResponse

    app = FastAPI()

    @app.get("/{path:path}")
    def _error(path: str = ""):
        return PlainTextResponse(
            f"App failed to start. Import error:\n\n{_tb}",
            status_code=500,
        )
