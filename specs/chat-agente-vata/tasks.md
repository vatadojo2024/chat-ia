# Agente do Vata no chat — Tarefas

**Serviço:** chat-copiloto (Python/FastAPI na VPS)
**Versão:** 1.0
**Método:** SDD — deriva do `requisitos.md` e do `design.md` (mesma pasta).

**Ordem:** T-01 (investigar e reportar) ANTES de tudo. Depois T-02→T-05. T-06 valida. Não construir nada de "Fora de escopo".

---

## T-01 — Investigar e reportar (sem código ainda)
- [ ] Reportar: como o chat seleciona o prompt hoje (por papel; arquivo/função).
- [ ] Reportar: o endpoint de chat já tem ciclo de tool-use (function-calling)? Ou é só `system + mensagens`?
- [ ] Reportar: a resposta do chat é streaming ou de uma vez?
- [ ] Reportar: `max_tokens` atual do chat.
- [ ] Reportar: assinatura e local de `buscar_campos_lead` (aceita email e telefone? retorno?).
- **Pronto quando:** os 5 itens reportados. **Parar e confirmar** antes de implementar (o item 2 decide o tamanho da T-04).

## T-02 — Prompt do Vata + roteamento por e-mail
- [ ] Adicionar `prompts/vata.md` (conteúdo do prompt adaptado).
- [ ] No seletor de prompt: se e-mail do usuário == `contato@vatadojo.com.br` → carregar `prompts/vata.md`; senão, lógica atual.
- **Cobre:** RF-01, RF-02.
- **Pronto quando:** logado como Vata, o chat usa o prompt do Vata; logado como SDR/closer, nada mudou.

## T-03 — Tool `buscar_lead` (implementação)
- [ ] Criar a tool `buscar_lead(email?, telefone?)`: normaliza o telefone no código (13 dígitos, 55 na frente), chama `buscar_campos_lead` (preferindo email se ambos), retorna o registro ou `{ "encontrado": false }`. Erro de rede → sinal tratável.
- **Cobre:** RF-03, RNF-04.
- **Pronto quando:** chamar `buscar_lead` com um email real devolve o registro do lead; com um inexistente devolve "não encontrado".

## T-04 — Ciclo de tool-use no chat (só p/ o agente do Vata)
- [ ] Passar `tools=[buscar_lead]` na chamada do modelo **apenas** para o agente do Vata (Hana/Mestre sem tools).
- [ ] Implementar o loop tool_use→tool_result→continuar, com limite de iterações (3–4).
- [ ] Não persistir os blocos internos de tool-use como turnos visíveis (RNF-01).
- [ ] Se for streaming, resolver o ciclo antes de transmitir a resposta final.
- **Cobre:** RF-04, RNF-01.
- **Pronto quando:** o Vata manda um email de lead e o agente chama a tool sozinho, recebe o dado e responde interpretando (sem JSON cru). Hana/Mestre seguem idênticos.

## T-05 — Teto de saída do agente do Vata
- [ ] Usar `max_tokens` generoso para o agente do Vata (caber o núcleo do playbook); manter o atual para os outros.
- **Cobre:** RF-05.
- **Pronto quando:** pedir "monta o playbook" (com material) gera o playbook inline sem cortar no meio do núcleo.

## T-06 — Validar
- [ ] Vata loga no chat → agente responde como estrategista (voz do prompt).
- [ ] Vata manda email/telefone de um lead → agente aciona `buscar_lead`, interpreta e responde; em lead inexistente, diz que não achou (sem inventar).
- [ ] Vata pede playbook com material → monta inline (núcleo ao menos).
- [ ] SDR e closer logam → Hana e Mestre idênticos ao de antes.
- **Cobre:** todos os RF.

---

## Pré-requisitos de teste
- Deploy na VPS após as mudanças. **Se mexer em variável de ambiente, recriar o container com `--force-recreate`** (reiniciar só não pega env nova).
- Login do **Vata** (`contato@vatadojo.com.br`) e de um **SDR/closer** para o teste de não-regressão.
- Um **email de lead real** que exista no Clint, para exercitar a tool.

## Critério de pronto da etapa
- [ ] Vata tem o agente exclusivo, com a tool `buscar_lead` funcionando no ciclo de tool-use (RF-01/03/04).
- [ ] Playbook inline funciona (RF-05).
- [ ] Hana/Mestre intactos (RF-02); pipeline do playbook intocado (RNF-02).
- [ ] `buscar_conversa`, Cindy/Jonas e a aba P2 ficaram de fora (escopo).
