-- =============================================================================
-- Chat IA-Guia — Gerador de Playbook P1 — Migration 0002: playbook_jobs
-- =============================================================================
-- Tabela dos "jobs" do gerador de playbook (motor que roda 3 agentes Opus).
-- Mesma instância Supabase; RLS por dono (user_id = auth.uid()). service_role
-- escreve livre (e o serviço replica a checagem de dono no código).
-- Idempotente. NÃO altera nada do schema existente.
--
-- Aplicar no SQL Editor do Supabase ANTES de testar o motor.
-- =============================================================================

begin;

-- -----------------------------------------------------------------------------
-- T-01 — Tabela playbook_jobs (RNF-04)
-- -----------------------------------------------------------------------------
create table if not exists public.playbook_jobs (
  id             uuid        primary key default gen_random_uuid(),
  user_id        uuid        not null,                              -- dono; chave da RLS (= auth.uid())
  status         text        not null default 'pendente'
                             check (status in ('pendente', 'processando', 'pronto', 'erro')),
  fase_atual     smallint    check (fase_atual in (1, 2, 3)),       -- nulo no começo; 1/2/3 no pipeline
  origem_arquivo text,                                              -- nome do arquivo enviado
  lead_email     text,                                             -- identificador informado
  lead_telefone  text,                                             -- identificador informado
  transcricao    text,                                             -- texto extraído do arquivo
  dados_lead     text,                                             -- bloco DADOS DO LEAD (Clint) ou 'n/i'
  resultado      text,                                             -- o playbook montado (3 fases)
  decisoes_c1    text,                                             -- auditoria: decisões de cada agente
  decisoes_c2    text,
  decisoes_c3    text,
  erro           text,                                             -- mensagem curta em caso de falha
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now()
);

-- Listar jobs do usuário pela mais recente.
create index if not exists idx_playbook_jobs_user_recente
  on public.playbook_jobs (user_id, updated_at desc);

-- -----------------------------------------------------------------------------
-- RLS e políticas (RNF-04, RNF-05) — cada um só age nos próprios jobs.
-- DROP POLICY IF EXISTS antes de CREATE = idempotente.
-- -----------------------------------------------------------------------------
alter table public.playbook_jobs enable row level security;

drop policy if exists playbook_jobs_select on public.playbook_jobs;
create policy playbook_jobs_select on public.playbook_jobs
  for select to authenticated
  using (user_id = auth.uid());

drop policy if exists playbook_jobs_insert on public.playbook_jobs;
create policy playbook_jobs_insert on public.playbook_jobs
  for insert to authenticated
  with check (user_id = auth.uid());

drop policy if exists playbook_jobs_update on public.playbook_jobs;
create policy playbook_jobs_update on public.playbook_jobs
  for update to authenticated
  using (user_id = auth.uid())
  with check (user_id = auth.uid());

drop policy if exists playbook_jobs_delete on public.playbook_jobs;
create policy playbook_jobs_delete on public.playbook_jobs
  for delete to authenticated
  using (user_id = auth.uid());

commit;

-- =============================================================================
-- Fim da migration 0002.
-- =============================================================================
