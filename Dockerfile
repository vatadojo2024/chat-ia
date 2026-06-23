# Chat IA-Guia — serviço backend (FastAPI). Empacotamento para a VPS.
# Roda atrás do Traefik já existente (este container NÃO sobe Traefik).
FROM python:3.12-slim

# Logs sem buffer e sem .pyc no container.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Dependências primeiro (aproveita cache de camada).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código e prompts (o app lê prompts/sdr.md e prompts/closer.md em runtime).
COPY app/ ./app/
COPY prompts/ ./prompts/

# Roda sem privilégios.
RUN useradd --create-home appuser
USER appuser

# Porta interna do serviço (o Traefik faz o roteamento externo).
EXPOSE 8000

# Healthcheck simples na rota pública /health (sem curl na imagem slim).
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').status==200 else 1)"

# HOST 0.0.0.0 para o Docker/Traefik alcançarem o serviço (NUNCA 127.0.0.1/localhost).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
