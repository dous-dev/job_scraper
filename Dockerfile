FROM python:3.12-slim

# Brak buforowania stdout/stderr + brak plikow .pyc
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HOST=0.0.0.0 \
    PORT=8000 \
    RELOAD=false

WORKDIR /app

# Najpierw zaleznosci - lepsze wykorzystanie cache warstw Dockera
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Klucz Jooble (opcjonalny) podajesz przez zmienna srodowiskowa:
#   docker run -e JOOBLE_API_KEY=twoj_klucz -p 8000:8000 jobscout
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
