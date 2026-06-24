# Gerador de Playbook — P1: Motor (backend) — Requisitos

**Projeto:** Chat IA-Guia — **trilha do gerador de playbook** (no MESMO serviço de chat)
**Etapa:** P1 de 2 (motor agora; aba do front é P2)
**Versão:** 1.1 (inclui busca dos dados do lead no Clint)
**Método:** SDD — este documento é a fonte da verdade. O código deriva dele.

---

## Objetivo da etapa

Criar o **motor do gerador de playbook** dentro do serviço de chat: recebe uma **transcrição de call** (arquivo) + o **e-mail/telefone do lead**, **busca os dados do lead no Clint**, roda **3 agentes Opus em sequência** (Diagnóstico → Estratégia → Execução) e **monta um playbook completo** (os 21 blocos). Como é um trabalho **longo**, roda em segundo plano, com **status** que a tela vai poder acompanhar.

Esta etapa é só o **motor** (testável por upload + consulta de status). A **aba do front** é a P2.

---

## Glossário rápido (em português claro)

- **Pipeline:** os 3 agentes rodando em fila, um depois do outro.
- **Opus:** o modelo de IA mais forte (e mais caro) da Anthropic — usado aqui pela complexidade do playbook. Diferente do Sonnet do chat.
- **Job:** um "trabalho" longo que roda em segundo plano; a tela acompanha por status até ficar pronto.
- **Decisões C1/C2/C3:** o que cada agente decide e **passa adiante** pro próximo, pra manter coerência entre as fases.
- **DADOS DO LEAD:** o perfil do lead (patrimônio, renda, dor, etc.), buscado no Clint pelo e-mail/telefone.

---

## Requisitos

### RF-01 — Enviar a transcrição + identificar o lead (e responder na hora)
- O usuário DEVE poder enviar um **arquivo de transcrição** junto com o **e-mail e/ou telefone do lead**. O serviço cria um **job**, começa a processar em segundo plano e **responde imediatamente** com o id do job.

### RF-02 — Ler o arquivo da transcrição
- O serviço DEVE extrair o **texto** da transcrição: **`.txt`** direto; **`.docx`** com extração; outros formatos → mensagem tratável pedindo `.txt`.

### RF-03 — Buscar os dados do lead no Clint
- O serviço DEVE usar o **e-mail/telefone** para buscar os dados do lead no **Clint**, reaproveitando a leitura já feita na Etapa 4 (`clint_lookup`), e montar o bloco **DADOS DO LEAD**.
- Se o lead **não for encontrado** no Clint, o serviço DEVE seguir mesmo assim, com DADOS DO LEAD = `n/i` (os prompts lidam com isso); o playbook ainda é gerado a partir da transcrição.

### RF-04 — Pipeline de 3 agentes Opus, em sequência
- O serviço DEVE rodar, em ordem: **Diagnóstico** (blocos 1–8) → **Estratégia** (9–15) → **Execução** (16–21).
- Cada agente recebe **DADOS DO LEAD + TRANSCRIÇÃO** mais as **decisões do(s) agente(s) anterior(es)**.

### RF-05 — Passar as decisões adiante
- O serviço DEVE **extrair** as decisões de cada agente (DECISOES_C1, _C2, _C3) da saída dele (por padrão de texto) e **injetar** no próximo, no formato que o prompt do próximo espera.

### RF-06 — Montar o playbook
- O serviço DEVE **juntar as três fases** num documento completo (os 21 blocos) e **guardar** o resultado.

### RF-07 — Status para a tela acompanhar
- O job DEVE ter **status** (pendente / processando / pronto / erro) e a **fase atual** (1, 2 ou 3).
- A tela vai **consultar** o job até ele ficar pronto (ou erro).

### RF-08 — Listar, ler e apagar jobs
- O usuário DEVE poder **listar** seus playbooks, **ler** um (status + resultado) e **apagar** um.

### RF-09 — Restrito ao dono
- Tudo usa o **login** (token de sessão) e é restrito às coisas do próprio usuário.

---

## Requisitos não-funcionais

- **RNF-01 — Modelo Opus, configurável:** as chamadas do pipeline usam Opus, via variável `PLAYBOOK_MODEL` (padrão **`claude-opus-4-8`**, o Opus atual). *O `claude-opus-4-7` do n8n pode estar desatualizado — por isso o padrão é o atual, trocável por env.*
- **RNF-02 — Assíncrono simples:** tarefa em segundo plano do próprio serviço (sem fila externa). Job longo → mais exposto a reinício (ver design).
- **RNF-03 — Prompts em arquivos:** `prompts/playbook_diagnostico.md`, `playbook_estrategia.md`, `playbook_execucao.md` (já criados).
- **RNF-04 — Nova tabela no Supabase:** `playbook_jobs`, com regra de acesso por dono (RLS).
- **RNF-05 — Dono no código:** o serviço usa a chave administrativa (ignora a RLS) → checar o dono em toda leitura/gravação/remoção.
- **RNF-06 — Reaproveitar a leitura do Clint:** usar o mesmo `clint_lookup`/token da Etapa 4 (só leitura); o serviço chama direto (não é ferramenta que o modelo aciona).
- **RNF-07 — Mesmo serviço de chat:** soma aos endpoints existentes; não é serviço novo.

---

## Fora de escopo (não fazer nesta etapa)

- **A aba do front** (upload, progresso, resultado, download) — é a P2.
- **Export bonito** (.docx/.pdf) — por ora o resultado é texto/markdown; export formatado fica para depois.
- **Histórico de conversa (Redis)** — o pipeline usa só DADOS DO LEAD (Clint) + transcrição.
- Restringir por papel (qualquer usuário logado pode gerar, salvo decisão em contrário), admin, resumo de chat.
