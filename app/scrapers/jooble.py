from __future__ import annotations

from typing import List, Optional

from ..config import settings
from ..matching import detect_remote, strip_html
from ..models import JobOffer
from .base import BaseScraper


class JoobleScraper(BaseScraper):
    """Jooble - agregator ofert z wielu portali (oficjalne REST API).

    Pokrywa WSZYSTKIE branze (ksiegowosc, budowlanka, handel, IT...), wiec
    jest glownym, ogolnym zrodlem dla zapytan typu "stolarz" czy "ksiegowa".
    Przeszukuje pelna tresc ofert, a w odpowiedzi zwraca fragment opisu.
    """

    id = "jooble"
    name = "Jooble"
    kind = "general"

    API_BASE = "https://pl.jooble.org/api/"

    async def search(self, keywords: str, location: Optional[str], limit: int) -> List[JobOffer]:
        api_key = settings.jooble_api_key.strip()
        if not api_key:
            return []

        payload = {"keywords": keywords, "location": location or ""}
        resp = await self.client.post(
            self.API_BASE + api_key,
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()

        offers: List[JobOffer] = []
        for job in (data.get("jobs") or [])[:limit]:
            location_str = (job.get("location") or "").strip()
            description = strip_html(job.get("snippet"))
            title = (job.get("title") or "").strip()
            company = (job.get("company") or "").strip() or "—"
            salary = (job.get("salary") or "").strip() or None

            offers.append(
                JobOffer(
                    title=title or "Bez tytulu",
                    company=company,
                    location=location_str,
                    url=(job.get("link") or "").strip(),
                    source=self.name,
                    salary=salary,
                    description=description,
                    remote=detect_remote(location_str, title, description),
                    posted=(job.get("updated") or None),
                )
            )
        return offers
