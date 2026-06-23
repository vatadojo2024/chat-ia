"""Seleção do prompt por papel.

Mapa papel -> arquivo de prompt. `sdr` (Hana) e `closer` (Mestre do Dojo, prompt
do Vata) estão populados; admin/gestor ficam para etapas futuras.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"

# Chaves previstas. Etapa 4bc populou closer (prompt do Vata).
PAPEL_TO_FILE: dict[str, str | None] = {
    "sdr": "sdr.md",
    "closer": "closer.md",
    "admin": None,
    "gestor": None,
}


class PromptIndisponivel(RuntimeError):
    """Não há prompt populado para o papel pedido nesta etapa."""


@lru_cache
def load_system_prompt(papel: str) -> str:
    """Devolve o texto do system prompt para o papel, ou levanta PromptIndisponivel."""
    nome_arquivo = PAPEL_TO_FILE.get(papel)
    if not nome_arquivo:
        raise PromptIndisponivel(
            f"Papel '{papel}' não tem prompt nesta etapa (só 'sdr' está populado)."
        )
    caminho = PROMPTS_DIR / nome_arquivo
    if not caminho.exists():
        raise PromptIndisponivel(f"Arquivo de prompt não encontrado: {caminho}")
    return caminho.read_text(encoding="utf-8")
