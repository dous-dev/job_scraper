from __future__ import annotations

from typing import List, Optional

from ..matching import fold, tokenize
from ..models import JobOffer
from .base import BaseScraper


class JustJoinScraper(BaseScraper):
    """JustJoin.it - najwiekszy polski portal z ofertami IT (publiczne API JSON).

    Endpoint "by-cursor" zwraca najnowsze oferty, ale nie wyszukuje po slowie
    kluczowym po stronie serwera - dlatego pobieramy partie ofert i filtrujemy
    je lokalnie po tytule / firmie / lokalizacji.

    Zrodlo branzowe: ma sens dla zapytan technicznych ("python", "react").
    Dla zapytan spoza IT nie zwroci nic - i to jest OK.
    """

    id = "justjoin"
    name = "JustJoin.it"
    kind = "it"

    API_URL = "https://api.justjoin.it/v2/user-panel/offers/by-cursor"
    FETCH_BATCH = 100  # ile najnowszych ofert pobrac do lokalnego filtrowania

    async def search(self, keywords: str, location: Optional[str], limit: int) -> List[JobOffer]:
        terms = tokenize(keywords)
        if not terms:
            return []

        resp = await self.client.get(self.API_URL, params={"itemsCount": self.FETCH_BATCH})
        resp.raise_for_status()
        data = resp.json()
        items = data.get("data") if isinstance(data, dict) else data
        items = items or []

        offers: List[JobOffer] = []
        for item in items:
            slug = (item.get("slug") or "").strip()
            title = (item.get("title") or "").strip()
            if not slug or not title:
                continue

            company = (item.get("companyName") or "—").strip() or "—"
            city = (item.get("city") or "").strip()
            workplace = (item.get("workplaceType") or "").lower()
            remote = workplace == "remote"
            skills = ", ".join(
                s.get("name", "") for s in (item.get("requiredSkills") or []) if isinstance(s, dict)
            )

            # Lokalne dopasowanie: token musi wystapic w tytule / firmie / miescie / skillach.
            blob = fold(f"{title} {company} {city} {skills}")
            if not any(term in blob for term in terms):
                continue

            description = "Wymagane: " + skills if skills else f"Poziom: {item.get('experienceLevel', '—')}"

            offers.append(
                JobOffer(
                    title=title,
                    company=company,
                    location=("Zdalnie" if remote and not city else city),
                    url=f"https://justjoin.it/job-offer/{slug}",
                    source=self.name,
                    salary=self._format_salary(item),
                    description=description,
                    remote=remote,
                    posted=item.get("publishedAt"),
                    logo=item.get("companyLogoThumbUrl"),
                )
            )
            if len(offers) >= limit:
                break
        return offers

    @staticmethod
    def _format_salary(item: dict) -> Optional[str]:
        employment = item.get("employmentTypes") or []
        if not employment:
            return None
        first = employment[0]
        low, high = first.get("fromPln") or first.get("from"), first.get("toPln") or first.get("to")
        if low and high:
            etype = first.get("type", "")
            suffix = f" {etype}" if etype else ""
            return f"{int(low):,}-{int(high):,} PLN{suffix}".replace(",", " ")
        return None
