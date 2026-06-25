"""FastAPI application factory for SimulateAI."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import router
from src.persistence.db import init_db


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
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)

    return app
