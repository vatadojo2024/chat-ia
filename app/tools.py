"""Ferramentas por papel (T-02). Nomes fixos para os prompts funcionarem sem reescrita:

- SDR    -> dados_lead(telefone)                  [55DDDNUMERO]
- CLOSER -> pesquisa_email(url), pesquisa_numero(url), buscar_conversa(chave)

Todas as de CRM chamam clint.* (servidor monta URL + adiciona token).
buscar_conversa só entra se houver REDIS_URL.
"""

from __future__ import annotations

from langchain_core.tools import StructuredTool

from . import clint
from .config import Settings
from .redis_tool import buscar_conversa_redis


def build_tools(papel: str, settings: Settings) -> list[StructuredTool]:
    tools: list[StructuredTool] = []

    if papel == "sdr":
        def dados_lead(telefone: str) -> str:
            return clint.lookup_por_telefone(settings, telefone)

        tools.append(StructuredTool.from_function(
            func=dados_lead,
            name="dados_lead",
            description=(
                "Busca dados do lead no CRM pelo telefone. "
                "Passe o número no formato 55DDDNUMERO (13 dígitos)."
            ),
        ))

    elif papel == "closer":
        def pesquisa_email(url: str) -> str:
            return clint.lookup_por_url_email(settings, url)

        def pesquisa_numero(url: str) -> str:
            return clint.lookup_por_url_telefone(settings, url)

        tools.append(StructuredTool.from_function(
            func=pesquisa_email,
            name="pesquisa_email",
            description=(
                "Busca o registro completo do lead no CRM por email. Recebe a URL "
                "completa do Clint que você montou (com &email=). Retorna os campos do lead."
            ),
        ))
        tools.append(StructuredTool.from_function(
            func=pesquisa_numero,
            name="pesquisa_numero",
            description=(
                "Busca o registro completo do lead no CRM por telefone. Recebe a URL "
                "completa do Clint que você montou (com &phone=). Retorna os campos do lead."
            ),
        ))

        if settings.redis_url:
            def buscar_conversa(chave: str) -> str:
                return buscar_conversa_redis(settings, chave)

            tools.append(StructuredTool.from_function(
                func=buscar_conversa,
                name="buscar_conversa",
                description=(
                    "Histórico bruto da conversa entre closer e lead. "
                    "Recebe a chave no formato <closer>:<55DDDNUMERO>."
                ),
            ))

    return tools
