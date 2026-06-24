"""Orkiestracja: rownolegle odpytanie zrodel, scalenie, ranking i filtrowanie."""

from __future__ import annotations

import asyncio
import logging
import time
from collections import Counter
from typing import List

import httpx

from .config import settings
from .matching import (
    dedupe,
    location_matches,
    parse_query,
    score_offer,
    tokenize,
)
from .models import JobOffer, SearchRequest, SearchResponse, SourceCount
from .scrapers import SCRAPER_REGISTRY
from .scrapers.base import DEFAULT_HEADERS

logger = logging.getLogger("jobscout.search")


async def run_search(req: SearchRequest) -> SearchResponse:
    started = time.perf_counter()

    keywords, location, remote_only = parse_query(
        req.query, req.location, req.remote_only
    )
    logger.info(
        "Zapytanie='%s' -> slowa='%s', lokalizacja='%s', zdalna=%s",
        req.query, keywords, location, remote_only,
    )

    requested = req.sources or settings.sources
    selected = [s for s in requested if s in SCRAPER_REGISTRY]
    if not selected:
        selected = list(SCRAPER_REGISTRY.keys())

    async with httpx.AsyncClient(
        timeout=settings.request_timeout,
        headers=DEFAULT_HEADERS,
        follow_redirects=True,
    ) as client:
        scrapers = [SCRAPER_REGISTRY[s](client) for s in selected]
        batches = await asyncio.gather(
            *(sc.safe_search(keywords, location, settings.per_source_limit) for sc in scrapers)
        )

    all_offers: List[JobOffer] = [offer for batch in batches for offer in batch]

    terms = tokenize(keywords)
    for offer in all_offers:
        offer.score = score_offer(offer, terms)

    # Filtrowanie wg lokalizacji / pracy zdalnej.
    filtered = [
        o for o in all_offers
        if (not remote_only or o.remote) and location_matches(o, location)
    ]
    # Bezpiecznik: nie zostawiaj uzytkownika z pustka, gdy filtr lokalizacji jest zbyt ostry.
    if not filtered:
        filtered = [o for o in all_offers if (not remote_only or o.remote)]

    results = dedupe(filtered)
    results.sort(key=lambda o: o.score, reverse=True)
    results = results[: settings.total_limit]

    counts = Counter(o.source for o in results)
    by_source = [SourceCount(source=src, count=cnt) for src, cnt in counts.most_common()]
    took_ms = int((time.perf_counter() - started) * 1000)

    return SearchResponse(
        query=req.query,
        parsed_keywords=keywords,
        parsed_location=location,
        remote_only=remote_only,
        total=len(results),
        took_ms=took_ms,
        by_source=by_source,
        results=results,
    )
