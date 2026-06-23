# Etapa 3 — Esqueleto do serviço Python — Tarefas

**Projeto:** Chat IA-Guia — **backend** (projeto novo)
**Etapa:** 3 de 9 (Fase C — Esqueleto do cérebro)
**Versão:** 1.0
**Método:** SDD — estas tarefas derivam do `requisitos.md` e do `design.md` (mesma pasta).

**Onde:** projeto novo do chat (mesma pasta/repo da Etapa 2). Roda **local** (uvicorn). Sem Docker.
**Insumo:** requisitos e design desta pasta. Autocontido — não consultar documento externo.

**Como executar:** tarefas T-01 → T-06 em ordem; cada uma testável. Não construir nada da lista "Fora de escopo" do `requisitos.md`. Sem IA, sem tabelas de chat, sem escrita no banco.

---

## Tarefas

### T-01 — Esqueleto FastAPI + `/health`
- [ ] Criar o app FastAPI mínimo e a rota `/health` (pública) → 200 `{"status":"ok"}`.
- [ ] Rodar local com uvicorn.
- **Cobre:** RF-01, RNF-01, RNF-05.
- **Pronto quando:** `curl http://localhost:PORTA/health` devolve 200 com JSON.

### T-02 — Config por `.env`
- [ ] Ler `SUPABASE_URL` e o necessário para validação/papel do `.env`; nenhum segredo no código.
- **Cobre:** RNF-02, RNF-03.
- **Pronto quando:** faltando uma variável, o serviço avisa claramente o que falta.

### T-03 — Validação do JWT (camada de auth)
- [ ] Criar uma dependência reutilizável que: lê o `Bearer` token, valida (assinatura via JWKS do Supabase, `exp`, `iss`) e devolve a identidade (`sub`, `email`).
- [ ] Token ausente/inválido/expirado → 401.
- [ ] **Autodiagnóstico:** confirmar o método de assinatura do projeto consultando o endpoint de chaves do Supabase — se houver chaves públicas, validar por JWKS (ES256, provável); se não, validar por HS256 com o segredo. Reportar qual é.
- **Cobre:** RF-02, RF-03.
- **Pronto quando:** uma rota protegida aceita token válido e rejeita inválido com 401.

### T-04 — Resolução do papel
- [ ] Resolver o papel (`admin`/`gestor`/`closer`/`sdr`) do usuário identificado.
- [ ] **Autodiagnóstico:** achar a fonte do papel na mesma Supabase — inspecionar o schema para localizar a tabela de equipe/usuários e a coluna do papel, casando pelo auth user id (`sub`). Se o papel vier no token (`app_metadata`), usar de lá. Reportar a fonte usada (tabela/coluna ou claim).
- [ ] Leitura via service_role, somente leitura.
- **Cobre:** RF-04, RNF-04.
- **Pronto quando:** para um usuário real, o papel correto é resolvido.

### T-05 — Endpoint `/me`
- [ ] Rota protegida `/me` → `{user_id, email, papel}`, usando a camada de auth (T-03) + resolução de papel (T-04).
- **Cobre:** RF-05.
- **Pronto quando:** `/me` com token válido devolve o usuário e o papel certos.

### T-06 — Rodar local e validar
- [ ] `curl /health` → 200.
- [ ] `/me` sem token → 401; com token inválido → 401; com token válido → 200 + dados certos.
- [ ] Testar com DOIS usuários de papéis diferentes (ex.: um closer e um SDR) → papel resolvido diferente para cada.
- **Cobre:** todos os RF + RNFs.
- **Pronto quando:** os testes acima passam.

---

## Como obter um JWT para testar

Logar no front (que faz login no Supabase) e copiar o token de acesso da sessão; ou usar o cliente do Supabase para logar e pegar o `access_token`. Enviar em `Authorization: Bearer <token>`.

---

## Critério de pronto da etapa (validação final)

- [ ] `/health` responde 200 (RF-01).
- [ ] JWT validado; ausente/inválido → 401 (RF-02).
- [ ] Usuário identificado: id e e-mail (RF-03).
- [ ] Papel resolvido da fonte confirmada (RF-04).
- [ ] `/me` devolve usuário + papel com token válido (RF-05).
- [ ] Roda local; nada escrito no banco; projeto novo (RNFs).
- [ ] Reportado: método de assinatura do JWT detectado e fonte do papel usada.
