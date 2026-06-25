"""Localização dos arquivos de prompt.

A seleção de prompt por agente vive em `app/agentes.py` (ponto único). Aqui ficam
apenas o diretório dos prompts e o erro compartilhado.
"""

from __future__ import annotations

from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


class PromptIndisponivel(RuntimeError):
    """Não há prompt configurado/encontrado para o agente pedido."""
