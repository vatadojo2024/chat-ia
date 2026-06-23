-- =============================================================================
-- Chat IA-Guia — Etapa 2 — Validação (T-06)
-- =============================================================================
-- NÃO faz parte da migration. Rodar bloco a bloco no SQL Editor do Supabase,
-- DEPOIS de aplicar 0001_chat_tabelas.sql. Cada bloco é independente.
-- Ao final há um bloco de limpeza para apagar os dados de teste.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- 1) As duas tabelas existem (espera 2 linhas: chat_conversas, chat_mensagens)
-- -----------------------------------------------------------------------------
select table_name
from information_schema.tables
where table_schema = 'public'
  and table_name in ('chat_conversas', 'chat_mensagens')
order by table_name;


-- -----------------------------------------------------------------------------
-- 2) Todos os índices existem (espera 6: 2 PK + 2 de acesso + 2 de trigrama)
-- -----------------------------------------------------------------------------
select tablename, indexname
from pg_indexes
where schemaname = 'public'
  and tablename in ('chat_conversas', 'chat_mensagens')
order by tablename, indexname;
-- Esperado:
--   chat_conversas: chat_conversas_pkey,
--                   idx_chat_conversas_user_recente,
--                   idx_chat_conversas_titulo_trgm
--   chat_mensagens: chat_mensagens_pkey,
--                   idx_chat_mensagens_conversa_ordem,
--                   idx_chat_mensagens_conteudo_trgm


-- -----------------------------------------------------------------------------
-- 2b) Extensão pg_trgm instalada (espera 1 linha)
-- -----------------------------------------------------------------------------
select extname from pg_extension where extname = 'pg_trgm';


-- -----------------------------------------------------------------------------
-- 2c) RLS ativa nas duas tabelas (relrowsecurity = true nas duas)
-- -----------------------------------------------------------------------------
select relname, relrowsecurity
from pg_class
where relname in ('chat_conversas', 'chat_mensagens')
order by relname;


-- -----------------------------------------------------------------------------
-- 2d) Políticas criadas (espera 8: 4 por tabela)
-- -----------------------------------------------------------------------------
select tablename, policyname, cmd
from pg_policies
where schemaname = 'public'
  and tablename in ('chat_conversas', 'chat_mensagens')
order by tablename, policyname;


-- -----------------------------------------------------------------------------
-- 3) Domínios (CHECK) rejeitam valor inválido
--    Rodar como service_role (SQL Editor padrão) — RLS não interfere aqui.
--    Os INSERT abaixo DEVEM falhar com erro de check constraint.
-- -----------------------------------------------------------------------------
-- papel inválido -> ERRO esperado
-- insert into public.chat_conversas (user_id, papel) values (gen_random_uuid(), 'invalido');

-- autor inválido -> ERRO esperado (criar antes uma conversa válida; ver bloco 4)
-- status inválido -> ERRO esperado
-- (descomente um de cada vez para confirmar que o banco recusa)


-- -----------------------------------------------------------------------------
-- 4) Teste de RLS com DOIS usuários + cascata
--    Usa dois UUIDs fixos simulando dois usuários logados. Como o SQL Editor
--    roda como service_role (ignora RLS), trocamos para o papel 'authenticated'
--    e injetamos o JWT (sub = id do usuário) para que auth.uid() responda.
-- -----------------------------------------------------------------------------

-- 4.0) Semear dados como service_role (ignora RLS): uma conversa para cada usuário.
insert into public.chat_conversas (id, user_id, papel, titulo) values
  ('11111111-1111-1111-1111-111111111111', '00000000-0000-0000-0000-0000000000aa', 'closer', 'Conversa do usuário A sobre abordagem'),
  ('22222222-2222-2222-2222-222222222222', '00000000-0000-0000-0000-0000000000bb', 'sdr',    'Conversa do usuário B sobre prospecção');

insert into public.chat_mensagens (conversa_id, autor, conteudo, status) values
  ('11111111-1111-1111-1111-111111111111', 'usuario', 'Como faço o follow-up deste lead?', 'pronta'),
  ('11111111-1111-1111-1111-111111111111', 'ia',      'Sugiro retomar pelo WhatsApp...',   'pronta'),
  ('22222222-2222-2222-2222-222222222222', 'usuario', 'Qual a melhor cadência de prospecção?', 'pronta');

-- 4.1) Como usuário A: deve enxergar APENAS a conversa A (espera 1 linha).
begin;
  set local role authenticated;
  set local request.jwt.claims = '{"sub":"00000000-0000-0000-0000-0000000000aa","role":"authenticated"}';
  select 'A vê estas conversas:' as etapa, id, titulo from public.chat_conversas order by created_at;
  select 'A vê estas mensagens:' as etapa, conversa_id, conteudo from public.chat_mensagens order by created_at;
commit;

-- 4.2) Como usuário B: deve enxergar APENAS a conversa B (espera 1 linha).
begin;
  set local role authenticated;
  set local request.jwt.claims = '{"sub":"00000000-0000-0000-0000-0000000000bb","role":"authenticated"}';
  select 'B vê estas conversas:' as etapa, id, titulo from public.chat_conversas order by created_at;
  select 'B vê estas mensagens:' as etapa, conversa_id, conteudo from public.chat_mensagens order by created_at;
commit;

-- 4.3) Como usuário A: tentar ler a conversa de B pelo id -> 0 linhas (RLS barra).
begin;
  set local role authenticated;
  set local request.jwt.claims = '{"sub":"00000000-0000-0000-0000-0000000000aa","role":"authenticated"}';
  select 'A tentando ler conversa de B (espera 0):' as etapa, count(*)
  from public.chat_conversas
  where id = '22222222-2222-2222-2222-222222222222';
commit;

-- 4.4) Como usuário A: tentar inserir conversa em nome de B -> deve FALHAR (WITH CHECK).
-- begin;
--   set local role authenticated;
--   set local request.jwt.claims = '{"sub":"00000000-0000-0000-0000-0000000000aa","role":"authenticated"}';
--   insert into public.chat_conversas (user_id, papel) values ('00000000-0000-0000-0000-0000000000bb', 'closer'); -- ERRO esperado
-- commit;


-- -----------------------------------------------------------------------------
-- 5) Teste de cascata: apagar a conversa A apaga as mensagens dela.
--    (como service_role, ignora RLS)
-- -----------------------------------------------------------------------------
select 'mensagens da conversa A antes (espera 2):' as etapa, count(*)
from public.chat_mensagens
where conversa_id = '11111111-1111-1111-1111-111111111111';

delete from public.chat_conversas
where id = '11111111-1111-1111-1111-111111111111';

select 'mensagens da conversa A depois (espera 0):' as etapa, count(*)
from public.chat_mensagens
where conversa_id = '11111111-1111-1111-1111-111111111111';


-- -----------------------------------------------------------------------------
-- 6) Teste de busca (ILIKE por trecho) usando os índices de trigrama.
-- -----------------------------------------------------------------------------
-- Busca no título da conversa (espera achar a conversa de B: "prospecção").
select 'busca titulo' as etapa, id, titulo
from public.chat_conversas
where titulo ilike '%prospec%';

-- Busca no conteúdo das mensagens (espera achar a mensagem de B: "cadência").
select 'busca conteudo' as etapa, conversa_id, conteudo
from public.chat_mensagens
where conteudo ilike '%cadência%';

-- (Opcional) Confirmar que o índice de trigrama é usável pelo planner:
-- explain (analyze, buffers)
-- select * from public.chat_mensagens where conteudo ilike '%cadência%';


-- -----------------------------------------------------------------------------
-- 7) Nada do schema existente do Mapa de Calor foi alterado:
--    apenas as duas tabelas novas têm prefixo chat_ e nenhuma outra foi tocada.
--    (confere visualmente que leads/users/etc. seguem intactas — a migration
--     só faz CREATE de objetos chat_*, sem ALTER/DROP em nada pré-existente.)
-- -----------------------------------------------------------------------------
select table_name
from information_schema.tables
where table_schema = 'public'
  and table_name like 'chat\_%'
order by table_name;


-- -----------------------------------------------------------------------------
-- 8) LIMPEZA — apagar os dados de teste (deixa o banco limpo).
-- -----------------------------------------------------------------------------
delete from public.chat_conversas
where id in (
  '11111111-1111-1111-1111-111111111111',
  '22222222-2222-2222-2222-222222222222'
);
-- as mensagens da conversa B somem por cascata.
