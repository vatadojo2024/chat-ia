"""Endpoints de chat (T-03, T-04) + tarefa em segundo plano (T-05).

Todos protegidos por login (Etapa 3) e restritos ao dono no código (RF-07):
como o serviço usa service_role (ignora RLS), checamos SEMPRE que a conversa é
do usuário do login antes de ler/gravar.
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Path, Response, status
from pydantic import BaseModel, field_validator

from . import agentes
from . import repository as repo
from .ai import montar_turnos, responder_com_agente
from .auth import Identity, get_identity
from .config import Settings, get_settings
from .roles import resolve_papel

logger = logging.getLogger(__name__)

router = APIRouter()


class EnviarMensagem(BaseModel):
    conteudo: str

    @field_validator("conteudo")
    @classmethod
    def _nao_vazio(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("conteudo não pode ser vazio")
        return v


async def _conversa_do_dono(
    conversa_id: str, identity: Identity, settings: Settings
) -> dict:
    """Carrega a conversa e confirma que pertence ao usuário do login (senão 404)."""
    conversa = await repo.buscar_conversa(conversa_id, settings)
    if conversa is None or conversa.get("user_id") != identity.user_id:
        # 404 para não revelar a existência de conversas de outros.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversa não encontrada.")
    return conversa


# --------------------------------- conversas ---------------------------------

@router.post("/conversas", status_code=status.HTTP_201_CREATED)
async def criar_conversa(
    identity: Identity = Depends(get_identity),
    settings: Settings = Depends(get_settings),
) -> dict:
    papel = await resolve_papel(identity.user_id, settings)
    if not papel:
        raise HTTPException(status_code=400, detail="Papel do usuário não resolvido.")
    return await repo.criar_conversa(identity.user_id, papel, settings)


@router.get("/conversas")
async def listar_conversas(
    identity: Identity = Depends(get_identity),
    settings: Settings = Depends(get_settings),
) -> list[dict]:
    return await repo.listar_conversas(identity.user_id, settings)


@router.delete("/conversas/{conversa_id}", status_code=status.HTTP_204_NO_CONTENT)
async def apagar_conversa(
    conversa_id: str = Path(...),
    identity: Identity = Depends(get_identity),
    settings: Settings = Depends(get_settings),
) -> Response:
    """Apaga a conversa do usuário (mensagens caem por cascata). Checa dono (404)."""
    await _conversa_do_dono(conversa_id, identity, settings)
    await repo.apagar_conversa(conversa_id, settings)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --------------------------------- mensagens ---------------------------------

@router.get("/conversas/{conversa_id}/mensagens")
async def listar_mensagens(
    conversa_id: str = Path(...),
    identity: Identity = Depends(get_identity),
    settings: Settings = Depends(get_settings),
) -> list[dict]:
    await _conversa_do_dono(conversa_id, identity, settings)
    return await repo.listar_mensagens(conversa_id, settings)


@router.post("/conversas/{conversa_id}/mensagens", status_code=status.HTTP_201_CREATED)
async def enviar_mensagem(
    corpo: EnviarMensagem,
    background_tasks: BackgroundTasks,
    conversa_id: str = Path(...),
    identity: Identity = Depends(get_identity),
    settings: Settings = Depends(get_settings),
) -> dict:
    conversa = await _conversa_do_dono(conversa_id, identity, settings)

    # 1) mensagem do usuário, já pronta
    msg_usuario = await repo.inserir_mensagem(
        conversa_id, "usuario", corpo.conteudo, "pronta", settings
    )
    # 2) resposta da IA, pendente (conteúdo vazio por enquanto)
    msg_ia = await repo.inserir_mensagem(conversa_id, "ia", "", "pendente", settings)

    # 3) agenda o processamento e responde NA HORA (sem esperar a IA).
    # O AGENTE é resolvido por e-mail (mapa em app/agentes.py); senão cai no papel.
    agente = agentes.resolver_agente(identity.email, conversa["papel"])
    background_tasks.add_task(
        processar_resposta_ia, conversa_id, msg_ia["id"], agente, settings
    )
    return {"mensagem_usuario": msg_usuario, "mensagem_ia": msg_ia}


# ----------------------- tarefa em segundo plano (T-05) ----------------------

async def processar_resposta_ia(
    conversa_id: str, msg_ia_id: str, agente: str, settings: Settings
) -> None:
    """Monta o prompt (system do agente + histórico), chama a IA e atualiza a msg-IA."""
    try:
        historico = await repo.listar_mensagens(
            conversa_id, settings, somente_pronta=True, limite=settings.history_limit
        )
        system_prompt = agentes.load_prompt(agente)
        max_tokens = agentes.max_tokens_do_agente(agente)
        turnos = montar_turnos(historico)
        # agente (tool-calling) é bloqueante → roda em thread para não travar o loop (polling segue).
        texto = await asyncio.to_thread(
            responder_com_agente, system_prompt, turnos, agente, settings, max_tokens
        )
        await repo.atualizar_mensagem(msg_ia_id, settings, conteudo=texto, status="pronta")
    except Exception:
        # Loga o traceback no stdout (docker logs) ANTES de gravar o status.
        logger.exception(
            "Falha ao processar resposta da IA (conversa=%s msg=%s agente=%s)",
            conversa_id, msg_ia_id, agente,
        )
        # Qualquer falha (IA, prompt, rede) marca a mensagem como erro (RF-03).
        await repo.atualizar_mensagem(msg_ia_id, settings, status="erro")
    finally:
        # Recência: atualizar updated_at mesmo em erro (houve atividade na conversa).
        try:
            await repo.tocar_conversa(conversa_id, settings)
        except Exception:
            pass
