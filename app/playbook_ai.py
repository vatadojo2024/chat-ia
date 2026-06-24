"""Camada Opus (T-05) + pipeline de 3 agentes (T-06).

- Opus via PLAYBOOK_MODEL (padrão claude-opus-4-8).
- 3 agentes em fila: Diagnóstico → Estratégia → Execução.
- A mensagem (input) de cada agente traz seções rotuladas EXATAMENTE como os
  prompts esperam (seção 13 de cada). As decisões [DECISOES_Cx]…[/DECISOES_Cx]
  são extraídas por regex e injetadas no próximo.

Esta camada NÃO toca o banco — recebe transcrição + dados_lead e devolve o
resultado + as 3 decisões. O lifecycle (status/fase) vive no router.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from .config import Settings
from .prompts import PROMPTS_DIR

# Rótulos das seções da mensagem (exatamente como os prompts esperam).
L_DADOS = "DADOS DO LEAD"
L_TRANSCRICAO = "TRANSCRIÇÃO DA CALL 1"
L_DEC_C1 = "DECISÕES DA CHAMADA 1 (DIAGNÓSTICO)"
L_DEC_C2 = "DECISÕES DA CHAMADA 2 (ESTRATÉGIA)"


def _carregar_prompt(nome_arquivo: str) -> str:
    return (PROMPTS_DIR / nome_arquivo).read_text(encoding="utf-8")


def _texto(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            b if isinstance(b, str) else b.get("text", "")
            for b in content
            if isinstance(b, (str, dict))
        )
    return str(content)


def _chamar_opus(system_prompt: str, mensagem: str, settings: Settings) -> str:
    """Uma chamada ao Opus: system (prompt do agente) + mensagem (input). Devolve texto."""
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY ausente no .env.")
    # temperature é deprecado no opus-4-8 → não enviar.
    modelo = ChatAnthropic(
        model=settings.playbook_model,
        api_key=settings.anthropic_api_key,
        max_tokens=8000,
        timeout=600,
    )
    resposta = modelo.invoke(
        [SystemMessage(content=system_prompt), HumanMessage(content=mensagem)]
    )
    texto = _texto(resposta.content).strip()
    if not texto:
        raise RuntimeError("A IA devolveu resposta vazia.")
    return texto


def extrair_decisoes(saida: str, n: int) -> str:
    """Extrai o bloco [DECISOES_Cn]…[/DECISOES_Cn]. Se faltar, devolve a saída inteira
    (resiliência: o próximo agente ainda recebe contexto)."""
    padrao = re.compile(rf"\[DECISOES_C{n}\](.*?)\[/DECISOES_C{n}\]", re.DOTALL)
    m = padrao.search(saida)
    if m:
        return f"[DECISOES_C{n}]{m.group(1)}[/DECISOES_C{n}]"
    return saida.strip()


def _secao(rotulo: str, corpo: str) -> str:
    return f"{rotulo}\n{corpo or 'n/i'}"


def _msg_diagnostico(dados_lead: str, transcricao: str) -> str:
    return "\n\n".join([
        _secao(L_DADOS, dados_lead),
        _secao(L_TRANSCRICAO, transcricao),
    ])


def _msg_estrategia(decisoes_c1: str, transcricao: str, dados_lead: str) -> str:
    return "\n\n".join([
        _secao(L_DEC_C1, decisoes_c1),
        _secao(L_TRANSCRICAO, transcricao),
        _secao(L_DADOS, dados_lead),
    ])


def _msg_execucao(decisoes_c1: str, decisoes_c2: str, dados_lead: str) -> str:
    return "\n\n".join([
        _secao(L_DEC_C1, decisoes_c1),
        _secao(L_DEC_C2, decisoes_c2),
        _secao(L_DADOS, dados_lead),
    ])


@dataclass
class ResultadoPlaybook:
    resultado: str
    decisoes_c1: str
    decisoes_c2: str
    decisoes_c3: str


def gerar_playbook(
    transcricao: str,
    dados_lead: str,
    settings: Settings,
    on_fase=None,
) -> ResultadoPlaybook:
    """Roda os 3 agentes em fila e devolve o playbook montado + as decisões.

    on_fase(n) é chamado antes de cada fase (1/2/3) para o lifecycle atualizar
    fase_atual. Esta função não toca o banco.
    """
    def _fase(n: int) -> None:
        if on_fase:
            on_fase(n)

    # Fase 1 — Diagnóstico (blocos 1–8)
    _fase(1)
    saida_c1 = _chamar_opus(
        _carregar_prompt("playbook_diagnostico.md"),
        _msg_diagnostico(dados_lead, transcricao),
        settings,
    )
    dec_c1 = extrair_decisoes(saida_c1, 1)

    # Fase 2 — Estratégia (blocos 9–15)
    _fase(2)
    saida_c2 = _chamar_opus(
        _carregar_prompt("playbook_estrategia.md"),
        _msg_estrategia(dec_c1, transcricao, dados_lead),
        settings,
    )
    dec_c2 = extrair_decisoes(saida_c2, 2)

    # Fase 3 — Execução (blocos 16–21)
    _fase(3)
    saida_c3 = _chamar_opus(
        _carregar_prompt("playbook_execucao.md"),
        _msg_execucao(dec_c1, dec_c2, dados_lead),
        settings,
    )
    dec_c3 = extrair_decisoes(saida_c3, 3)

    # Montagem final: as 3 fases concatenadas.
    resultado = "\n\n".join([saida_c1, saida_c2, saida_c3])
    return ResultadoPlaybook(resultado, dec_c1, dec_c2, dec_c3)
