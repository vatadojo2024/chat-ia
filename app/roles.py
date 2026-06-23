"""Resolução do papel (T-04).

Fonte confirmada no autodiagnóstico: tabela public.users, coluna `role`
(enum public.user_role), casando users.id = sub do JWT. Leitura via service_role,
SOMENTE leitura (RNF-04). Mesma fonte de autorização do Mapa de Calor.
"""

from __future__ import annotations

import httpx

from .config import Settings

PAPEIS_VALIDOS = {"admin", "gestor", "closer", "sdr"}


async def resolve_papel(user_id: str, settings: Settings) -> str | None:
    """Devolve o papel do usuário, ou None se não encontrado.

    Lê public.users via PostgREST com a chave service_role (só GET).
    """
    headers = {
        "apikey": settings.supabase_key,
        "Authorization": f"Bearer {settings.supabase_key}",
        "Accept": "application/json",
    }
    params = {"id": f"eq.{user_id}", "select": "role", "limit": "1"}

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(settings.users_endpoint, headers=headers, params=params)
    resp.raise_for_status()

    rows = resp.json()
    if not rows:
        return None
    return rows[0].get("role")
