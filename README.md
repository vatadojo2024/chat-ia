# Chat IA-Guia — Serviço backend (Etapa 3)

Esqueleto do "cérebro" do chat: um serviço FastAPI que sobe local, confirma que
está no ar (`/health`) e valida o login do Supabase para dizer quem é o usuário e
qual o papel (`/me`). **Sem IA, sem chat, sem escrever no banco** — isso vem nas
próximas etapas.

## Rotas

| Rota      | Acesso    | Resposta |
|-----------|-----------|----------|
| `GET /health` | público   | `200 {"status":"ok"}` |
| `GET /me`     | protegido | `200 {user_id, email, papel}` — ou `401` sem token válido |
| `POST /conversas` | protegido | cria conversa do usuário (com o papel dele) → `201 {id, papel, titulo, ...}` |
| `GET /conversas`  | protegido | lista conversas do usuário, mais recente primeiro |
| `GET /conversas/{id}/mensagens`  | protegido | mensagens em ordem (exibição + polling) |
| `POST /conversas/{id}/mensagens` | protegido | corpo `{"conteudo":"..."}` → salva msg do usuário (`pronta`), cria msg da IA (`pendente`), agenda a IA e responde na hora → `201 {mensagem_usuario, mensagem_ia}` |

| `DELETE /conversas/{id}` | protegido | apaga a conversa do usuário (mensagens caem por cascata) → `204`; `404` se não for dono |

A resposta da IA é **assíncrona**: a `mensagem_ia` nasce `pendente` e, em segundo plano,
vira `pronta` (com o texto do agente) ou `erro`. A tela faz **polling** no GET de mensagens.

### Agentes e ferramentas (Etapa 4bc)

Na tarefa em segundo plano roda um **agente LangChain (tool-calling)** com as ferramentas do papel:

- **SDR (Hana):** `dados_lead(telefone)` — busca lead no Clint por `55DDDNUMERO`.
- **Closer (Mestre do Dojo):** `pesquisa_email(url)` e `pesquisa_numero(url)` — recebem a URL do Clint
  que o modelo monta; o servidor extrai o email/telefone e **adiciona o token** (o modelo nunca vê o token).
  `buscar_conversa(chave)` (histórico via Redis) só é registrada se `REDIS_URL` estiver no `.env`.

O Clint é **só leitura** (`api-token` no header, adicionado no servidor). Sem `CLINT_TOKEN`, as
ferramentas retornam mensagem tratável e a IA explica sem quebrar. Prompts em `prompts/sdr.md` (Hana)
e `prompts/closer.md` (Mestre, texto do Vata).

### Histórico do closer via Redis (Parte B)

`buscar_conversa` lê o Redis do n8n: closers no **DB 8** (`REDIS_CLOSERS_DB`, padrão 8), chave
`closer:55DDDNUMERO`. O DB vem da config, não do `/0` da URL. Dado o número, o servidor normaliza
para `55DDDNUMERO` e tenta os prefixos em ordem: `closer:` → `aurelio:` → `marcio:` → `giba:`
(primeiro com dado vence). Tolera valor em string pura, JSON (lista de mensagens) ou lista do Redis.
Só leitura; erros (não achou / inalcançável) viram texto curto, nunca derrubam.

> O endereço `redis://redis:6379` usa o host interno do Docker da VPS — **só resolve dentro da VPS**.
> Localmente a ferramenta fica registrada mas não alcança esse host; o teste real depende do serviço
> rodar na VPS. O encanamento foi validado local com um Redis em memória.

## Autodiagnóstico (contra a Supabase real)

- **Assinatura do JWT:** **ES256 via JWKS** (assimétrico). Chaves públicas em
  `${SUPABASE_URL}/auth/v1/.well-known/jwks.json`. Emissor (`iss`):
  `${SUPABASE_URL}/auth/v1`.
- **Fonte do papel:** tabela `public.users`, coluna `role` (enum `public.user_role`),
  casando `users.id` = `sub` do JWT. Leitura via **service_role**, somente leitura.

## Como rodar (local)

Pré-requisito: Python 3.11+. A partir da raiz do projeto:

```bash
python -m venv .venv
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Linux/Mac:
# source .venv/bin/activate

pip install -r requirements.txt
```

Garanta que o `.env` tem `SUPABASE_URL` e `SUPABASE_KEY` (veja `.env.example`).
Suba o serviço:

```bash
uvicorn app.main:app --reload --port 8000
```

## Testar

```bash
# 1) Health (público)
curl http://localhost:8000/health
# -> {"status":"ok"}

# 2) /me sem token -> 401
curl -i http://localhost:8000/me

# 3) /me com token inválido -> 401
curl -i -H "Authorization: Bearer token-invalido" http://localhost:8000/me

# 4) /me com token válido -> 200 {user_id, email, papel}
curl -s -H "Authorization: Bearer <ACCESS_TOKEN>" http://localhost:8000/me
```

### Como obter um `<ACCESS_TOKEN>` para testar

Logar no front (que faz login no Supabase) e copiar o `access_token` da sessão; ou
logar via cliente Supabase e pegar o `access_token`. Enviar em
`Authorization: Bearer <token>`. **Para cair na Hana, use um token de uma conta SDR.**

## Testar o chat (Etapa 4a)

Precisa de `ANTHROPIC_API_KEY` no `.env` e de um `<TOKEN>` de uma conta **SDR**.

```bash
TOKEN="<ACCESS_TOKEN_DE_UM_SDR>"
H="Authorization: Bearer $TOKEN"

# 1) Criar conversa
curl -s -X POST -H "$H" http://localhost:8000/conversas
#  -> {"id":"<CONV>","papel":"sdr","titulo":null,...}

# 2) Enviar mensagem (responde NA HORA; a IA fica pendente)
curl -s -X POST -H "$H" -H "Content-Type: application/json" \
  -d '{"conteudo":"Oi Hana, como abordo um lead que sumiu há 3 dias?"}' \
  http://localhost:8000/conversas/<CONV>/mensagens
#  -> {"mensagem_usuario":{...,"status":"pronta"}, "mensagem_ia":{"id":"<IA>","status":"pendente",...}}

# 3) Polling: repetir até a msg da IA virar "pronta" (ou "erro")
curl -s -H "$H" http://localhost:8000/conversas/<CONV>/mensagens

# 4) Memória: 2ª mensagem na MESMA conversa mantém o contexto
curl -s -X POST -H "$H" -H "Content-Type: application/json" \
  -d '{"conteudo":"e se ele responder que está sem tempo?"}' \
  http://localhost:8000/conversas/<CONV>/mensagens

# 5) Erro: com ANTHROPIC_API_KEY inválida/ausente, a msg da IA vira "erro"
# 6) Dono: com o TOKEN de OUTRO usuário, GET .../mensagens da <CONV> -> 404
```
