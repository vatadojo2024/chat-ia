"""Conceito de AGENTE — separado do papel.

Ponto ÚNICO que decide, por agente: prompt + ferramentas (via build_tools) +
max_tokens. O agente é resolvido por e-mail (mapa abaixo); se o e-mail não estiver
mapeado, cai no comportamento atual por papel (sdr→Hana, closer→Mestre).

Para adicionar Cindy/Jonas no futuro: basta estender EMAIL_TO_AGENTE e AGENTES —
sem refatorar o chat.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from .prompts import PROMPTS_DIR, PromptIndisponivel

# e-mail (minúsculo) -> agente. Estender aqui no futuro (cindy/jonas).
EMAIL_TO_AGENTE: dict[str, str] = {
    "contato@vatadojo.com.br": "vata",
}

MAX_TOKENS_PADRAO = 1500       # turno normal de chat (Hana/Mestre, como hoje)
MAX_TOKENS_VATA = 8000         # generoso: cabe ao menos o núcleo do playbook inline


@dataclass(frozen=True)
class AgenteConfig:
    prompt_file: str
    max_tokens: int


# agente -> config. sdr/closer == papéis atuais (comportamento idêntico ao de hoje).
AGENTES: dict[str, AgenteConfig] = {
    "vata": AgenteConfig("vata.md", MAX_TOKENS_VATA),
    "sdr": AgenteConfig("sdr.md", MAX_TOKENS_PADRAO),
    "closer": AgenteConfig("closer.md", MAX_TOKENS_PADRAO),
}


def resolver_agente(email: str | None, papel: str | None) -> str:
    """E-mail mapeado vence; senão cai no papel (sdr/closer = comportamento atual)."""
    if email and email.strip().lower() in EMAIL_TO_AGENTE:
        return EMAIL_TO_AGENTE[email.strip().lower()]
    return papel or ""


def max_tokens_do_agente(agente: str) -> int:
    cfg = AGENTES.get(agente)
    return cfg.max_tokens if cfg else MAX_TOKENS_PADRAO


@lru_cache
def load_prompt(agente: str) -> str:
    """Carrega o system prompt do agente. Levanta PromptIndisponivel se não houver."""
    cfg = AGENTES.get(agente)
    if not cfg:
        raise PromptIndisponivel(f"Agente '{agente}' não tem prompt configurado.")
    caminho = PROMPTS_DIR / cfg.prompt_file
    if not caminho.exists():
        raise PromptIndisponivel(f"Arquivo de prompt não encontrado: {caminho}")
    return caminho.read_text(encoding="utf-8")
