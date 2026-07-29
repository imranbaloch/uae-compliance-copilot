"""FastAPI application entrypoint.

    uvicorn api.app:app --reload

Exposes:
- JSON API under /api (see api/routes.py) — OpenAPI docs at /docs
- HTML dashboard under /web (see api/web.py)
- / redirects to /web
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from api import routes, store, web
from compliance_copilot.config import get_settings
from compliance_copilot.logging_config import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    store.init_db()
    yield


app = FastAPI(
    title="UAE Compliance Copilot API",
    description="Multi-agent UAE SME tax/e-invoicing/AML compliance reconciliation.",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes.router)
app.include_router(web.router)
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/web")


@app.get("/health", tags=["meta"])
async def health() -> dict:
    return {"status": "ok"}
