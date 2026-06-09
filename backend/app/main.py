"""FastAPI application entry point.

Mounts two families of routes:
  - Builder/dashboard routes (Supabase-JWT auth, RLS-backed): /api/account, /api/datasets,
    /api/keys
  - Consumer public API (API-key auth): /api/v1/datasets/{id}

Routers are added in later phases; Phase 0 only wires the app, CORS, the DB pool
lifespan, and a health check.
"""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import db
from app.config import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("spreadsheet_api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Best-effort pool startup: the scaffold should boot (and /health respond) even
    # before .env credentials are filled in. Routes that need the DB will surface a
    # clear error if the pool never came up.
    try:
        await db.connect()
        logger.info("Database pool connected.")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Database pool not connected at startup: %s", exc)
    yield
    await db.disconnect()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Spreadsheet-to-API",
        version="0.1.0",
        summary="Upload a spreadsheet, get a live queryable REST API.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:  # noqa: BLE001 — last-resort handler, keep the shape consistent
            elapsed = (time.perf_counter() - start) * 1000
            logger.exception("[%s] %s %s -> 500 (%.1fms)", request_id, request.method, request.url.path, elapsed)
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error.", "request_id": request_id},
                headers={"X-Request-ID": request_id},
            )
        elapsed = (time.perf_counter() - start) * 1000
        logger.info(
            "[%s] %s %s -> %s (%.1fms)",
            request_id, request.method, request.url.path, response.status_code, elapsed,
        )
        response.headers["X-Request-ID"] = request_id
        return response

    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    # Routers
    from app.routers import account, api_keys, datasets, public_api

    app.include_router(account.router)
    app.include_router(datasets.router)
    app.include_router(api_keys.router)
    app.include_router(public_api.router)

    return app


app = create_app()
