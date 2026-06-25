"""Ferramentas por AGENTE. Nomes fixos para os prompts funcionarem sem reescrita:

- sdr    -> dados_lead(telefone)                  [55DDDNUMERO]
- closer -> pesquisa_email(url), pesquisa_numero(url), buscar_conversa(chave)
- vata   -> buscar_lead(email?, telefone?)        [CRM Clint, normaliza no servidor]

Todas as de CRM chamam clint.* (servidor monta URL + adiciona token).
buscar_conversa só entra se houver REDIS_URL.
"""

from __future__ import annotations

from langchain_core.tools import StructuredTool

from . import clint
from .config import Settings
from .redis_tool import buscar_conversa_redis


def build_tools(agente: str, settings: Settings) -> list[StructuredTool]:
    tools: list[StructuredTool] = []

    if agente == "vata":
        def buscar_lead(email: str | None = None, telefone: str | None = None) -> str:
            return clint.buscar_lead_resultado(settings, email=email, telefone=telefone)

        tools.append(StructuredTool.from_function(
            func=buscar_lead,
            name="buscar_lead",
            description=(
                "Busca o registro do lead no CRM Clint. "
                "Forneça email OU telefone (pelo menos um)."
            ),
        ))

    elif agente == "sdr":
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

    elif agente == "closer":
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
