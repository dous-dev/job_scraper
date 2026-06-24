from typing import List, Optional

from pydantic import BaseModel, Field


class JobOffer(BaseModel):
    """Pojedyncza, znormalizowana oferta pracy z dowolnego zrodla."""

    title: str
    company: str = "—"
    location: str = ""
    url: str
    source: str
    salary: Optional[str] = None
    description: str = ""
    remote: bool = False
    posted: Optional[str] = None
    logo: Optional[str] = None
    score: float = 0.0


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=200)
    location: Optional[str] = Field(default=None, max_length=100)
    remote_only: bool = False
    sources: Optional[List[str]] = None


class SourceCount(BaseModel):
    source: str
    count: int


class SearchResponse(BaseModel):
    query: str
    parsed_keywords: str
    parsed_location: Optional[str] = None
    remote_only: bool = False
    total: int
    took_ms: int
    by_source: List[SourceCount]
    results: List[JobOffer]


class SourceInfo(BaseModel):
    id: str
    name: str
    kind: str
