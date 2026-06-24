"""Acesso a dados das tabelas de chat via PostgREST com service_role.

O service_role IGNORA a RLS — por isso o serviço SEMPRE checa o dono no código
(RF-07 / RNF-03). A RLS continua protegendo acesso direto (defesa em dois lugares).
"""

from __future__ import annotations

from datetime import datetime, timezone

import httpx

from .config import Settings

_TIMEOUT = 15.0


def _headers(settings: Settings, *, representation: bool = False) -> dict:
    h = {
        "apikey": settings.supabase_key,
        "Authorization": f"Bearer {settings.supabase_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if representation:
        h["Prefer"] = "return=representation"
    return h


def _rest(settings: Settings, tabela: str) -> str:
    return f"{settings.supabase_url}/rest/v1/{tabela}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ----------------------------- conversas -------------------------------------

async def criar_conversa(user_id: str, papel: str, settings: Settings) -> dict:
    payload = {"user_id": user_id, "papel": papel}
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(
            _rest(settings, "chat_conversas"),
            headers=_headers(settings, representation=True),
            json=payload,
        )
    resp.raise_for_status()
    return resp.json()[0]


async def listar_conversas(user_id: str, settings: Settings) -> list[dict]:
    params = {
        "user_id": f"eq.{user_id}",
        "select": "id,papel,titulo,resumo,created_at,updated_at",
        "order": "updated_at.desc",
    }
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(
            _rest(settings, "chat_conversas"), headers=_headers(settings), params=params
        )
    resp.raise_for_status()
    return resp.json()


async def apagar_conversa(conversa_id: str, settings: Settings) -> None:
    """Apaga a conversa; as mensagens caem por cascata (ON DELETE CASCADE)."""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.delete(
            _rest(settings, "chat_conversas"),
            headers=_headers(settings),
            params={"id": f"eq.{conversa_id}"},
        )
    resp.raise_for_status()


async def buscar_conversa(conversa_id: str, settings: Settings) -> dict | None:
    params = {"id": f"eq.{conversa_id}", "select": "*", "limit": "1"}
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(
            _rest(settings, "chat_conversas"), headers=_headers(settings), params=params
        )
    resp.raise_for_status()
    linhas = resp.json()
    return linhas[0] if linhas else None


async def tocar_conversa(conversa_id: str, settings: Settings) -> None:
    """Atualiza updated_at (não há trigger no banco) para ordenar por recência."""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.patch(
            _rest(settings, "chat_conversas"),
            headers=_headers(settings),
            params={"id": f"eq.{conversa_id}"},
            json={"updated_at": _now_iso()},
        )
    resp.raise_for_status()


# ----------------------------- mensagens -------------------------------------

async def listar_mensagens(
    conversa_id: str, settings: Settings, *, somente_pronta: bool = False, limite: int | None = None
) -> list[dict]:
    params = {
        "conversa_id": f"eq.{conversa_id}",
        "select": "id,conversa_id,autor,conteudo,status,anexos,created_at",
        "order": "created_at.asc",
    }
    if somente_pronta:
        params["status"] = "eq.pronta"
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(
            _rest(settings, "chat_mensagens"), headers=_headers(settings), params=params
        )
    resp.raise_for_status()
    linhas = resp.json()
    if limite is not None and len(linhas) > limite:
        linhas = linhas[-limite:]  # últimas N, preservando a ordem cronológica
    return linhas


async def inserir_mensagem(
    conversa_id: str, autor: str, conteudo: str, status: str, settings: Settings
) -> dict:
    payload = {
        "conversa_id": conversa_id,
        "autor": autor,
        "conteudo": conteudo,
        "status": status,
    }
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(
            _rest(settings, "chat_mensagens"),
            headers=_headers(settings, representation=True),
            json=payload,
        )
    resp.raise_for_status()
    return resp.json()[0]


async def atualizar_mensagem(
    mensagem_id: str, settings: Settings, *, conteudo: str | None = None, status: str | None = None
) -> dict:
    payload: dict = {}
    if conteudo is not None:
        payload["conteudo"] = conteudo
    if status is not None:
        payload["status"] = status
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.patch(
            _rest(settings, "chat_mensagens"),
            headers=_headers(settings, representation=True),
            params={"id": f"eq.{mensagem_id}"},
            json=payload,
        )
    resp.raise_for_status()
    return resp.json()[0]


# --------------------------- playbook_jobs (P1) ------------------------------

_PLAYBOOK_LISTA_COLS = (
    "id,status,fase_atual,origem_arquivo,lead_email,lead_telefone,erro,created_at,updated_at"
)


async def criar_job(
    user_id: str,
    settings: Settings,
    *,
    origem_arquivo: str,
    lead_email: str | None,
    lead_telefone: str | None,
    transcricao: str,
) -> dict:
    payload = {
        "user_id": user_id,
        "status": "pendente",
        "origem_arquivo": origem_arquivo,
        "lead_email": lead_email,
        "lead_telefone": lead_telefone,
        "transcricao": transcricao,
    }
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(
            _rest(settings, "playbook_jobs"),
            headers=_headers(settings, representation=True),
            json=payload,
        )
    resp.raise_for_status()
    return resp.json()[0]


async def listar_jobs(user_id: str, settings: Settings) -> list[dict]:
    params = {
        "user_id": f"eq.{user_id}",
        "select": _PLAYBOOK_LISTA_COLS,
        "order": "updated_at.desc",
    }
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(
            _rest(settings, "playbook_jobs"), headers=_headers(settings), params=params
        )
    resp.raise_for_status()
    return resp.json()


async def buscar_job(job_id: str, settings: Settings) -> dict | None:
    params = {"id": f"eq.{job_id}", "select": "*", "limit": "1"}
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(
            _rest(settings, "playbook_jobs"), headers=_headers(settings), params=params
        )
    resp.raise_for_status()
    linhas = resp.json()
    return linhas[0] if linhas else None


async def atualizar_job(job_id: str, settings: Settings, **campos) -> dict:
    payload = {k: v for k, v in campos.items() if v is not None}
    payload["updated_at"] = _now_iso()
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.patch(
            _rest(settings, "playbook_jobs"),
            headers=_headers(settings, representation=True),
            params={"id": f"eq.{job_id}"},
            json=payload,
        )
    resp.raise_for_status()
    return resp.json()[0]


async def apagar_job(job_id: str, settings: Settings) -> None:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.delete(
            _rest(settings, "playbook_jobs"),
            headers=_headers(settings),
            params={"id": f"eq.{job_id}"},
        )
    resp.raise_for_status()
