"""Camada de IA (RNF-01 / T-03): agente LangChain (tool-calling) com claude-sonnet-4-6.

A partir da Etapa 4bc a chamada simples vira um AGENTE: o modelo decide quando
chamar as ferramentas do papel (Clint / histórico). Mantém system do papel +
histórico (memória). É síncrono por dentro (roda em thread na tarefa de fundo).
Sem ferramenta registrada, o agente é só uma chamada de chat (igual à 4a).
"""

from __future__ import annotations

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from .config import Settings
from .tools import build_tools


class IAIndisponivel(RuntimeError):
    """Falta configuração para chamar a IA (ex.: ANTHROPIC_API_KEY)."""


def montar_turnos(historico: list[dict]) -> list[BaseMessage]:
    """Converte mensagens do banco em turnos: usuario->Human, ia->AI."""
    turnos: list[BaseMessage] = []
    for msg in historico:
        autor = msg.get("autor")
        conteudo = msg.get("conteudo") or ""
        if autor == "usuario":
            turnos.append(HumanMessage(content=conteudo))
        elif autor == "ia":
            turnos.append(AIMessage(content=conteudo))
    return turnos


def _texto(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        partes = []
        for bloco in content:
            if isinstance(bloco, str):
                partes.append(bloco)
            elif isinstance(bloco, dict) and bloco.get("type") == "text":
                partes.append(bloco.get("text", ""))
        return "".join(partes)
    return str(content)


def responder_com_agente(
    system_prompt: str,
    turnos: list[BaseMessage],
    agente: str,
    settings: Settings,
    max_tokens: int = 1500,
) -> str:
    """Roda o loop de tool-calling e devolve o texto final da resposta.

    As ferramentas e o teto de saída são decididos por AGENTE (ver app/agentes.py).
    Os blocos tool_use/tool_result vivem só aqui — não são persistidos (RNF-01).
    """
    if not settings.anthropic_api_key:
        raise IAIndisponivel("ANTHROPIC_API_KEY ausente no .env.")

    modelo = ChatAnthropic(
        model=settings.chat_model,
        api_key=settings.anthropic_api_key,
        temperature=0.7,
        max_tokens=max_tokens,
        timeout=180,
    )
    ferramentas = build_tools(agente, settings)
    por_nome = {t.name: t for t in ferramentas}
    modelo_exec = modelo.bind_tools(ferramentas) if ferramentas else modelo

    mensagens: list[BaseMessage] = [SystemMessage(content=system_prompt), *turnos]

    for _ in range(settings.agent_max_iters):
        ai_msg = modelo_exec.invoke(mensagens)
        mensagens.append(ai_msg)
        chamadas = getattr(ai_msg, "tool_calls", None) or []
        if not chamadas:
            texto = _texto(ai_msg.content).strip()
            if not texto:
                raise IAIndisponivel("A IA devolveu resposta vazia.")
            return texto
        # executa cada ferramenta pedida e devolve o resultado ao modelo
        for chamada in chamadas:
            tool = por_nome.get(chamada["name"])
            try:
                resultado = (
                    tool.invoke(chamada["args"])
                    if tool is not None
                    else f"Ferramenta '{chamada['name']}' indisponível."
                )
            except Exception as exc:
                resultado = f"Erro ao executar a ferramenta: {exc}"
            mensagens.append(
                ToolMessage(content=str(resultado), tool_call_id=chamada["id"])
            )

    # estourou o limite de rodadas: devolve o melhor texto que houver
    texto = _texto(mensagens[-1].content).strip()
    return texto or "Não consegui concluir a resposta agora."
