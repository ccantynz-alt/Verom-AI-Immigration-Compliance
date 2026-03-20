"""Vercel serverless function entry point.

Exposes the FastAPI ASGI app for Vercel's Python runtime.
"""

import sys
from pathlib import Path

# Ensure the src directory is on the Python path so imports resolve
_src = Path(__file__).resolve().parent.parent / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from immigration_compliance.api.app import app  # noqa: E402, F401
