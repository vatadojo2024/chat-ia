# Etapa 2 — Tabelas no Supabase — Tarefas

**Projeto:** Chat IA-Guia — **backend** (projeto NOVO, separado do front)
**Etapa:** 2 de 9 (Fase B — Fundação de dados)
**Versão:** 1.1
**Método:** SDD — estas tarefas derivam do `requisitos.md` e do `design.md` (mesma pasta).

**Onde:** projeto NOVO do chat (pasta/repo próprios), separado do front. Esta migration é o 1º artefato dele. É aplicada na **MESMA instância Supabase** do Mapa de Calor (a que já tem `leads`, `users`, etc.) — o login é compartilhado.

**Insumo:** os campos, domínios, RLS e índices estão no `design.md` desta pasta. Autocontido — não consultar documento externo. Entregável: UMA migration SQL versionada e idempotente.

**Como executar:** montar a migration nas tarefas abaixo, em ordem; tudo num único arquivo SQL. Cada bloco é verificável. Não construir nada da lista "Fora de escopo" do `requisitos.md`. NÃO alterar tabelas existentes.

---

## Tarefas

### T-01 — Tabela `chat_conversas`
- [ ] No arquivo de migration, criar `chat_conversas` com os campos da seção 3 do `design.md`
  (id uuid PK com default; user_id uuid; papel text; titulo text null; resumo text default null;
  resumido_ate timestamptz null; created_at/updated_at timestamptz default agora).
- [ ] `CREATE TABLE IF NOT EXISTS` (idempotente).
- **Cobre:** RF-01, RF-05, RF-08, RNF-01, RNF-02.
- **Pronto quando:** rodar a migration cria a tabela; rodar de novo não dá erro.

### T-02 — Tabela `chat_mensagens`
- [ ] Criar `chat_mensagens` com os campos da seção 3 (id uuid PK; conversa_id uuid;
  autor text; conteudo text; status text default 'pronta'; anexos jsonb default '[]'; created_at).
- [ ] FK `conversa_id` → `chat_conversas(id)` ON DELETE CASCADE.
- [ ] `CREATE TABLE IF NOT EXISTS` (idempotente).
- **Cobre:** RF-02, RF-06, RNF-01.
- **Pronto quando:** a tabela existe; apagar uma conversa apaga as mensagens dela.

### T-03 — Domínios (CHECK)
- [ ] `papel` ∈ {admin, gestor, closer, sdr}; `autor` ∈ {usuario, ia}; `status` ∈ {pendente, pronta, erro}.
- **Cobre:** RF-07.
- **Pronto quando:** inserir um valor fora do domínio é rejeitado.

### T-04 — Índices (acesso + busca)
- [ ] `chat_conversas`: índice em (user_id, updated_at desc).
- [ ] `chat_mensagens`: índice em (conversa_id, created_at).
- [ ] Busca: `CREATE EXTENSION IF NOT EXISTS pg_trgm` e índices GIN de trigramas em
  `chat_conversas.titulo` e `chat_mensagens.conteudo` (para ILIKE rápido).
- [ ] Todos com `IF NOT EXISTS` (idempotente).
- **Cobre:** RF-04 (listar por recência), RF-09 (busca), e desempenho de leitura.
- **Pronto quando:** os índices (inclusive os de busca) existem.

### T-05 — RLS e políticas
- [ ] Ativar RLS nas duas tabelas.
- [ ] `chat_conversas`: políticas de SELECT/INSERT/UPDATE/DELETE permitindo apenas `user_id = auth.uid()`.
- [ ] `chat_mensagens`: políticas permitindo apenas mensagens de conversas cujo dono é `auth.uid()`
  (checar via existência da conversa-pai com user_id = auth.uid()).
- [ ] Escrita via service_role continua livre (ignora RLS) — comportamento padrão do Supabase, confirmar.
- **Cobre:** RF-03, RNF-03.
- **Pronto quando:** as políticas existem e estão ativas.

### T-06 — Aplicar e validar
- [ ] Aplicar a migration no Supabase (SQL Editor).
- [ ] Conferir que as duas tabelas e todos os índices (inclusive os de busca) existem.
- [ ] Teste de RLS: inserir conversas de dois usuários distintos e confirmar que, autenticado como um, só as próprias aparecem; as do outro não.
- [ ] Teste de cascata: apagar uma conversa remove as mensagens dela.
- [ ] Teste de busca: um ILIKE por trecho em `conteudo`/`titulo` retorna o esperado.
- [ ] Confirmar que NADA do schema existente do Mapa de Calor foi alterado.
- **Cobre:** todos os RF + RNF-04.
- **Pronto quando:** os testes acima passam.

---

## Critério de pronto da etapa (validação final)

- [ ] `chat_conversas` e `chat_mensagens` existem na mesma Supabase, com os campos do design (RF-01, RF-02).
- [ ] Domínios (papel/autor/status) rejeitam valor inválido (RF-07).
- [ ] RLS ativa: cada usuário só enxerga as próprias conversas e mensagens (RF-03).
- [ ] Um usuário pode ter várias conversas, listáveis pela mais recente (RF-04).
- [ ] `titulo` aceita nulo (pronto para a IA preencher depois) (RF-08).
- [ ] Busca por texto viável: extensão e índices de trigrama criados (RF-09).
- [ ] Campos de resumo e de anexos existem e estão vazios, prontos para as etapas futuras (RF-05, RF-06).
- [ ] Apagar conversa apaga as mensagens (cascata).
- [ ] Migration é idempotente e não tocou no schema existente (RNF-01, RNF-04).
