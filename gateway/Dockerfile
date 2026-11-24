# Construído a partir da raiz do repositório (para copiar a pasta comum/)
FROM python:3.12-slim

RUN useradd --create-home --uid 10001 helpdesk

WORKDIR /srv
COPY gateway/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY comum ./comum
COPY gateway/app ./app
COPY gateway/web ./web

USER helpdesk
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 WEB_DIR=/srv/web
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
