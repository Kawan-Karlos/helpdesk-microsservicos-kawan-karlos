# Construído a partir da raiz do repositório (para copiar a pasta comum/)
FROM python:3.12-slim

# Não roda como root dentro do contêiner
RUN useradd --create-home --uid 10001 helpdesk

WORKDIR /srv
COPY servicos/chamados/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY comum ./comum
COPY servicos/chamados/app ./app

USER helpdesk
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
EXPOSE 8000
# --proxy-headers: o IP do usuário chega do gateway (usado no limite de tentativas de login)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
