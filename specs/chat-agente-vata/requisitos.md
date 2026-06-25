# Agente do Vata no chat (Estrategista de Call de Plano) — Requisitos

**Serviço:** chat-copiloto (Python/FastAPI na VPS, https://chat-api.infradojo.pro)
**Versão:** 1.0
**Método:** SDD — este documento é a fonte da verdade.

---

## Objetivo

Adicionar ao chat-copiloto um **terceiro agente**: o **Estrategista de Call de Plano (Call 2)** do Vata. É **exclusivo do login do Vata**. Ele conversa por padrão, monta playbook quando pedido, e pode **buscar o registro do lead no Clint** por conta própria através de uma tool.

Hoje o chat tem dois agentes (Hana = SDR, Mestre = closer). Este é o do Vata.

---

## Glossário (termos técnicos em português claro)

- **Agente / papel:** a "personalidade" que o chat assume conforme quem está logado. Hoje muda pelo cargo da pessoa (SDR ou closer).
- **System prompt:** o texto de instrução que define o agente. Mora num arquivo `.md` (ex.: `prompts/sdr.md`).
- **Tool (ferramenta):** uma capacidade que o modelo pode acionar sozinho durante a conversa — aqui, buscar os dados de um lead no Clint.
- **Ciclo de tool-use:** o vai-e-volta em que o modelo **pede** a ferramenta, o serviço **executa** e devolve o resultado, e o modelo **continua** a resposta já com o dado em mãos. Sem esse ciclo, uma tool descrita no prompt não funciona de verdade.

---

## Requisitos

### RF-01 — Roteamento por e-mail (exclusivo do Vata)
- Quando o usuário autenticado for **`contato@vatadojo.com.br`**, o chat DEVE carregar o system prompt do Vata (`prompts/vata.md` — o arquivo `prompt_vata_call_de_plano.md` já adaptado).
- O roteamento é pelo **e-mail**, não pelo papel `admin` — porque o papel admin inclui outras pessoas que estão fora de escopo.

### RF-02 — Não alterar os agentes existentes
- Hana (`prompts/sdr.md`) e Mestre (`prompts/closer.md`) DEVEM continuar idênticos, com o mesmo comportamento.

### RF-03 — Tool `buscar_lead`
- O agente do Vata DEVE ter uma tool **`buscar_lead`** que busca o registro do lead no Clint, aceitando **email OU telefone** (pelo menos um).
- Reusar a função **`buscar_campos_lead`** que já existe (em `app/clint.py`, usada no pipeline do playbook). A normalização do telefone fica **na tool/serviço**, não no modelo.

### RF-04 — O agente usa a tool por conta própria
- O agente DEVE conseguir acionar `buscar_lead` sozinho quando precisar de dados do lead (ciclo de tool-use), executar, e responder **já interpretando** o resultado — sem despejar o JSON cru pro Vata.
- Em lead não encontrado, a tool DEVE devolver um sinal claro de "não encontrado" (o agente não inventa dados).

### RF-05 — Playbook inline
- Quando o Vata pedir o playbook e houver material suficiente, o agente monta o playbook **na própria conversa** (formato da seção 12 do prompt). Isso é separado da aba dedicada de playbook (P2) — são caminhos diferentes, ambos válidos.
- Como o playbook é grande, o teto de saída do agente do Vata DEVE ser generoso o bastante pra caber pelo menos o **núcleo** (o prompt já instrui o modelo a entregar núcleo primeiro se não couber tudo).

---

## Requisitos não-funcionais

- **RNF-01 — Histórico limpo:** os blocos internos do ciclo de tool-use (pedido e resultado da ferramenta) NÃO devem virar turnos visíveis na conversa; só a mensagem do Vata e a resposta final do agente são persistidas.
- **RNF-02 — Não tocar no pipeline do playbook** (motor P1 / aba P2 / chamadas Opus). Este agente roda no **chat** (Sonnet), não no pipeline.
- **RNF-03 — Modelo:** o chat usa `claude-sonnet-4-6`. Tool-use funciona nele. (O parâmetro `temperature` é normal no Sonnet — a descontinuação era só no Opus.)
- **RNF-04 — Segredo:** a tool não expõe URL/endpoint do Clint pro modelo; o modelo só passa email/telefone.

---

## Fora de escopo (não fazer agora)

- A tool **`buscar_conversa`** (histórico WhatsApp/Discord) — fica para uma v2.
- Agentes para **Cindy e Jonas** (papel admin) — fora por enquanto.
- A **aba de playbook (P2)** no front — é outra frente.
- Qualquer mudança nos agentes Hana e Mestre.
