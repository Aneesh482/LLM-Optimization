"""FastAPI application entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models.database import init_db
from app.api.routes import router

# ── Logging ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if settings.app_debug else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ── Lifespan ─────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database …")
    await init_db()
    logger.info("LLM Gateway ready (env=%s)", settings.app_env)
    yield
    logger.info("Shutting down …")


# ── App ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="LLM Optimization Gateway",
    description="A smart proxy that optimizes context before sending it to Gemini.",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow the React dashboard in dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
