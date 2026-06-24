from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from ..models import JobOffer
from .base import BaseScraper


class NoFluffJobsScraper(BaseScraper):
    """NoFluffJobs - portal z ofertami IT (publiczne search API JSON).

    Drugie zrodlo branzowe IT. Jak JustJoin: cenne dla zapytan technicznych,
    neutralne dla pozostalych (zostana odfiltrowane przez ranking trafnosci).
    """

    id = "nofluffjobs"
    name = "NoFluffJobs"
    kind = "it"

    API_URL = "https://nofluffjobs.com/api/search/posting"

    async def search(self, keywords: str, location: Optional[str], limit: int) -> List[JobOffer]:
        params = {
            "pageSize": min(max(limit, 1), 100),
            "pageTo": 1,
            "salaryCurrency": "PLN",
            "salaryPeriod": "month",
            "region": "pl",
        }
        # Kluczowe: poprawny klucz body to "rawSearch" (rawJobTitle zwraca HTTP 500).
        body = {"rawSearch": keywords}
        resp = await self.client.post(
            self.API_URL,
            params=params,
            json=body,
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()

        postings = data.get("postings") if isinstance(data, dict) else None
        postings = postings or []

        offers: List[JobOffer] = []
        for item in postings[:limit]:
            slug = (item.get("url") or "").strip()
            if not slug:
                continue

            fully_remote = bool(item.get("fullyRemote"))
            city = self._first_city(item)

            tech = (item.get("technology") or "").strip()
            seniority = ", ".join(item.get("seniority") or [])
            description = " · ".join(p for p in (tech, seniority) if p)

            offers.append(
                JobOffer(
                    title=(item.get("title") or "").strip() or "Bez tytulu",
                    company=(item.get("name") or "—").strip() or "—",
                    location=("Zdalnie" if fully_remote else (city or "—")),
                    url=f"https://nofluffjobs.com/pl/job/{slug}",
                    source=self.name,
                    salary=self._format_salary(item),
                    description=description,
                    remote=fully_remote,
                    posted=self._format_posted(item.get("posted")),
                    logo=item.get("logo", {}).get("original") if isinstance(item.get("logo"), dict) else None,
                )
            )
        return offers

    @staticmethod
    def _format_posted(value) -> Optional[str]:
        # NFJ zwraca znacznik czasu w milisekundach (epoch ms).
        if isinstance(value, (int, float)):
            try:
                return datetime.fromtimestamp(value / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
            except (ValueError, OSError):
                return None
        return str(value) if value else None

    @staticmethod
    def _first_city(item: dict) -> str:
        places = (item.get("location") or {}).get("places") or []
        for place in places:
            city = (place.get("city") or "").strip()
            if city and city.lower() != "remote":
                return city
        return ""

    @staticmethod
    def _format_salary(item: dict) -> Optional[str]:
        salary = item.get("salary") or {}
        low, high = salary.get("from"), salary.get("to")
        currency = salary.get("currency", "PLN")
        if low and high:
            return f"{low:,}-{high:,} {currency}".replace(",", " ")
        return None
