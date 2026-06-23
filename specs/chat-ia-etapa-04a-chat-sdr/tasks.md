# Etapa 4 — Ligar o buscar_conversa — Tarefas

**Projeto:** Chat IA-Guia — **backend** (projeto novo)
**Versão:** 1.1 (DB8, prefixo, host interno)
**Método:** SDD — deriva do `requisitos.md` e do `design.md` (mesma pasta).

**Onde:** projeto novo do chat (em cima da Etapa 4 já feita). Mexe principalmente em `app/redis_tool.py`.
**Como executar:** T-01 → T-06 em ordem. Não mexer no resto da Etapa 4.

---

## Tarefas

### T-01 — Conexão no banco dos closers (DB8)
- [ ] Cliente de Redis com host/porta de `REDIS_URL`, selecionando o banco via `REDIS_CLOSERS_DB` (padrão **8**). Suporta `redis://` e `rediss://`. Sem senha.
- [ ] Falha de conexão → erro tratável (não derruba).
- **Cobre:** RF-01, RNF-01.
- **Pronto quando:** conecta no DB8 com `REDIS_URL` válido; URL inválida não quebra.

### T-02 — Achar a conversa por chave em DB8
- [ ] Normalizar número para `55DDDNUMERO`.
- [ ] Tentar, em ordem: `closer:<NUMERO>` → `aurelio:<NUMERO>` → `marcio:<NUMERO>` → `giba:<NUMERO>`. Primeiro com dado vence.
- [ ] (Opcional) se o prefixo real for por nome, usar o nome-curto do closer logado (mapa e-mail→curto) para mirar direto.
- **Cobre:** RF-02.
- **Pronto quando:** dado um número, a ferramenta encontra a chave correspondente em DB8 (quando existe).

### T-03 — Tolerar o formato do valor
- [ ] Transformar o valor em texto legível tentando: string pura → JSON lista de mensagens → lista do Redis.
- **Cobre:** RF-03.
- **Pronto quando:** a conversa volta como texto que o Mestre interpreta.

### T-04 — Erros tratáveis
- [ ] Chave vazia / não achada / Redis inalcançável → texto curto alinhado ao prompt do Mestre.
- **Cobre:** RF-05.
- **Pronto quando:** nenhum desses casos derruba o serviço.

### T-05 — Diagnóstico contra o dado real
- [ ] Com acesso ao Redis, listar algumas chaves do DB8 e confirmar prefixo real (`closer:` ou nome) e formato do valor; ajustar o leitor.
- **Cobre:** RF-04.
- **Pronto quando:** o leitor casa com o que existe de verdade no DB8.

### T-06 — Testar (encanamento agora; real no deploy)
- [ ] **Local:** subir um Redis local (o próprio Claude Code pode), pôr uma chave de exemplo `closer:5547999998888` com uma conversa, apontar `REDIS_URL` + DB8 pra ele, e validar: como **closer**, "o que esse lead falou sobre X? 5547999998888" → o Mestre lê e responde no personagem.
- [ ] Confirmar que sem `REDIS_URL` a ferramenta segue desligada.
- [ ] Anotar que o teste com **conversa real** depende do serviço rodar na VPS (host `redis` interno).
- **Cobre:** todos os RF.
- **Pronto quando:** o teste de encanamento passa e o caminho real está claro.

---

## Pré-requisitos / configuração

- `.env`: `REDIS_URL=redis://redis:6379` (host/porta) e `REDIS_CLOSERS_DB=8`. (Para o teste local, apontar `REDIS_URL` pro Redis local.)
- **Sem senha** (Redis interno).
- Lembrar: `redis://redis:6379` só conecta **dentro da VPS** — teste real no passo de container; teste local com Redis de mentira.
- Conta de **closer** (ou override de papel em dev) para cair no Mestre.

---

## Critério de pronto da etapa (validação final)

- [ ] Conecta no Redis no **DB8** (RF-01).
- [ ] Acha a conversa por chave, tolerando o formato (RF-02, RF-03).
- [ ] Diagnóstico confirmou prefixo e formato reais (RF-04) — quando houver acesso.
- [ ] Erros tratáveis (RF-05).
- [ ] Só leitura; sem `REDIS_URL` segue desligada (RF-06, RNF-02).
- [ ] Encanamento testado local; teste real planejado para o deploy.
