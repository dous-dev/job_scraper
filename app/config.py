from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Konfiguracja aplikacji ladowana ze zmiennych srodowiskowych / pliku .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Klucz API Jooble wczytywany WYLACZNIE z .env (nigdy nie trzymamy go w kodzie).
    # Pobierz darmowy klucz: https://pl.jooble.org/api/about
    # Bez klucza zrodlo Jooble jest pomijane - pozostale (OLX/JustJoin/NoFluffJobs) dzialaja.
    jooble_api_key: str = ""

    request_timeout: float = 20.0
    per_source_limit: int = 30
    total_limit: int = 120
    enabled_sources: str = "jooble,olx,justjoin,nofluffjobs"

    # Serwer
    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = True

    @property
    def sources(self) -> list[str]:
        return [s.strip().lower() for s in self.enabled_sources.split(",") if s.strip()]


settings = Settings()
