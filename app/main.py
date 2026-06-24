from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .config import settings
from .models import SearchRequest, SearchResponse, SourceInfo
from .scrapers import SCRAPER_REGISTRY
from .search import run_search

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app = FastAPI(
    title="JobScout API",
    description="Wieloźródłowy agregator ofert pracy (Jooble, OLX, JustJoin.it, NoFluffJobs).",
    version=__version__,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "version": __version__}


@app.get("/api/sources", response_model=list[SourceInfo])
async def sources() -> list[SourceInfo]:
    return [
        SourceInfo(id=cls.id, name=cls.name, kind=cls.kind)
        for cls in SCRAPER_REGISTRY.values()
    ]


@app.post("/api/search", response_model=SearchResponse)
async def search(req: SearchRequest) -> SearchResponse:
    return await run_search(req)


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


# Statyczny frontend (CSS/JS) montujemy na koncu, by nie przyslonil tras /api.
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
