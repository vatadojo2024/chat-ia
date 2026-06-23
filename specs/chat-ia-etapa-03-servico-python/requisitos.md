# Etapa 3 — Esqueleto do serviço Python — Requisitos

**Projeto:** Chat IA-Guia — **backend** (projeto novo)
**Etapa:** 3 de 9 (Fase C — Esqueleto do cérebro)
**Versão:** 1.0
**Método:** SDD — este documento é a fonte da verdade. O código é derivado dele.

---

## Objetivo da etapa

Subir o **serviço Python (FastAPI)** do chat, com uma rota `/health` que confirma "está no ar", e fazer ele **validar o mesmo login do Supabase** para saber **quem é o usuário** e **qual o papel** (admin/gestor/closer/sdr). Sem IA, sem chat, sem escrever nada no banco. Roda **local primeiro** (como a API do Mapa de Calor começou na Etapa 1 dela).

É o esqueleto do cérebro: o serviço existe, sobe, e já sabe identificar com segurança quem está do outro lado. A inteligência (responder) vem na Etapa 4.

---

## Glossário rápido (em português claro)

- **FastAPI:** ferramenta em Python para criar serviços web. É o "cérebro" do chat.
- **`/health`:** rota simples que responde "ok" — serve para provar que o serviço subiu.
- **JWT:** o "crachá" que o login do Supabase entrega ao usuário. O serviço confere se é válido.
- **JWKS:** as chaves públicas do Supabase usadas para conferir a assinatura do crachá (JWT).
- **Endpoint protegido:** rota que só responde se vier um crachá válido.
- **Papel:** a função do usuário (admin/gestor/closer/sdr).
- **Local primeiro:** roda na sua máquina; subir na VPS é a Etapa 9.
- **service_role:** a chave administrativa do Supabase (a mesma do backfill); aqui só para LER, se preciso.

---

## Requisitos

### RF-01 — Serviço no ar com `/health`

**Como** desenvolvedor,
**quero** uma rota que confirme que o serviço está rodando,
**para** saber que o esqueleto subiu antes de qualquer outra coisa.

Critérios de aceite:
- QUANDO o serviço estiver rodando ENTÃO uma chamada a `/health` DEVE responder 200 com um JSON simples (ex.: `{"status":"ok"}`).
- `/health` NÃO exige login.

### RF-02 — Validação do login (JWT)

**Como** sistema,
**quero** validar o crachá do Supabase,
**para** só atender quem está realmente logado.

Critérios de aceite:
- QUANDO uma rota protegida receber um JWT válido do Supabase ENTÃO o serviço DEVE aceitar.
- QUANDO o JWT estiver ausente, expirado ou inválido ENTÃO o serviço DEVE responder 401.
- A validação DEVE conferir assinatura, expiração e emissor, usando as chaves públicas do Supabase (o **mesmo Auth** do Mapa de Calor).

### RF-03 — Identidade do usuário

**Como** sistema,
**quero** saber quem é o usuário a partir do crachá,
**para** ligar a conversa ao dono certo (nas próximas etapas).

Critérios de aceite:
- A partir de um JWT válido, o serviço DEVE extrair a identidade: id do usuário (`sub`) e e-mail.

### RF-04 — Papel do usuário

**Como** sistema,
**quero** saber o papel do usuário,
**para** escolher o agente certo (closer/SDR/admin) nas próximas etapas.

Critérios de aceite:
- O serviço DEVE resolver o papel (`admin`/`gestor`/`closer`/`sdr`) do usuário identificado.
- O papel DEVE vir da **mesma fonte** que o Mapa de Calor usa para autorização (a tabela de equipe/usuários na mesma Supabase). A tabela/coluna exata é confirmada na execução.

### RF-05 — Endpoint que prova o pipeline (`/me`)

**Como** desenvolvedor,
**quero** uma rota que devolva quem sou e meu papel,
**para** testar de ponta a ponta que o login é validado e o papel resolvido.

Critérios de aceite:
- O serviço DEVE expor uma rota protegida (ex.: `/me`) que, com JWT válido, devolve usuário + papel.
- Sem token ou com token inválido, `/me` DEVE responder 401.

---

## Requisitos não-funcionais

- **RNF-01 — Local primeiro:** roda na máquina; deploy/Docker é a Etapa 9.
- **RNF-02 — Config por `.env`:** URL do Supabase e o necessário para validar/resolver papel; nenhum segredo no código.
- **RNF-03 — Mesma Supabase:** usa o mesmo Auth (chaves do JWT) e a mesma fonte de papel do Mapa de Calor.
- **RNF-04 — Sem escrita:** nenhuma escrita no banco nesta etapa; no máximo **leitura** da tabela de usuários para resolver o papel.
- **RNF-05 — Projeto novo:** mesma pasta/repo da migration da Etapa 2.

---

## Fora de escopo (não fazer nesta etapa)

- IA, prompts dos agentes, qualquer resposta de chat (Etapa 4).
- Escrever conversas/mensagens nas tabelas (Etapa 4).
- Memória/resumo (Etapa 6), leitura de arquivo (Etapa 7), Clint (Etapa 8), Docker/deploy (Etapa 9).
- Tela e ligação com o front (a tela já existe; ligar é a Etapa 5).
