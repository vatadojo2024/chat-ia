# Etapa 3 — Esqueleto do serviço Python — Design

**Projeto:** Chat IA-Guia — **backend** (projeto novo)
**Etapa:** 3 de 9 (Fase C — Esqueleto do cérebro)
**Versão:** 1.0
**Método:** SDD — deriva do `requisitos.md` (mesma pasta) e orienta o `tasks.md`.

---

## 1. Visão geral

Um serviço **FastAPI** pequeno que roda **local**. Duas rotas: `/health` (pública) e `/me` (protegida). Uma camada de autenticação valida o JWT do Supabase (pelas chaves públicas/JWKS) e resolve o papel do usuário. Nenhuma IA, nenhum acesso às tabelas de chat.

O foco da etapa é o **pipeline de login funcionando**: o serviço recebe o crachá, confirma que é válido, e diz "você é fulano, papel X".

---

## 2. Onde mora no projeto

Projeto novo do chat (mesma pasta/repo da migration da Etapa 2). Estrutura mínima de serviço Python (app + config + camada de auth). Roda com um servidor local (uvicorn). Sem Docker nesta etapa.

---

## 3. Estrutura mínima

- **App FastAPI** — ponto de entrada do serviço.
- **Config** — lê o `.env`.
- **Rota `/health`** (pública) → 200 `{"status":"ok"}`.
- **Camada de auth** (dependência reutilizável) — pega o token do header, valida, devolve a identidade.
- **Resolução de papel** — descobre o papel do usuário identificado.
- **Rota `/me`** (protegida) → `{user_id, email, papel}`.

---

## 4. Validação do JWT

- O front manda o JWT do Supabase no header `Authorization: Bearer <token>`.
- O serviço valida: **assinatura** (chaves públicas/JWKS do Supabase), **expiração** (`exp`) e **emissor** (`iss`).
- **JWKS:** buscar as chaves públicas no endpoint de Auth do Supabase derivado de `SUPABASE_URL` (padrão Supabase, sob `/auth/v1`), com cache em memória.
- **Confirmar o método de assinatura do projeto** na execução: **assimétrico (JWKS, ES256)** — provável, é o que o Mapa de Calor usa — vs **segredo compartilhado (HS256)**. Dá para detectar consultando o endpoint de chaves: se devolve chaves públicas, é assimétrico; se não, é HS256 (validar com o segredo do `.env`). A validação segue o método real.
- **Claims usados:** `sub` (id do usuário) e `email`. (Atenção: o `role` que vem no token padrão é o papel do Postgres — geralmente `authenticated` —, **não** o papel do app.)

---

## 5. Resolução do papel

- O papel do app (`admin`/`gestor`/`closer`/`sdr`) **não** é um claim padrão do Supabase.
- **Resolver lendo a tabela de equipe/usuários** na MESMA Supabase, casando pelo id do usuário (auth user id = `sub`). **Confirmar a tabela e a coluna** na execução (a mesma fonte que o Mapa de Calor usa para autorização) — inspecionar o schema do Supabase para achar onde os papéis vivem.
- **Alternativa:** se o projeto já colocar o papel no token (em `app_metadata`), usar de lá e evitar ler o banco. Confirmar na execução o que existe.
- A leitura usa a chave **service_role** (a mesma do backfill), **somente leitura**.

---

## 6. Config (`.env`)

- `SUPABASE_URL` — para derivar o endpoint de chaves (JWKS) e/ou a fonte do papel.
- A forma de validação: JWKS automático a partir da URL; ou, se o projeto for HS256, o segredo do JWT.
- Chave **service_role** do Supabase — se for ler a tabela de usuários para o papel.
- Porta do serviço (ex.: 8000).

---

## 7. Respostas e erros

- `/health`: sempre 200 `{"status":"ok"}`, sem login.
- `/me` sem token, ou com token inválido/expirado: **401**.
- `/me` com token válido: **200** `{user_id, email, papel}`.

---

## 8. O que NÃO fazer

- NÃO chamar IA, NÃO usar prompts, NÃO responder chat.
- NÃO acessar `chat_conversas`/`chat_mensagens`.
- NÃO escrever no banco (no máximo LER a tabela de usuários para o papel).
- NÃO dockerizar nem subir na VPS (Etapa 9).
- NÃO ligar o front ainda (Etapa 5).
