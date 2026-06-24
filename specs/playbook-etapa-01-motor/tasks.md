# Gerador de Playbook — P1: Motor — Tarefas

**Projeto:** Chat IA-Guia — trilha do gerador de playbook (no MESMO serviço de chat)
**Etapa:** P1 de 2
**Versão:** 1.1 (inclui busca no Clint)
**Método:** SDD — deriva do `requisitos.md` e do `design.md` (mesma pasta).

**Onde:** dentro do serviço de chat (FastAPI), somando aos endpoints atuais. Roda **local**. Mesma Supabase.
**Como executar:** T-01 → T-08 em ordem, cada uma testável. Não construir nada de "Fora de escopo".

---

## Tarefas

### T-01 — Migration `playbook_jobs` no Supabase
- [ ] Tabela com os campos do design (status, fase_atual, origem_arquivo, lead_email, lead_telefone, transcricao, dados_lead, resultado, decisoes_c1/2/3, erro, datas) + RLS por dono.
- **Cobre:** RNF-04.
- **Pronto quando:** a tabela existe no Supabase com RLS; **aplicar a migration ANTES de testar.**

### T-02 — Leitura do arquivo
- [ ] Extrair texto: `.txt` direto; `.docx` com extração; outros → retorno tratável pedindo `.txt`.
- **Cobre:** RF-02.
- **Pronto quando:** um `.txt` e um `.docx` viram texto; formato inválido não quebra.

### T-03 — Endpoints + lifecycle (com STUB, sem IA ainda)
- [ ] POST `/playbooks` (recebe arquivo + e-mail/telefone, extrai texto, cria job `pendente`, agenda tarefa, responde id+status).
- [ ] GET `/playbooks` (lista do usuário), GET `/playbooks/{id}` (status+fase+resultado), DELETE `/playbooks/{id}`.
- [ ] Tarefa em segundo plano com **stub**: `processando` → escreve `resultado` placeholder → `pronto`.
- [ ] Tudo protegido + dono no código.
- **Cobre:** RF-01, RF-07, RF-08, RF-09.
- **Pronto quando:** enviar arquivo+identificador cria um job que vira `pronto` com placeholder; listar/ler/apagar funcionam; outro usuário recebe 404.

### T-04 — Busca do lead no Clint (reaproveitar Etapa 4)
- [ ] Na tarefa em segundo plano, antes do pipeline, chamar `clint_lookup` com o e-mail/telefone; formatar os campos num bloco **DADOS DO LEAD**; guardar em `dados_lead`.
- [ ] Resiliência: não achou / falhou → `dados_lead = "n/i"`, segue.
- **Cobre:** RF-03, RNF-06.
- **Pronto quando:** com um lead real, `dados_lead` traz os campos do Clint; com lead inexistente, vira `n/i` e não quebra.

### T-05 — Camada Opus
- [ ] Função que chama o modelo **Opus** via `PLAYBOOK_MODEL` (padrão `claude-opus-4-8`) com um system (prompt do agente) + a entrada (mensagem montada), e devolve o texto.
- **Cobre:** RNF-01.
- **Pronto quando:** uma chamada de teste a um dos prompts devolve texto.

### T-06 — Pipeline real (3 agentes em fila)
- [ ] Trocar o stub pelos 3 agentes: Diagnóstico → Estratégia → Execução (Opus), `fase_atual` 1→2→3.
- [ ] Montar a entrada de cada agente com seções rotuladas como os prompts esperam (DADOS DO LEAD, TRANSCRIÇÃO, DECISÕES C1/C2).
- [ ] Extrair DECISOES_C1/C2/C3 (regex nos marcadores `[DECISOES_Cx]…[/DECISOES_Cx]`) e injetar no próximo.
- [ ] Montar o playbook (juntar as 3 fases) em `resultado`; guardar decisoes_c*; `status = pronto`; erro → `erro`.
- **Cobre:** RF-04, RF-05, RF-06.
- **Pronto quando:** um job real passa pelas 3 fases e produz o playbook montado.

### T-07 — Prompts em arquivos
- [ ] Colocar `prompts/playbook_diagnostico.md`, `playbook_estrategia.md`, `playbook_execucao.md` (já fornecidos) e o serviço lê deles.
- **Cobre:** RNF-03.
- **Pronto quando:** o pipeline usa os 3 prompts dos arquivos.

### T-08 — Rodar local e validar
- [ ] Enviar transcrição (.txt) + e-mail/telefone de um lead real → acompanhar status (fase 1→2→3) → receber o playbook montado, com DADOS DO LEAD vindo do Clint.
- [ ] Lead inexistente → `dados_lead = n/i`, playbook ainda gera.
- [ ] Apagar um job; outro usuário não acessa o alheio; arquivo inválido tratado; erro de IA → status `erro`.
- **Cobre:** todos os RF + RNFs.
- **Pronto quando:** o ciclo completo funciona local.

---

## Como testar (pré-requisitos)

- `ANTHROPIC_API_KEY` e `CLINT_TOKEN` no `.env` (já tem).
- Migration da T-01 **aplicada** no Supabase.
- Uma **transcrição de exemplo** (`.txt`) + o **e-mail/telefone de um lead real** no Clint.
- Os 3 prompts em `prompts/` (T-07).
- Login com qualquer conta (o gerador não depende de papel).

---

## Critério de pronto da etapa (validação final)

- [ ] Transcrição + identificador enviados → job criado e processado em segundo plano (RF-01, RF-07).
- [ ] Texto extraído do arquivo (RF-02); dados do lead vindos do Clint, resiliente a "não achou" (RF-03).
- [ ] 3 agentes Opus em sequência, com decisões passadas adiante (RF-04, RF-05).
- [ ] Playbook montado e guardado (RF-06).
- [ ] Listar / ler / apagar, restrito ao dono (RF-08, RF-09).
- [ ] Modelo Opus configurável; prompts em arquivos; Clint reaproveitado (RNFs).
- [ ] (Front é a P2.)
