"""App FastAPI — Chat IA-Guia (serviço backend).

Etapa 3 (esqueleto): GET /health (pública), GET /me (protegida).
Etapa 4a (chat do SDR): conversas e mensagens com IA assíncrona (router em chat.py).
Etapa 4bc: agente com ferramentas Clint (SDR + closer), papel closer, apagar conversa.

Sem admin, sem gerador de playbook, sem resumo (Etapa 6).
"""

from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import Identity, get_identity
from .chat import router as chat_router
from .config import Settings, get_settings
from .roles import resolve_papel

app = FastAPI(title="Chat IA-Guia — Serviço (Etapa 4bc)", version="1.2")

# CORS (Etapa 5, T-01): libera a(s) origem(ns) do front para chamar o serviço do
# navegador. Em DEV, a regex libera qualquer porta de localhost/127.0.0.1 (Next em
# 3000, 3001, ...). Em PROD, a origem da Vercel entra na LISTA via CORS_ORIGINS.
# Nunca origem "*" literal: com credenciais, a origem precisa ser explícita
# (lista) ou casar a regex — o middleware reflete a origem de volta.
_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origins,
    allow_origin_regex=_settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS", "PATCH", "PUT"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/health")
def health() -> dict:
    """Prova que o serviço subiu. Não exige login."""
    return {"status": "ok"}


@app.get("/me")
async def me(
    identity: Identity = Depends(get_identity),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Prova o pipeline: valida o JWT e resolve o papel do usuário."""
    papel = await resolve_papel(identity.user_id, settings)
    return {
        "user_id": identity.user_id,
        "email": identity.email,
        "papel": papel,
    }


app.include_router(chat_router)
