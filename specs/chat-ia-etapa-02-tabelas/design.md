# Etapa 2 — Tabelas no Supabase — Design

**Projeto:** Chat IA-Guia — **backend** (projeto NOVO, separado do front)
**Etapa:** 2 de 9 (Fase B — Fundação de dados)
**Versão:** 1.1
**Método:** SDD — deriva do `requisitos.md` (mesma pasta) e orienta o `tasks.md`.

---

## 1. Visão geral

Duas tabelas no mesmo Supabase do Mapa de Calor: **`chat_conversas`** e **`chat_mensagens`**. Prefixo `chat_` para deixar claro que pertencem ao recurso de chat e não colidir com as tabelas existentes (`leads`, `users`…). Uma conversa pertence a um usuário e tem um agente (papel); uma mensagem pertence a uma conversa.

O sistema suporta **várias conversas por usuário**, **título gerado por IA** e **busca por texto**. O schema já contempla título e busca (campo `titulo` + índice de busca); a lógica de gerar título e a tela de busca vêm em etapas próprias.

Tudo entregue como **uma migration SQL versionada e idempotente**, no estilo das 0009–0012, aplicada na mesma instância Supabase (via SQL Editor, como as anteriores).

**Decisão de simplicidade:** sem tabela de anexos, sem compartilhamento, sem pastas, sem arquivamento, sem tags. Anexos são um campo jsonb na mensagem; resumo é um campo na conversa. O mínimo para funcionar bem.

---

## 2. Onde mora no projeto

- **Projeto novo, separado do front.** A tela do chat (Etapa 1) já vive no front; o que começa agora é o **backend** do chat, num repositório/pasta próprios. Esta migration é o **primeiro artefato** desse projeto novo.
- **Mesma instância Supabase** do Mapa de Calor — porque o login é compartilhado (mesmas contas/Auth). As tabelas novas convivem com `leads`/`users` no mesmo banco, com nomes próprios (`chat_`).
- Por ora a migration é um arquivo SQL aplicado pelo SQL Editor do Supabase (o serviço Python só nasce na Etapa 3; quando nascer, ele hospeda esta migration, pois é o serviço dono dessas tabelas).
- Não há código de aplicação nesta etapa — só DDL (SQL de criação).

---

## 3. Modelo de dados

### Tabela `chat_conversas`

| Campo | Tipo | Regra |
|---|---|---|
| `id` | uuid | PK, default de geração automática |
| `user_id` | uuid | Dono. Referencia o usuário autenticado (auth). É a chave da RLS. |
| `papel` | text | CHECK: `admin` \| `gestor` \| `closer` \| `sdr`. Definido a partir do papel do usuário na criação. |
| `titulo` | text | Nulo permitido. `null` = ainda sem título. Será preenchido pela IA em etapa futura (não aqui). |
| `resumo` | text | Nulo, default null. Preenchido só na Etapa 6 (memória). |
| `resumido_ate` | timestamptz | Nulo. Marca d'água: mensagens criadas até este instante já estão no `resumo`. Vazio nesta etapa. |
| `created_at` | timestamptz | default agora. |
| `updated_at` | timestamptz | default agora. Atualizado quando chega mensagem nova (usado para ordenar por recência). |

### Tabela `chat_mensagens`

| Campo | Tipo | Regra |
|---|---|---|
| `id` | uuid | PK, default de geração automática |
| `conversa_id` | uuid | FK → `chat_conversas(id)` ON DELETE CASCADE. |
| `autor` | text | CHECK: `usuario` \| `ia`. |
| `conteudo` | text | O texto da mensagem. |
| `status` | text | CHECK: `pendente` \| `pronta` \| `erro`. Default `pronta` (mensagem do usuário nasce pronta; a da IA nasce `pendente`). |
| `anexos` | jsonb | default `'[]'`. Lista de anexos; vazia nesta etapa (Fase F preenche). |
| `created_at` | timestamptz | default agora. Ordena as mensagens dentro da conversa. |

Observações:
- A mensagem **não** repete `user_id` nem `papel` — isso vive na conversa. A RLS da mensagem olha o dono da conversa-pai.
- O `status` é o que habilita o "pensando…" (`pendente`) e o erro (`erro`), igual ao contrato da Etapa 1.

---

## 4. Relacionamento

`chat_mensagens.conversa_id` → `chat_conversas.id`, com **ON DELETE CASCADE**: apagar uma conversa apaga as mensagens dela. Não há outras FKs (mantém simples).

---

## 5. Segurança (RLS)

RLS **ativada** nas duas tabelas. Políticas:

- **`chat_conversas`:** o usuário só vê/cria/edita/apaga linhas onde `user_id = auth.uid()`.
- **`chat_mensagens`:** o usuário só acessa mensagens cuja `conversa_id` pertence a uma conversa dele — via verificação do tipo "existe conversa com este id e `user_id = auth.uid()`".

A chave **service_role** (que o serviço de IA usará nas próximas etapas) ignora a RLS — então o serviço escreve normalmente. A RLS protege qualquer leitura direta do front. É a mesma filosofia de "segurança em dois lugares" já usada no Mapa de Calor.

---

## 6. Índices

- `chat_conversas`: índice em `(user_id, updated_at desc)` — listar conversas de um usuário pela mais recente.
- `chat_mensagens`: índice em `(conversa_id, created_at)` — carregar as mensagens de uma conversa em ordem.

**Busca por texto (RF-09):** habilitar a extensão `pg_trgm` e criar índices GIN de trigramas para busca rápida por substring (ILIKE), sem precisar de migration depois:
- `chat_conversas`: índice trigram em `titulo`.
- `chat_mensagens`: índice trigram em `conteudo`.

Trigramas dão busca por trecho/parecido em português sem configuração de idioma — simples e suficiente. Sem mais índices (não otimizar antes da hora).

---

## 7. O que NÃO fazer

- NÃO criar tabela de anexos (é campo jsonb na mensagem).
- NÃO implementar a **geração** de título por IA (só o campo `titulo`, que fica nulo).
- NÃO criar endpoint/tela de busca (só o índice).
- NÃO implementar lógica de resumo (só os campos `resumo`/`resumido_ate`, vazios).
- NÃO criar colunas de arquivamento, tags, compartilhamento ou pastas.
- NÃO alterar nem remover nada do schema existente do Mapa de Calor.
- NÃO usar texto livre onde há domínio (papel/autor/status são CHECK).
