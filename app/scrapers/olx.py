from __future__ import annotations

from typing import List, Optional

from ..matching import detect_remote, strip_html
from ..models import JobOffer
from .base import BaseScraper

# Kategoria "Praca" w publicznym API OLX.
OLX_JOBS_CATEGORY = 4


class OlxScraper(BaseScraper):
    """OLX Praca - najwiekszy w PL portal z ogloszeniami ogolnymi.

    Korzysta z publicznego JSON API OLX (bez przegladarki). Wyszukiwarka OLX
    przeszukuje zarowno tytul, jak i pelny opis ogloszenia po stronie serwera,
    a opis trafia rowniez do naszej oceny trafnosci.
    """

    id = "olx"
    name = "OLX"
    kind = "general"

    API_URL = "https://www.olx.pl/api/v1/offers/"

    async def search(self, keywords: str, location: Optional[str], limit: int) -> List[JobOffer]:
        params = {
            "offset": 0,
            "limit": min(max(limit, 1), 50),
            "category_id": OLX_JOBS_CATEGORY,
            "query": keywords,
            "sort_by": "created_at:desc",
        }
        resp = await self.client.get(
            self.API_URL,
            params=params,
            headers={
                "Accept": "application/json",
                "Referer": "https://www.olx.pl/praca/",
                "Origin": "https://www.olx.pl",
                "X-Requested-With": "XMLHttpRequest",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
            },
        )
        resp.raise_for_status()
        data = resp.json()

        offers: List[JobOffer] = []
        for item in (data.get("data") or [])[:limit]:
            title = (item.get("title") or "").strip()
            description = strip_html(item.get("description"))[:800]

            location_str, salary = self._extract_location_and_salary(item)
            logo = self._first_photo(item)

            offers.append(
                JobOffer(
                    title=title or "Bez tytulu",
                    company="—",
                    location=location_str,
                    url=(item.get("url") or "").strip(),
                    source=self.name,
                    salary=salary,
                    description=description,
                    remote=detect_remote(location_str, title, description),
                    posted=(item.get("created_time") or None),
                    logo=logo,
                )
            )
        return offers

    @staticmethod
    def _extract_location_and_salary(item: dict) -> tuple[str, Optional[str]]:
        loc = item.get("location") or {}
        city = ((loc.get("city") or {}).get("name") or "").strip()
        region = ((loc.get("region") or {}).get("name") or "").strip()
        location_str = ", ".join(p for p in (city, region) if p)

        salary: Optional[str] = None
        for param in item.get("params") or []:
            if param.get("key") == "salary":
                value = param.get("value") or {}
                label = value.get("label")
                if label:
                    salary = str(label).strip()
                elif value.get("from") and value.get("to"):
                    currency = value.get("currency", "zl")
                    salary = f"{value['from']}-{value['to']} {currency}"
                break
        return location_str, salary

    @staticmethod
    def _first_photo(item: dict) -> Optional[str]:
        photos = item.get("photos") or []
        if not photos:
            return None
        link = photos[0].get("link") or ""
        # Szablon OLX zawiera placeholdery {width}/{height}.
        return link.replace("{width}", "200").replace("{height}", "150") or None
