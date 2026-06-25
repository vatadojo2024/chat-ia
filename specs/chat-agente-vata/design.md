# Agente do Vata no chat — Design

**Serviço:** chat-copiloto (Python/FastAPI na VPS)
**Versão:** 1.0
**Método:** SDD — deriva do `requisitos.md` (mesma pasta).

---

## 0. Verificar ANTES de implementar (não assumir)

O Claude Code DEVE inspecionar o serviço e **reportar** isto antes de escrever código:
1. Como o chat seleciona o system prompt hoje (por papel? onde, qual arquivo/função?).
2. Se o endpoint de chat **já tem ciclo de tool-use** (function-calling) ligado, ou se hoje é só `system + mensagens` sem tools.
3. Se a resposta do chat é **streaming** ou de uma vez só.
4. Qual o `max_tokens` usado hoje na chamada do chat.
5. Assinatura e localização de `buscar_campos_lead` (aceita email e telefone? o que retorna?).

A implementação abaixo se ajusta ao que for encontrado. O item (2) é o pré-requisito crítico do RF-04.

---

## 1. Visão geral

Três mudanças, todas no serviço de chat:
- **Roteamento por e-mail** para carregar o prompt do Vata.
- **Ciclo de tool-use** no endpoint de chat, com a tool `buscar_lead` — disponível **apenas** para o agente do Vata (Hana/Mestre seguem sem tools).
- **Teto de saída** generoso para o agente do Vata (playbook).

---

## 2. Roteamento por e-mail (RF-01, RF-02)

- No ponto onde o chat decide qual prompt carregar, adicionar: se o **e-mail** do usuário autenticado == `contato@vatadojo.com.br` → carregar `prompts/vata.md`.
- Caso contrário, manter exatamente a lógica atual (sdr→Hana, closer→Mestre).
- O e-mail vem da sessão autenticada (Supabase Auth/JWT) — usar a mesma fonte que o chat já usa pra saber o papel.
- Colocar o arquivo do prompt em `prompts/vata.md` (conteúdo = `prompt_vata_call_de_plano.md` adaptado).

---

## 3. Tool `buscar_lead` (RF-03, RF-04, RNF-04)

### 3.1 Schema (o que o modelo enxerga)
- Nome: `buscar_lead`.
- Descrição: "Busca o registro do lead no CRM Clint. Forneça email OU telefone (pelo menos um)."
- Parâmetros: `email` (string, opcional), `telefone` (string, opcional). Pelo menos um obrigatório.
- O modelo **não** vê URL nem endpoint.

### 3.2 Implementação (wrapper)
- Recebe `email` e/ou `telefone`.
- **Normaliza o telefone** dentro da tool: só dígitos; se 10–11 dígitos sem 55, prefixar 55; alvo 13 dígitos. (mesma regra que estava no prompt antigo, agora no código)
- Chama `buscar_campos_lead` (reuso) com o que tiver — preferir email se ambos vierem.
- Retorno:
  - Lead encontrado → o registro do lead (mesmo formato que o pipeline já usa).
  - Não encontrado → um objeto claro tipo `{ "encontrado": false }` (o agente trata como "não está no CRM"; nunca inventa).
- Erros de rede/Clint → devolver sinal de erro tratável, não derrubar a resposta.

---

## 4. Ciclo de tool-use no chat (RF-04, RNF-01)

- Na chamada ao modelo (Sonnet), passar `tools=[buscar_lead]` **apenas** quando o agente for o do Vata. Hana/Mestre: sem `tools` (comportamento idêntico ao atual).
- Loop:
  1. Enviar `system + histórico + tools`.
  2. Se a resposta contiver `tool_use` → executar `buscar_lead`, anexar o `tool_result` ao histórico da chamada, repetir.
  3. Se a resposta for texto final → devolver ao Vata.
- **Limite de iterações** (ex.: 3–4) para evitar loop infinito; se estourar, responder com o que tem.
- **RNF-01:** os blocos `tool_use`/`tool_result` são internos a este turno — **não** persistir como turnos visíveis; persistir só a mensagem do Vata e o texto final do agente.
- Se o chat for **streaming**: resolver o ciclo de tool-use **antes** de começar a transmitir o texto final (o streaming vale só pra resposta final).

---

## 5. Teto de saída para o playbook (RF-05)

- O agente do Vata pode gerar playbook → usar um `max_tokens` **maior** para esse agente do que o usado num turno comum de chat (o suficiente para o núcleo do playbook).
- O prompt já tem a seção "ORÇAMENTO DE SAÍDA" instruindo o modelo a entregar o núcleo primeiro e oferecer o resto — então não é preciso lógica extra de paginação; basta o teto não ser apertado.

---

## 6. O que NÃO fazer

- NÃO mexer em Hana (`prompts/sdr.md`) e Mestre (`prompts/closer.md`).
- NÃO mexer no pipeline do playbook (P1/P2/Opus).
- NÃO adicionar a tool `buscar_conversa` (v2).
- NÃO rotear Cindy/Jonas para este agente.
