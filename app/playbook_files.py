"""Leitura da transcrição (T-02 / RF-02).

.txt → lê direto; .docx → extrai o texto; outros formatos → erro tratável
pedindo .txt. Recebe os bytes do upload e devolve o texto.
"""

from __future__ import annotations

import io


class FormatoNaoSuportado(ValueError):
    """Formato de arquivo que não sabemos ler. Mensagem pede .txt."""


def _ext(nome: str) -> str:
    return ("." + nome.rsplit(".", 1)[1].lower()) if "." in nome else ""


def extrair_texto(nome_arquivo: str, conteudo: bytes) -> str:
    """Extrai o texto da transcrição a partir do nome + bytes do arquivo."""
    ext = _ext(nome_arquivo or "")

    if ext == ".txt":
        return conteudo.decode("utf-8", errors="replace").strip()

    if ext == ".docx":
        try:
            from docx import Document  # import tardio (dependência só p/ docx)
        except ImportError as exc:  # pragma: no cover
            raise FormatoNaoSuportado(
                "Suporte a .docx indisponível no servidor. Envie a transcrição em .txt."
            ) from exc
        documento = Document(io.BytesIO(conteudo))
        partes = [p.text for p in documento.paragraphs]
        return "\n".join(partes).strip()

    raise FormatoNaoSuportado(
        f"Formato '{ext or '?'}' não suportado. Envie a transcrição em .txt (ou .docx)."
    )
