"""Endpoints do gerador de playbook (T-03) + busca no Clint (T-04) + pipeline (T-06).

Protegidos por login e restritos ao dono no código (o service_role ignora a RLS).
Fluxo: POST cria o job e agenda a tarefa em segundo plano; a tarefa busca o lead
no Clint, roda os 3 agentes Opus e grava o resultado.
"""

from __future__ import annotations

import asyncio

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Path,
    Response,
    UploadFile,
    status,
)

from . import clint
from . import repository as repo
from .auth import Identity, get_identity
from .config import Settings, get_settings
from .playbook_ai import gerar_playbook
from .playbook_files import FormatoNaoSuportado, extrair_texto

router = APIRouter()


async def _job_do_dono(job_id: str, identity: Identity, settings: Settings) -> dict:
    job = await repo.buscar_job(job_id, settings)
    if job is None or job.get("user_id") != identity.user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Playbook não encontrado.")
    return job


# ------------------------------- DADOS DO LEAD -------------------------------

async def montar_dados_lead(
    settings: Settings, email: str | None, telefone: str | None
) -> str:
    """Busca o lead no Clint e formata o bloco DADOS DO LEAD. Resiliente: erro/não
    achou → 'n/i' (o playbook ainda é gerado a partir da transcrição)."""
    try:
        campos = await asyncio.to_thread(
            clint.buscar_campos_lead, settings, email=email, telefone=telefone
        )
    except Exception:
        return "n/i"
    if not campos:
        return "n/i"
    linhas = [f"- {k}: {v}" for k, v in campos.items() if v not in (None, "", [], {})]
    if not linhas:
        return "n/i"
    return "DADOS DO LEAD (CRM Clint)\n" + "\n".join(linhas)


# --------------------------------- endpoints ---------------------------------

@router.post("/playbooks", status_code=status.HTTP_201_CREATED)
async def criar_playbook(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    lead_email: str | None = Form(None),
    lead_telefone: str | None = Form(None),
    identity: Identity = Depends(get_identity),
    settings: Settings = Depends(get_settings),
) -> dict:
    email = (lead_email or "").strip() or None
    telefone = (lead_telefone or "").strip() or None
    if not email and not telefone:
        raise HTTPException(status_code=400, detail="Informe e-mail e/ou telefone do lead.")

    conteudo = await file.read()
    try:
        transcricao = extrair_texto(file.filename or "", conteudo)
    except FormatoNaoSuportado as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not transcricao:
        raise HTTPException(status_code=400, detail="A transcrição está vazia.")

    job = await repo.criar_job(
        identity.user_id,
        settings,
        origem_arquivo=file.filename or "transcricao",
        lead_email=email,
        lead_telefone=telefone,
        transcricao=transcricao,
    )
    background_tasks.add_task(processar_playbook, job["id"], settings)
    return {"id": job["id"], "status": job["status"]}


@router.get("/playbooks")
async def listar_playbooks(
    identity: Identity = Depends(get_identity),
    settings: Settings = Depends(get_settings),
) -> list[dict]:
    return await repo.listar_jobs(identity.user_id, settings)


@router.get("/playbooks/{job_id}")
async def ler_playbook(
    job_id: str = Path(...),
    identity: Identity = Depends(get_identity),
    settings: Settings = Depends(get_settings),
) -> dict:
    job = await _job_do_dono(job_id, identity, settings)
    # devolve status + fase + resultado (e os campos úteis para a tela)
    return {
        "id": job["id"],
        "status": job["status"],
        "fase_atual": job.get("fase_atual"),
        "origem_arquivo": job.get("origem_arquivo"),
        "lead_email": job.get("lead_email"),
        "lead_telefone": job.get("lead_telefone"),
        "dados_lead": job.get("dados_lead"),
        "resultado": job.get("resultado"),
        "erro": job.get("erro"),
        "created_at": job.get("created_at"),
        "updated_at": job.get("updated_at"),
    }


@router.delete("/playbooks/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def apagar_playbook(
    job_id: str = Path(...),
    identity: Identity = Depends(get_identity),
    settings: Settings = Depends(get_settings),
) -> Response:
    await _job_do_dono(job_id, identity, settings)
    await repo.apagar_job(job_id, settings)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ----------------------- tarefa em segundo plano (T-06) ----------------------

async def processar_playbook(job_id: str, settings: Settings) -> None:
    """Busca o lead no Clint e roda o pipeline de 3 agentes Opus, atualizando o job."""
    try:
        job = await repo.buscar_job(job_id, settings)
        if job is None:
            return
        await repo.atualizar_job(job_id, settings, status="processando")

        dados_lead = await montar_dados_lead(
            settings, job.get("lead_email"), job.get("lead_telefone")
        )
        await repo.atualizar_job(job_id, settings, dados_lead=dados_lead)

        # Atualiza fase_atual a partir da thread do pipeline, sem travar o loop.
        loop = asyncio.get_running_loop()

        def on_fase(n: int) -> None:
            asyncio.run_coroutine_threadsafe(
                repo.atualizar_job(job_id, settings, fase_atual=n), loop
            )

        res = await asyncio.to_thread(
            gerar_playbook, job["transcricao"], dados_lead, settings, on_fase
        )

        await repo.atualizar_job(
            job_id,
            settings,
            status="pronto",
            fase_atual=3,
            resultado=res.resultado,
            decisoes_c1=res.decisoes_c1,
            decisoes_c2=res.decisoes_c2,
            decisoes_c3=res.decisoes_c3,
        )
    except Exception as exc:
        await repo.atualizar_job(job_id, settings, status="erro", erro=str(exc)[:300])
