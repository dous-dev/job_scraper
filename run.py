"""Punkt wejscia: uruchamia serwer deweloperski.

Uzycie:
    python run.py
Nastepnie otworz wypisany adres (domyslnie http://127.0.0.1:8000).

Jesli skonfigurowany port jest zajety (np. zostal po poprzednim uruchomieniu),
skrypt automatycznie wybierze nastepny wolny port - nie trzeba nic robic recznie.
"""

import socket

import uvicorn

from app.config import settings


def is_port_free(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((host, port))
            return True
        except OSError:
            return False


def pick_port(host: str, preferred: int, attempts: int = 30) -> int:
    if is_port_free(host, preferred):
        return preferred
    for candidate in range(preferred + 1, preferred + 1 + attempts):
        if is_port_free(host, candidate):
            print(f"[JobScout] Port {preferred} jest zajety - przechodze na {candidate}.")
            return candidate
    raise SystemExit(
        f"[JobScout] Nie znalazlem wolnego portu w zakresie {preferred}-{preferred + attempts}."
    )


if __name__ == "__main__":
    port = pick_port(settings.host, settings.port)
    print(f"[JobScout] Start: http://{settings.host}:{port}  (dokumentacja API: /docs)")
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=port,
        reload=settings.reload,
    )
