"""FastAPI application factory for SimulateAI."""

import time
from collections import defaultdict
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src.api.routes import router
from src.api.export import router as export_router
from src.api.webhook_routes import router as webhook_router
from src.persistence.db import init_db

STATIC_DIR = Path(__file__).resolve().parent.parent.parent / "static" / "dist"

RATE_LIMIT_MAX = 3
RATE_LIMIT_WINDOW = 86400  # 24 hours in seconds
_rate_store: dict[str, list[float]] = defaultdict(list)


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _is_rate_limited(ip: str) -> bool:
    now = time.time()
    timestamps = _rate_store[ip]
    _rate_store[ip] = [t for t in timestamps if now - t < RATE_LIMIT_WINDOW]
    return len(_rate_store[ip]) >= RATE_LIMIT_MAX


def _record_usage(ip: str):
    _rate_store[ip].append(time.time())


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle: DB init on startup, cleanup on shutdown."""
    db = await init_db()
    app.state.db = db
    yield
    await db.close()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="SimulateAI",
        description="Multi-agent LLM simulation API — run swarm debates, "
                    "crisis stress-tests, and resilience analysis.",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS — allow all origins for dev
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Rate limiter middleware for POST /api/simulate
    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        if request.method == "POST" and request.url.path == "/api/simulate":
            has_own_key = request.headers.get("x-api-key")
            if not has_own_key:
                ip = _get_client_ip(request)
                if _is_rate_limited(ip):
                    return JSONResponse(
                        status_code=429,
                        content={
                            "detail": "Demo limit reached (3 runs/day). Add your own API key for unlimited access.",
                            "limit": RATE_LIMIT_MAX,
                            "window": "24h",
                        },
                    )
                _record_usage(ip)
        response = await call_next(request)
        return response

    app.include_router(router)
    app.include_router(export_router)
    app.include_router(webhook_router)

    # Serve frontend static build if it exists
    if STATIC_DIR.exists():
        # Serve static assets (JS/CSS bundles)
        assets_dir = STATIC_DIR / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="static-assets")

        # SPA fallback: serve index.html for non-API routes
        @app.get("/")
        async def serve_root():
            return FileResponse(str(STATIC_DIR / "index.html"))

        @app.get("/{full_path:path}")
        async def spa_fallback(full_path: str):
            # If the file exists in static dir, serve it
            file_path = STATIC_DIR / full_path
            if file_path.is_file() and STATIC_DIR in file_path.resolve().parents:
                return FileResponse(str(file_path))
            # Otherwise serve index.html for SPA routing
            return FileResponse(str(STATIC_DIR / "index.html"))

    return app
