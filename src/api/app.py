"""FastAPI application factory for SimulateAI."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.api.routes import router
from src.api.export import router as export_router
from src.api.webhook_routes import router as webhook_router
from src.persistence.db import init_db

STATIC_DIR = Path(__file__).resolve().parent.parent.parent / "static" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle: DB init on startup, cleanup on shutdown."""
    # Startup
    db = await init_db()
    app.state.db = db
    yield
    # Shutdown
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
