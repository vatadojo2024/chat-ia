# Etapa 4 — Ligar o buscar_conversa (histórico closer↔lead via Redis) — Requisitos

**Projeto:** Chat IA-Guia — **backend** (projeto novo)
**Etapa:** complemento da Etapa 4 (ativa a ferramenta `buscar_conversa`, que ficou opcional/desligada)
**Versão:** 1.1 (corrige DB, prefixo e o aviso do endereço interno)
**Método:** SDD — este documento é a fonte da verdade. O código deriva dele.

---

## Objetivo da etapa

Ligar de verdade a ferramenta **`buscar_conversa`** do agente closer (Mestre): ele passa a **ler a conversa real que o closer teve com o lead** e usar isso na correção.

**Escopo (importante):** esta etapa **LÊ** um Redis que já existe (o mesmo do seu fluxo do n8n). Ela **não constrói** a captura dessas conversas. Se o Redis estiver acessível e populado, a gente conecta e lê.

---

## O que já sabemos do Redis (informado pelo Vata)

- As conversas estão separadas por **banco (DB)** dentro do Redis:
  - DB1 = Glaucio (SDR) · DB2 = Delrue (SDR) · DB3 = Ben (SDR)
  - **DB8 = closers**, com a chave no formato `closer:55DDDNUMERO` (número do lead).
- Endereço: `redis://redis:6379` — **sem senha** (Redis interno, não exposto).
- Atenção 1: a `buscar_conversa` é do closer → usa **DB8** (não o DB0 que aparece na URL).
- Atenção 2: o host `redis` é um **nome interno do Docker** — só resolve **dentro da VPS**. Fora dela (teste local) esse nome não é alcançável.

---

## Glossário rápido

- **Redis:** banco rápido de chave→valor. Cada lead vira uma chave; o valor é a conversa.
- **Banco/DB:** o Redis tem vários "compartimentos" numerados (0,1,2…). Os closers estão no compartimento **8**.
- **Chave:** o identificador do registro, ex.: `closer:5547999998888`.

---

## Requisitos

### RF-01 — Conexão com o Redis, no banco dos closers (DB8)
- O serviço DEVE conectar no Redis usando o host/porta de `REDIS_URL` e selecionar o **banco 8** (configurável, padrão 8).
- Sem senha (Redis interno).
- A ferramenta `buscar_conversa` continua **registrada só se `REDIS_URL` estiver setado**.

### RF-02 — Encontrar a conversa do lead em DB8
- A ferramenta DEVE, dado o número do lead (normalizado para `55DDDNUMERO`), procurar a conversa em DB8.
- Ordem de tentativa: **`closer:<NUMERO>`** (formato informado) primeiro; se não houver, tentar os prefixos por nome do prompt do Mestre (`aurelio:` / `marcio:` / `giba:`). Primeiro com dado vence.

### RF-03 — Tolerância de formato do valor
- O valor pode estar como **texto puro**, **lista em JSON** de mensagens, ou **lista do Redis**. A ferramenta DEVE transformar qualquer um num **texto de conversa legível** para o Mestre.

### RF-04 — Diagnóstico contra o dado real
- Com acesso ao Redis, a ferramenta/desenvolvimento DEVE **listar algumas chaves do DB8** para confirmar o prefixo real (`closer:` ou nome) e o formato do valor, e ajustar o leitor — em vez de supor.

### RF-05 — Erros tratáveis
- Chave vazia, lead não encontrado, ou Redis inalcançável DEVEM virar **texto curto e tratável** (o Mestre contorna), nunca derrubam o serviço. Mensagens alinhadas ao que o prompt do Mestre já espera.

### RF-06 — Só leitura
- A ferramenta **não escreve** no Redis. Acesso continua restrito ao dono (já garantido).

---

## Requisitos não-funcionais

- **RNF-01:** banco dos closers configurável (`REDIS_CLOSERS_DB`, padrão 8); conexão tolerante a TLS (`rediss://`), embora aqui seja `redis://` sem senha.
- **RNF-02:** a ferramenta só é registrada com `REDIS_URL` setado.
- **RNF-03 — endereço interno:** `redis://redis:6379` só resolve **dentro da rede Docker da VPS**. Logo, o **teste com conversa real** acontece quando o serviço de chat roda na VPS (passo de container). **Localmente**, testar só o encanamento com um Redis de mentira (chave de exemplo).

---

## Fora de escopo

- **Gravar/capturar** as conversas no Redis (a fonte que popula as chaves) — é outro sistema.
- Leitura das conversas de SDR (DB1/2/3) — a Hana usa o Clint, não o Redis. Fica para depois, se necessário.
- Admin, gerador de playbook, resumo rolante, leitura de arquivo, deploy.
