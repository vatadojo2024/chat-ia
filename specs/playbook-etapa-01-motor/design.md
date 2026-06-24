# Gerador de Playbook — P1: Motor — Design

**Projeto:** Chat IA-Guia — trilha do gerador de playbook (no MESMO serviço de chat)
**Etapa:** P1 de 2
**Versão:** 1.1 (inclui busca no Clint)
**Método:** SDD — deriva do `requisitos.md` (mesma pasta) e orienta o `tasks.md`.

---

## 1. Visão geral

Novo conjunto de endpoints **dentro do serviço de chat**. O usuário envia a transcrição + e-mail/telefone do lead → o serviço cria um **job** e processa em segundo plano: **busca os dados do lead no Clint**, roda os **3 agentes Opus em fila** (passando as decisões de um pro outro) e **monta o playbook**. A tela acompanha por **status**.

---

## 2. Onde mora

- Mesmo **serviço de chat** (FastAPI) — soma aos endpoints atuais.
- Mesma **Supabase** (uma tabela nova).
- Mesmo `ANTHROPIC_API_KEY` (modelo Opus) e mesmo `CLINT_TOKEN`/`clint_lookup` da Etapa 4.

---

## 3. Tabela `playbook_jobs` (nova)

Campos:
- `id` (uuid), `user_id` (uuid).
- `status` (`pendente` | `processando` | `pronto` | `erro`).
- `fase_atual` (smallint 1/2/3, nulo no começo).
- `origem_arquivo` (texto: nome do arquivo enviado).
- `lead_email`, `lead_telefone` (texto: identificadores informados).
- `transcricao` (texto: o texto extraído do arquivo).
- `dados_lead` (texto: o bloco DADOS DO LEAD montado a partir do Clint — ou `n/i`).
- `resultado` (texto: o playbook montado).
- `decisoes_c1`, `decisoes_c2`, `decisoes_c3` (texto, opcionais — auditoria).
- `erro` (texto curto, opcional).
- `created_at`, `updated_at`.

RLS: o dono só vê/age nos próprios jobs (`user_id = auth.uid()`).

---

## 4. Endpoints (protegidos por login, restritos ao dono)

- **POST `/playbooks`** — recebe o **arquivo** (multipart) + **e-mail e/ou telefone** do lead; extrai o texto; cria o job (`pendente`) com a transcrição e os identificadores; agenda a tarefa; responde `id` + `status`.
- **GET `/playbooks`** — lista os jobs do usuário (mais recente primeiro).
- **GET `/playbooks/{id}`** — status + fase + resultado (para polling e exibição).
- **DELETE `/playbooks/{id}`** — apaga o job.

---

## 5. Leitura do arquivo

- `.txt` → lê direto. `.docx` → extrai o texto. Outros → retorno tratável pedindo `.txt`. Guarda em `transcricao`.

---

## 6. Buscar dados do lead no Clint (reaproveitando a Etapa 4)

- Com o e-mail/telefone, chamar o **`clint_lookup`** já existente (só leitura, token no servidor).
- Formatar os campos retornados (os mesmos do backfill: `renda`, `patrimonio`, `observacoes`, `objetivo`, `obstaculo`, `profissao`, etc.) num bloco legível **DADOS DO LEAD** e guardar em `dados_lead`.
- **Resiliência:** se não achar o lead (ou a busca falhar), seguir com `dados_lead = "n/i"` — o playbook ainda é gerado a partir da transcrição.

---

## 7. Pipeline (na tarefa em segundo plano)

0. `status = processando`. **Buscar no Clint** (seção 6) → `dados_lead`.
1. `fase_atual = 1`. **Agente Diagnóstico** (Opus, `playbook_diagnostico.md`): entrada = DADOS DO LEAD + TRANSCRIÇÃO. Saída = blocos 1–8 + **DECISOES_C1**. Extrair DECISOES_C1.
2. `fase_atual = 2`. **Agente Estratégia** (`playbook_estrategia.md`): entrada = DECISOES_C1 + TRANSCRIÇÃO + DADOS DO LEAD. Saída = blocos 9–15 + **DECISOES_C2**. Extrair DECISOES_C2.
3. `fase_atual = 3`. **Agente Execução** (`playbook_execucao.md`): entrada = DECISOES_C1 + DECISOES_C2 + DADOS DO LEAD. Saída = blocos 16–21 + **DECISOES_C3**.
4. **Montar** o playbook (juntar as três fases) → `resultado`. Guardar DECISOES em `decisoes_c*`. `status = pronto`.
5. Em **qualquer erro**: `status = erro`, mensagem curta em `erro`.

A cada passo, `updated_at` é atualizado.

---

## 8. Passar as decisões adiante + montar a entrada (ponto de atenção)

- O serviço **extrai** os blocos `[DECISOES_C1]…[/DECISOES_C1]` (e C2) da saída por padrão de texto (regex).
- A **mensagem do usuário** de cada agente é montada com seções **rotuladas exatamente como os prompts esperam** (seção 13 de cada prompt): `DADOS DO LEAD`, `TRANSCRIÇÃO DA CALL 1`, `DECISÕES DA CHAMADA 1 (DIAGNÓSTICO)`, `DECISÕES DA CHAMADA 2 (ESTRATÉGIA)`. Alinhar os rótulos com os prompts ao implementar.

---

## 9. Modelo (Opus, configurável)

- As chamadas do pipeline usam Opus via `PLAYBOOK_MODEL` (padrão `claude-opus-4-8`). Não assumir `claude-opus-4-7`.

---

## 10. Assíncrono + limitação honesta

- Tarefa em segundo plano **no mesmo processo** (sem fila externa). Job **longo** (3 Opus + busca → minutos). Se o serviço reiniciar no meio, o job fica `processando` parado; a tela mostra "tempo esgotado" após um limite e o usuário **reenvia**. Fila de verdade é assunto futuro.

---

## 11. Prompts em arquivos

- `prompts/playbook_diagnostico.md`, `playbook_estrategia.md`, `playbook_execucao.md` (já criados, conteúdo do Vata). A transcrição, os dados do lead e as decisões entram como **input** (mensagem), não dentro do prompt.

---

## 12. Dono no código

- O serviço usa a chave administrativa (ignora a RLS) → checar o dono em **toda** leitura, gravação e remoção (incluindo o DELETE).

---

## 13. O que NÃO fazer

- NÃO construir a aba do front (P2). NÃO fazer export .docx/.pdf.
- NÃO usar histórico de conversa (Redis). NÃO mexer no chat existente.
