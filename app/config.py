"""Config do serviço — lê tudo do .env. Nenhum segredo no código (RNF-02).

Variáveis:
  SUPABASE_URL        (obrigatória) — deriva JWKS, issuer e a fonte do papel.
  SUPABASE_KEY        (obrigatória) — service_role; usada só para LER users.role.
  SUPABASE_JWT_SECRET (opcional)    — só se o projeto for HS256 (este é ES256/JWKS).
  AUTH_AUDIENCE       (opcional)    — aud esperado no token (default: authenticated).
  PORT                (opcional)    — porta do uvicorn (default: 8000).
"""

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


class ConfigError(RuntimeError):
    """Erro de configuração: variável de ambiente faltando."""


class Settings:
    def __init__(self) -> None:
        self.supabase_url = (os.getenv("SUPABASE_URL") or "").rstrip("/")
        self.supabase_key = os.getenv("SUPABASE_KEY") or ""
        # Só usado no caminho HS256 (este projeto é ES256/JWKS; fica vazio).
        self.jwt_secret = os.getenv("SUPABASE_JWT_SECRET") or ""
        self.audience = os.getenv("AUTH_AUDIENCE") or "authenticated"
        self.port = int(os.getenv("PORT") or "8000")
        # IA (Etapa 4a). A chave não é exigida no boot: se faltar, a resposta da
        # IA vira status 'erro' (caminho de falha previsto), o serviço continua de pé.
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY") or ""
        self.chat_model = os.getenv("CHAT_MODEL") or "claude-sonnet-4-6"
        # Gerador de playbook: modelo Opus, configurável. NÃO assumir opus-4-7.
        self.playbook_model = os.getenv("PLAYBOOK_MODEL") or "claude-opus-4-8"
        self.history_limit = int(os.getenv("HISTORY_LIMIT") or "20")
        # Limite de rodadas de ferramenta do agente (Etapa 4bc), trava de segurança.
        self.agent_max_iters = int(os.getenv("AGENT_MAX_ITERS") or "6")
        # Clint (CRM, só leitura). Token NUNCA vai ao modelo; o servidor monta a URL.
        self.clint_token = os.getenv("CLINT_TOKEN") or ""
        self.clint_token_header = os.getenv("CLINT_TOKEN_HEADER") or "api-token"
        # CORS: LISTA de origens liberadas para o front (dev + Vercel depois).
        # Vem de CORS_ORIGINS (separada por vírgula); default cobre o dev local.
        # Nunca "*": com Authorization, a origem precisa ser explícita.
        raw_origins = os.getenv("CORS_ORIGINS") or "http://localhost:3000,http://127.0.0.1:3000"
        self.cors_origins = [o.strip() for o in raw_origins.split(",") if o.strip()]
        # Regex que libera QUALQUER porta de localhost/127.0.0.1 em dev (Next em
        # 3000, 3001, ...). Origens de produção ficam na lista acima (sem "*").
        self.cors_origin_regex = (
            os.getenv("CORS_ORIGIN_REGEX") or r"http://(localhost|127\.0\.0\.1)(:\d+)?"
        )
        # buscar_conversa só liga se houver Redis. Sem isso, o closer roda sem ela.
        self.redis_url = os.getenv("REDIS_URL") or ""
        # Closers ficam no DB 8 do Redis do n8n (a URL pode terminar em /0).
        self.redis_closers_db = int(os.getenv("REDIS_CLOSERS_DB") or "8")
        self._validate()

    def _validate(self) -> None:
        missing = [
            name
            for name, value in (
                ("SUPABASE_URL", self.supabase_url),
                ("SUPABASE_KEY", self.supabase_key),
            )
            if not value
        ]
        if missing:
            raise ConfigError(
                "Variáveis faltando no .env: "
                + ", ".join(missing)
                + ". Veja .env.example."
            )

    # --- endpoints derivados da SUPABASE_URL (padrão Supabase, sob /auth/v1) ---
    @property
    def jwks_url(self) -> str:
        return f"{self.supabase_url}/auth/v1/.well-known/jwks.json"

    @property
    def issuer(self) -> str:
        return f"{self.supabase_url}/auth/v1"

    @property
    def users_endpoint(self) -> str:
        return f"{self.supabase_url}/rest/v1/users"

    @property
    def uses_hs256(self) -> bool:
        """HS256 só se um segredo for fornecido; caso contrário, JWKS (ES256)."""
        return bool(self.jwt_secret)


@lru_cache
def get_settings() -> Settings:
    return Settings()
