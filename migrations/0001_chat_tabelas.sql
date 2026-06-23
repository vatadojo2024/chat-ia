-- =============================================================================
-- Chat IA-Guia — Etapa 2 — Migration 0001: tabelas do chat
-- =============================================================================
-- Projeto NOVO (backend do chat), aplicado na MESMA instância Supabase do
-- Mapa de Calor (login compartilhado, RLS por auth.uid()).
--
-- Cria chat_conversas e chat_mensagens com domínios (CHECK), índices
-- (acesso + busca por trigrama) e RLS. Tudo idempotente (rodar 2x não dá erro
-- nem duplica). NÃO altera nem remove nada do schema existente do Mapa de Calor.
--
-- Aplicar no SQL Editor do Supabase. Derivado de:
--   specs/chat-ia-etapa-02-tabelas/{requisitos,design,tasks}.md
-- =============================================================================

begin;

-- -----------------------------------------------------------------------------
-- T-04 (parte) — Extensão de busca por trigrama (ILIKE rápido).
-- Criada antes das tabelas porque os índices GIN abaixo usam gin_trgm_ops.
-- -----------------------------------------------------------------------------
create extension if not exists pg_trgm;

-- -----------------------------------------------------------------------------
-- T-01 — Tabela chat_conversas (RF-01, RF-05, RF-08)
-- Uma thread de chat de um usuário com o seu agente (papel).
-- -----------------------------------------------------------------------------
create table if not exists public.chat_conversas (
  id            uuid        primary key default gen_random_uuid(),
  user_id       uuid        not null,                              -- dono; chave da RLS (= auth.uid())
  papel         text        not null
                            check (papel in ('admin', 'gestor', 'closer', 'sdr')),  -- T-03 / RF-07
  titulo        text,                                              -- null = ainda sem título (IA preenche depois)
  resumo        text        default null,                          -- vazio nesta etapa (Etapa 6)
  resumido_ate  timestamptz,                                       -- marca d'água do resumo; vazio nesta etapa
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()                 -- atualizado pelo serviço ao chegar mensagem (etapa futura)
);

-- -----------------------------------------------------------------------------
-- T-02 — Tabela chat_mensagens (RF-02, RF-06)
-- Uma fala dentro de uma conversa. Cascata: apagar a conversa apaga as mensagens.
-- -----------------------------------------------------------------------------
create table if not exists public.chat_mensagens (
  id          uuid        primary key default gen_random_uuid(),
  conversa_id uuid        not null
                          references public.chat_conversas (id) on delete cascade,  -- T-02 cascata
  autor       text        not null
                          check (autor in ('usuario', 'ia')),                       -- T-03 / RF-07
  conteudo    text        not null,
  status      text        not null default 'pronta'
                          check (status in ('pendente', 'pronta', 'erro')),         -- T-03 / RF-07
  anexos      jsonb       not null default '[]'::jsonb,                             -- lista; vazia nesta etapa (Fase F)
  created_at  timestamptz not null default now()                                    -- ordena mensagens dentro da conversa
);

-- -----------------------------------------------------------------------------
-- T-04 — Índices (acesso + busca) (RF-04, RF-09)
-- -----------------------------------------------------------------------------
-- Listar conversas de um usuário pela mais recente.
create index if not exists idx_chat_conversas_user_recente
  on public.chat_conversas (user_id, updated_at desc);

-- Carregar mensagens de uma conversa em ordem.
create index if not exists idx_chat_mensagens_conversa_ordem
  on public.chat_mensagens (conversa_id, created_at);

-- Busca por trecho (ILIKE) — trigramas GIN.
create index if not exists idx_chat_conversas_titulo_trgm
  on public.chat_conversas using gin (titulo gin_trgm_ops);

create index if not exists idx_chat_mensagens_conteudo_trgm
  on public.chat_mensagens using gin (conteudo gin_trgm_ops);

-- -----------------------------------------------------------------------------
-- T-05 — RLS e políticas (RF-03, RNF-03)
-- Cada usuário só acessa o que é seu. service_role ignora RLS (padrão Supabase),
-- então o serviço de IA (etapas futuras) escreve livremente.
-- DROP POLICY IF EXISTS antes de CREATE POLICY = idempotente (CREATE POLICY não
-- aceita IF NOT EXISTS).
-- -----------------------------------------------------------------------------
alter table public.chat_conversas enable row level security;
alter table public.chat_mensagens enable row level security;

-- chat_conversas: dono = auth.uid()
drop policy if exists chat_conversas_select on public.chat_conversas;
create policy chat_conversas_select on public.chat_conversas
  for select to authenticated
  using (user_id = auth.uid());

drop policy if exists chat_conversas_insert on public.chat_conversas;
create policy chat_conversas_insert on public.chat_conversas
  for insert to authenticated
  with check (user_id = auth.uid());

drop policy if exists chat_conversas_update on public.chat_conversas;
create policy chat_conversas_update on public.chat_conversas
  for update to authenticated
  using (user_id = auth.uid())
  with check (user_id = auth.uid());

drop policy if exists chat_conversas_delete on public.chat_conversas;
create policy chat_conversas_delete on public.chat_conversas
  for delete to authenticated
  using (user_id = auth.uid());

-- chat_mensagens: só mensagens de conversas cujo dono é auth.uid()
-- (verifica a existência da conversa-pai do usuário).
drop policy if exists chat_mensagens_select on public.chat_mensagens;
create policy chat_mensagens_select on public.chat_mensagens
  for select to authenticated
  using (exists (
    select 1 from public.chat_conversas c
    where c.id = chat_mensagens.conversa_id
      and c.user_id = auth.uid()
  ));

drop policy if exists chat_mensagens_insert on public.chat_mensagens;
create policy chat_mensagens_insert on public.chat_mensagens
  for insert to authenticated
  with check (exists (
    select 1 from public.chat_conversas c
    where c.id = chat_mensagens.conversa_id
      and c.user_id = auth.uid()
  ));

drop policy if exists chat_mensagens_update on public.chat_mensagens;
create policy chat_mensagens_update on public.chat_mensagens
  for update to authenticated
  using (exists (
    select 1 from public.chat_conversas c
    where c.id = chat_mensagens.conversa_id
      and c.user_id = auth.uid()
  ))
  with check (exists (
    select 1 from public.chat_conversas c
    where c.id = chat_mensagens.conversa_id
      and c.user_id = auth.uid()
  ));

drop policy if exists chat_mensagens_delete on public.chat_mensagens;
create policy chat_mensagens_delete on public.chat_mensagens
  for delete to authenticated
  using (exists (
    select 1 from public.chat_conversas c
    where c.id = chat_mensagens.conversa_id
      and c.user_id = auth.uid()
  ));

commit;

-- =============================================================================
-- Fim da migration 0001. Validação: ver 0001_chat_tabelas_validacao.sql
-- =============================================================================
