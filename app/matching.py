"""Logika przetwarzania zapytan i oceny trafnosci ofert.

Tu mieszka cala "inteligencja" wyszukiwarki: rozbijanie naturalnego zapytania
uzytkownika (np. "praca zdalna w branzy ksiegowosci") na slowa kluczowe,
lokalizacje i flage pracy zdalnej, a takze scoring ofert na podstawie tytulu
ORAZ opisu (nie tylko samego tytulu).
"""

from __future__ import annotations

import html
import re
import unicodedata
from typing import List, Optional, Tuple

from .models import JobOffer

# Frazy sygnalizujace prace zdalna.
REMOTE_TERMS = [
    "praca zdalna", "zdalna", "zdalnie", "zdalny", "zdalne", "zdalnej",
    "remote", "fully remote", "home office", "praca z domu",
    "hybrydowo", "hybrydowa", "hybryda",
]

# Najwieksze polskie miasta (do wykrywania lokalizacji w naturalnym zapytaniu).
CITY_LIST = [
    "warszawa", "krakow", "lodz", "wroclaw", "poznan", "gdansk", "szczecin",
    "bydgoszcz", "lublin", "katowice", "bialystok", "gdynia", "czestochowa",
    "radom", "sosnowiec", "torun", "kielce", "rzeszow", "gliwice", "zabrze",
    "olsztyn", "bielsko-biala", "bytom", "zielona gora", "rybnik", "ruda slaska",
    "opole", "tychy", "gorzow wielkopolski", "elblag", "plock", "walbrzych",
    "wloclawek", "tarnow", "chorzow", "koszalin", "kalisz", "legnica",
    "trojmiasto", "slask", "mazowsze",
]

# Slowa wypelniacze, ktore nie niosa wartosci jako slowo kluczowe.
STOPWORDS = {
    "praca", "pracy", "prace", "oferta", "oferty", "ofert", "szukam", "szukac",
    "w", "we", "na", "do", "z", "ze", "i", "oraz", "dla", "jako", "branzy",
    "branza", "branze", "stanowisko", "stanowiska", "okolicy", "okolice",
    "rejonie", "miescie", "miasto", "praca", "etat", "pelny", "czas",
}

_TAG_RE = re.compile(r"<[^>]+>")
_WORD_RE = re.compile(r"[0-9a-ząćęłńóśźż\+\#]+", re.IGNORECASE)


def strip_html(text: Optional[str]) -> str:
    """Usuwa tagi HTML i normalizuje biale znaki."""
    if not text:
        return ""
    text = _TAG_RE.sub(" ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _fold(text: str) -> str:
    """Zamienia na male litery i usuwa polskie znaki diakrytyczne (ł -> l itd.)."""
    text = (text or "").lower().replace("ł", "l").replace("Ł", "l")
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def fold(text: str) -> str:
    """Publiczny alias normalizacji - przydatny w scraperach filtrujacych lokalnie."""
    return _fold(text)


def tokenize(text: str) -> List[str]:
    folded = _fold(text)
    return [t for t in _WORD_RE.findall(folded) if len(t) > 1 or t in {"c", "r"}]


def detect_remote(*texts: str) -> bool:
    blob = _fold(" ".join(t for t in texts if t))
    return any(_fold(term) in blob for term in REMOTE_TERMS)


def parse_query(
    query: str,
    location_override: Optional[str] = None,
    remote_override: bool = False,
) -> Tuple[str, Optional[str], bool]:
    """Rozbija naturalne zapytanie na (slowa_kluczowe, lokalizacja, tylko_zdalna).

    Przyklady:
        "praca zdalna w branzy ksiegowosci" -> ("ksiegowosci", None, True)
        "stolarz w lodzi"                   -> ("stolarz", "lodz", False)
    """
    raw = (query or "").strip()
    folded = _fold(raw)

    remote = bool(remote_override) or detect_remote(raw)

    # Wykrycie lokalizacji w tekscie zapytania (jesli nie podano jawnie).
    location = location_override.strip() if location_override else None
    if not location:
        for city in CITY_LIST:
            if re.search(r"\b" + re.escape(_fold(city)) + r"\b", folded):
                location = city
                break

    folded_location = _fold(location) if location else None
    folded_remote = {_fold(t) for t in REMOTE_TERMS}

    # Budujemy slowa kluczowe z ORYGINALNEGO tekstu (zachowujemy polskie znaki -
    # polskie portale lepiej radza sobie z "ksiegowosci" pisanym z diakrytykami).
    # Porownania (stopwords/remote/lokalizacja) robimy na formie zlozonej (folded).
    keywords: List[str] = []
    for token in _WORD_RE.findall(raw.lower()):
        folded_token = _fold(token)
        if folded_token in STOPWORDS:
            continue
        if folded_token in folded_remote:
            continue
        if folded_location and folded_token in folded_location.split():
            continue
        keywords.append(token)

    keyword_str = " ".join(keywords).strip()
    # Awaryjnie: jesli po oczyszczeniu nic nie zostalo, uzyj surowego zapytania.
    if not keyword_str:
        keyword_str = raw

    return keyword_str, location, remote


def score_offer(offer: JobOffer, terms: List[str]) -> float:
    """Ocena trafnosci oferty.

    Klucz wymagania: przeszukujemy NIE tylko tytul, ale i opis oraz firme.
    Wagi: tytul (3), firma (1.5), opis (1) + bonus za pokrycie wszystkich slow.
    """
    if not terms:
        return 1.0

    title = _fold(offer.title)
    desc = _fold(offer.description)
    company = _fold(offer.company)

    score = 0.0
    matched = 0
    for term in terms:
        hit = False
        if term in title:
            score += 3.0
            hit = True
        if term in company:
            score += 1.5
            hit = True
        if term in desc:
            score += 1.0
            hit = True
        if hit:
            matched += 1

    # Bonus za to, ile z wszystkich slow kluczowych zostalo dopasowanych.
    score += (matched / len(terms)) * 2.0
    return round(score, 3)


def location_matches(offer: JobOffer, location: Optional[str]) -> bool:
    if not location:
        return True
    if offer.remote:
        return True
    return _fold(location) in _fold(offer.location)


def dedupe(offers: List[JobOffer]) -> List[JobOffer]:
    """Usuwa duplikaty po znormalizowanym URL i sygnaturze (tytul+firma)."""
    seen_urls: set[str] = set()
    seen_sigs: set[str] = set()
    result: List[JobOffer] = []
    for offer in offers:
        url_key = offer.url.split("?")[0].rstrip("/").lower()
        sig = f"{_fold(offer.title)}|{_fold(offer.company)}"
        if url_key and url_key in seen_urls:
            continue
        if sig in seen_sigs:
            continue
        if url_key:
            seen_urls.add(url_key)
        seen_sigs.add(sig)
        result.append(offer)
    return result
