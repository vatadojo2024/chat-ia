"""Ferramenta de leitura do CRM Clint (T-01). SÓ LEITURA.

Regras (não-negociáveis #1 e #9):
- A URL real é montada NO SERVIDOR (base + params fixos); o token vem do .env
  (CLINT_TOKEN) e é adicionado no header. O modelo NUNCA recebe o token.
- SDR (`dados_lead`) passa só o número 55DDDNUMERO.
- CLOSER (`pesquisa_email`/`pesquisa_numero`) passa a URL completa que ele montou;
  aqui extraímos o email/telefone dela e refazemos a chamada no servidor.
- Erro / não encontrado -> string curta e tratável (não derruba o agente).
"""

from __future__ import annotations

import json
import re
from urllib.parse import parse_qs, urlparse

import httpx

from .config import Settings

CLINT_BASE = "https://api.clint.digital/v1/contacts"
PARAMS_FIXOS = {"limit": "200", "offset": "0", "page": "1"}
_TIMEOUT = 20.0


def normalizar_telefone(bruto: str) -> str | None:
    """Normaliza para 13 dígitos com 55 na frente (55DDDNUMERO). None se inválido."""
    if not bruto:
        return None
    digitos = re.sub(r"\D", "", bruto)
    if not digitos:
        return None
    if digitos.startswith("55") and len(digitos) == 13:
        return digitos
    if len(digitos) in (10, 11):  # DDD + número, sem o 55
        return "55" + digitos
    if digitos.startswith("55") and len(digitos) in (12, 13):
        return digitos
    return None


def _valor_da_url(url: str, chave: str) -> str | None:
    """Extrai ?chave= de uma URL (ou aceita o valor cru, se não vier URL)."""
    if "=" in url or "?" in url or url.startswith("http"):
        qs = parse_qs(urlparse(url).query)
        if chave in qs and qs[chave]:
            return qs[chave][0]
    return None


def _buscar_campos(settings: Settings, params: dict) -> dict | None:
    """Retorna os campos do lead (data[0].fields) ou None. Levanta em erro de rede/http."""
    headers = {settings.clint_token_header: settings.clint_token, "Accept": "application/json"}
    with httpx.Client(timeout=_TIMEOUT) as client:
        resp = client.get(CLINT_BASE, params={**PARAMS_FIXOS, **params}, headers=headers)
    resp.raise_for_status()
    dados = resp.json().get("data", [])
    if not dados:
        return None
    # data[0].fields.* (mesmos nomes do backfill, sem prefixo contact_)
    return dados[0].get("fields", dados[0])


def buscar_campos_lead(
    settings: Settings, *, email: str | None = None, telefone: str | None = None
) -> dict | None:
    """Busca os campos do lead por email e/ou telefone (reaproveitado no playbook).

    Tenta email primeiro, depois telefone. Levanta em erro de rede/http/token;
    devolve None se não encontrar. O chamador decide a resiliência (n/i).
    """
    if not settings.clint_token:
        raise RuntimeError("Token do Clint não configurado no servidor.")
    if email:
        campos = _buscar_campos(settings, {"email": email.strip()})
        if campos:
            return campos
    if telefone:
        tel = normalizar_telefone(telefone)
        if tel:
            return _buscar_campos(settings, {"phone": tel})
    return None


def buscar_lead_resultado(
    settings: Settings, *, email: str | None = None, telefone: str | None = None
) -> str:
    """Resultado da tool `buscar_lead` (agente do Vata).

    Reusa buscar_campos_lead (normaliza telefone internamente, prefere email).
    Encontrado → JSON dos campos; não encontrado → {"encontrado": false};
    erro/rede → texto curto tratável (não derruba a resposta).
    """
    if not (email or telefone):
        return json.dumps({"erro": "Forneça email ou telefone."}, ensure_ascii=False)
    try:
        campos = buscar_campos_lead(settings, email=email, telefone=telefone)
    except Exception as exc:  # token/rede/http — tratável
        return f"Erro ao consultar o CRM: {exc}"
    if not campos:
        return json.dumps({"encontrado": False}, ensure_ascii=False)
    return json.dumps(campos, ensure_ascii=False)


def _consultar(settings: Settings, params: dict) -> str:
    if not settings.clint_token:
        return "CRM indisponível: token do Clint não configurado no servidor."
    try:
        campos = _buscar_campos(settings, params)
    except Exception as exc:  # rede, http, json — tudo tratável
        return f"Erro ao consultar o CRM: {exc}"
    if campos is None:
        return "Lead não encontrado no CRM com esse dado."
    return json.dumps(campos, ensure_ascii=False)


# ----------------------------- entradas das tools ----------------------------

def lookup_por_telefone(settings: Settings, telefone: str) -> str:
    """SDR: recebe 55DDDNUMERO (ou normalizável)."""
    tel = normalizar_telefone(telefone)
    if not tel:
        return "Telefone inválido. Envie no formato 55DDDNUMERO."
    return _consultar(settings, {"phone": tel})


def lookup_por_url_email(settings: Settings, url: str) -> str:
    """CLOSER: recebe a URL do Clint com &email= (ou o email cru)."""
    email = _valor_da_url(url, "email") or (url.strip() if "@" in url else None)
    if not email:
        return "Não consegui ler o email da URL enviada."
    return _consultar(settings, {"email": email})


def lookup_por_url_telefone(settings: Settings, url: str) -> str:
    """CLOSER: recebe a URL do Clint com &phone= (ou o telefone cru)."""
    bruto = _valor_da_url(url, "phone") or url
    tel = normalizar_telefone(bruto)
    if not tel:
        return "Não consegui ler um telefone válido da URL enviada."
    return _consultar(settings, {"phone": tel})
