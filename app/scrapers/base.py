from __future__ import annotations

import abc
import asyncio
import logging
from typing import List, Optional

import httpx

from ..models import JobOffer

logger = logging.getLogger("jobscout.scraper")

# Realistyczne naglowki - wiekszosc API odrzuca puste/podejrzane User-Agenty.
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
}

# Twardy limit czasu na pojedyncze zrodlo - chroni przed zawieszeniem calego wyszukiwania.
PER_SOURCE_TIMEOUT = 25.0


class BaseScraper(abc.ABC):
    """Wspolny kontrakt dla wszystkich zrodel ofert.

    Kazde zrodlo dziala niezaleznie i jest w pelni izolowane bledami:
    awaria jednego portalu NIGDY nie wywala calego wyszukiwania.
    """

    id: str = "base"
    name: str = "Base"
    kind: str = "general"  # "general" | "it"

    def __init__(self, client: httpx.AsyncClient):
        self.client = client

    @abc.abstractmethod
    async def search(self, keywords: str, location: Optional[str], limit: int) -> List[JobOffer]:
        """Implementacja konkretnego zrodla. Moze rzucac wyjatkami."""
        raise NotImplementedError

    async def safe_search(self, keywords: str, location: Optional[str], limit: int) -> List[JobOffer]:
        """Bezpieczne opakowanie: timeout + przechwycenie kazdego bledu."""
        try:
            offers = await asyncio.wait_for(
                self.search(keywords, location, limit),
                timeout=PER_SOURCE_TIMEOUT,
            )
            valid = [o for o in offers if o.url and o.title]
            logger.info("[%s] zwrocono %d ofert", self.name, len(valid))
            return valid
        except asyncio.TimeoutError:
            logger.warning("[%s] przekroczono limit czasu (%.0fs)", self.name, PER_SOURCE_TIMEOUT)
        except httpx.HTTPStatusError as exc:
            logger.warning("[%s] blad HTTP %s", self.name, exc.response.status_code)
        except httpx.HTTPError as exc:
            logger.warning("[%s] blad polaczenia: %s", self.name, exc)
        except Exception as exc:  # noqa: BLE001 - celowo lapiemy wszystko, by nie ubic potoku
            logger.warning("[%s] nieoczekiwany blad: %s", self.name, exc)
        return []
