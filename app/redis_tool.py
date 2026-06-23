"""Ferramenta `buscar_conversa` (Parte B) — histórico bruto closer↔lead via Redis.

Realidade do Redis (n8n, na VPS): closers no **DB 8**, chave `closer:55DDDNUMERO`.
Endereço `redis://redis:6379` sem senha (host interno do Docker; só resolve na VPS).

- Registrada SÓ SE REDIS_URL estiver no .env (não-negociável A/#5).
- O DB vem de REDIS_CLOSERS_DB (padrão 8), não do `/0` da URL.
- Suporta `rediss://` (TLS). Só LEITURA.
- Erros tratáveis: chave vazia / não achada / Redis inalcançável → texto curto,
  nunca derruba o agente.
"""

from __future__ import annotations

import json
import re
from urllib.parse import urlparse, urlunparse

from .config import Settings

# Ordem de tentativa de prefixo no DB8 (primeiro com dado vence) — B2.
PREFIXOS = ("closer", "aurelio", "marcio", "giba")


def _url_com_db(url: str, db: int) -> str:
    """Força o número do banco no caminho da URL (a URL pode terminar em /0)."""
    p = urlparse(url)
    return urlunparse(p._replace(path=f"/{db}"))


def _numero_da_chave(chave: str) -> str | None:
    """Extrai e normaliza o número (55DDDNUMERO) de uma chave/entrada qualquer."""
    bruto = chave.split(":")[-1] if ":" in chave else chave
    digitos = re.sub(r"\D", "", bruto)
    if not digitos:
        return None
    if digitos.startswith("55") and len(digitos) in (12, 13):
        return digitos
    if len(digitos) in (10, 11):
        return "55" + digitos
    return None


def _texto_legivel(valor) -> str:
    """B3: string pura → JSON (lista/dict de mensagens) → texto legível."""
    if isinstance(valor, list):  # veio de LRANGE
        linhas = [_texto_legivel(v) for v in valor]
        return "\n".join(l for l in linhas if l)
    if isinstance(valor, (dict,)):
        return json.dumps(valor, ensure_ascii=False)
    texto = str(valor)
    try:
        parsed = json.loads(texto)
    except (ValueError, TypeError):
        return texto
    if isinstance(parsed, list):
        partes = []
        for item in parsed:
            if isinstance(item, dict):
                # tenta um formato "papel: conteúdo" se houver chaves óbvias
                papel = item.get("role") or item.get("autor") or item.get("from") or ""
                conteudo = item.get("content") or item.get("text") or item.get("message") or ""
                partes.append(f"{papel}: {conteudo}".strip(": ").strip() if conteudo else json.dumps(item, ensure_ascii=False))
            else:
                partes.append(str(item))
        return "\n".join(p for p in partes if p)
    if isinstance(parsed, dict):
        return json.dumps(parsed, ensure_ascii=False)
    return texto


def _ler_chave(cliente, chave: str):
    """Lê string ou lista; None se não existir. Tolerante a tipo (B3)."""
    tipo = cliente.type(chave)
    if tipo == "none":
        return None
    if tipo == "list":
        return cliente.lrange(chave, 0, -1)
    # string (ou outro) — tenta GET, com fallback p/ list se der WRONGTYPE
    try:
        return cliente.get(chave)
    except Exception:
        try:
            return cliente.lrange(chave, 0, -1)
        except Exception:
            return None


def buscar_conversa_redis(settings: Settings, chave: str) -> str:
    if not settings.redis_url:
        return "Histórico indisponível: Redis não configurado."
    numero = _numero_da_chave(chave or "")
    if not numero:
        return "Não consegui ler um telefone válido. Manda no formato 55DDDNUMERO."
    try:
        import redis  # import tardio: só quando há REDIS_URL
    except ImportError:
        return "Histórico indisponível: pacote redis não instalado."

    url = _url_com_db(settings.redis_url, settings.redis_closers_db)
    try:
        cliente = redis.from_url(url, decode_responses=True)
        for prefixo in PREFIXOS:
            valor = _ler_chave(cliente, f"{prefixo}:{numero}")
            if valor:
                return _texto_legivel(valor)
    except Exception as exc:
        return f"Erro ao consultar o histórico: {exc}"
    return "Sem histórico dessa conversa no momento. Confere o número ou o canal."
