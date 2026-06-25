"""SimulateAI API Server entry point.

Usage:
    python server.py                    # Start on port 8000
    python server.py --port 9000        # Custom port
    python server.py --reload           # Auto-reload for development
"""
import argparse
import sys
from pathlib import Path

# Ensure project root is on path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import uvicorn  # noqa: E402

from src.api.app import create_app  # noqa: E402


app = create_app()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SimulateAI API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Bind port (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    args = parser.parse_args()

    uvicorn.run(
        "server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )
