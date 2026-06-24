"""Rejestr dostepnych zrodel ofert pracy."""

from typing import Dict, Type

from .base import BaseScraper
from .jooble import JoobleScraper
from .justjoin import JustJoinScraper
from .nofluffjobs import NoFluffJobsScraper
from .olx import OlxScraper

SCRAPER_REGISTRY: Dict[str, Type[BaseScraper]] = {
    JoobleScraper.id: JoobleScraper,
    OlxScraper.id: OlxScraper,
    JustJoinScraper.id: JustJoinScraper,
    NoFluffJobsScraper.id: NoFluffJobsScraper,
}

__all__ = ["SCRAPER_REGISTRY", "BaseScraper"]
