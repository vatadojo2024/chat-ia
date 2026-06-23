"""Camada de auth (T-03): valida o JWT do Supabase e devolve a identidade.

Confere assinatura, expiração (exp) e emissor (iss). Método detectado no
autodiagnóstico: ES256 via JWKS (assimétrico). Mantém também o caminho HS256
caso o projeto use segredo compartilhado (ativado por SUPABASE_JWT_SECRET).

Token ausente/inválido/expirado -> 401.
"""

from __future__ import annotations

from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, Request, status
from jwt import PyJWKClient

from .config import Settings, get_settings


@dataclass
class Identity:
    user_id: str
    email: str | None


# PyJWKClient já faz cache em memória das chaves públicas (design seção 4).
_jwks_client: PyJWKClient | None = None


def _jwks(settings: Settings) -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = PyJWKClient(settings.jwks_url)
    return _jwks_client


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _extract_bearer(request: Request) -> str:
    header = request.headers.get("Authorization")
    if not header or not header.lower().startswith("bearer "):
        raise _unauthorized("Token ausente.")
    token = header.split(" ", 1)[1].strip()
    if not token:
        raise _unauthorized("Token ausente.")
    return token


def _decode(token: str, settings: Settings) -> dict:
    common = dict(
        issuer=settings.issuer,
        audience=settings.audience,
        options={"require": ["exp", "iss", "sub"]},
    )
    if settings.uses_hs256:
        return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"], **common)
    signing_key = _jwks(settings).get_signing_key_from_jwt(token)
    return jwt.decode(token, signing_key.key, algorithms=["ES256"], **common)


def get_identity(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> Identity:
    token = _extract_bearer(request)
    try:
        payload = _decode(token, settings)
    except jwt.PyJWTError as exc:
        raise _unauthorized(f"Token inválido: {exc}") from exc

    sub = payload.get("sub")
    if not sub:
        raise _unauthorized("Token sem 'sub'.")
    return Identity(user_id=sub, email=payload.get("email"))
