# Chat IA-Guia — Guia do Projeto

Documento de visão e roadmap do recurso de Chat IA do painel comercial Vata Dojo. Não é especificação técnica — é o mapa do projeto, para alinhamento e controle. As specs detalhadas de cada etapa moram em pastas próprias (`chat-ia-etapa-XX-.../`).

Versão: 1.0 — junho/2026

---

## 1. O que estamos construindo (o objetivo)

Um **espaço de chat dentro do painel comercial onde cada pessoa conversa com o seu guia de IA** — um agente por papel: admin (Vata/Cindy), closer e SDR.

Os guias já existem hoje como prompts (espalhados em Discord/n8n). O objetivo deste projeto é **trazer esses guias para dentro do painel**, num lugar só, com **continuidade** (histórico das conversas + memória) e **contexto** (lendo arquivos relevantes e o Clint, só leitura).

Em uma frase: **dar a cada papel um copiloto de IA para o trabalho do dia a dia**, que lembra do que já foi conversado e entende o contexto da operação.

**Como se encaixa com o Mapa de Calor:** o Mapa de Calor diz *quem atender primeiro e por quê* (prioriza leads). O Chat IA é um *parceiro de raciocínio por papel* — ajuda a pensar, tirar dúvida, preparar abordagem. Um ranqueia; o outro orienta. São complementares, não a mesma coisa.

---

## 2. A arquitetura, em três peças

Mesma lógica do Mapa de Calor: três peças funcionais e um banco que as conecta.

### Entrada
O que o usuário manda: o texto que ele digita no chat. No futuro, também arquivos anexados.

### Cérebro
Um **serviço próprio em Python (FastAPI)**. É o único lugar com a inteligência do chat. Responsável por:
- Saber quem é o usuário e qual o papel dele (valida o login).
- Escolher o prompt certo conforme o papel (admin/closer/SDR).
- Chamar a IA para responder.
- Ler arquivos e o Clint (somente leitura) quando precisar de contexto.
- Manter a memória da conversa (resumo rolante).
- Guardar tudo no banco.

Toda regra mora aqui. A tela não decide nada.

### Saída
A **tela de chat** que o usuário abre no painel (já construída na Etapa 1, dentro do front). Ela só apresenta: mostra as mensagens, o "pensando…", a resposta. Sem inteligência.

### Banco
**Supabase (Postgres)** — a **mesma instância** do Mapa de Calor. Guarda as conversas, as mensagens e a memória.

---

## 3. As decisões estruturantes (e por quê)

- **Serviço separado, não acoplado à API do Mapa de Calor.** O chat roda como um **container próprio na VPS**, compartilhando o mesmo docker-compose/Traefik que já existe, mas com vida própria. Razão: o chat tem um ciclo diferente (uma resposta pode demorar minutos) e não deve arriscar a API que serve o ranking. Código e deploy novos e separados.

- **Banco compartilhado (mesma Supabase).** Isso não contradiz o "é algo novo": separação de código/deploy é um eixo; banco é outro. Tem que ser a mesma Supabase porque o **login é o mesmo** — closers/SDRs/admins entram com as mesmas contas, e a segurança (RLS por `auth.uid()`) e a validação do login dependem do mesmo Auth. Um Supabase separado obrigaria contas novas e quebraria o login.

- **Assíncrono.** A resposta da IA pode demorar. Em vez de travar a tela esperando, o serviço grava a mensagem como "pendente", processa, e a tela busca quando fica "pronta". É o que dá a sensação de chat sem prender a interface.

- **Memória por resumo rolante.** Conversa longa e contínua sem estourar o limite de contexto da IA: o serviço vai resumindo o que ficou para trás e mantém o recente em detalhe.

- **IA geral, não reconhece lead específico.** O chat é um **guia de papel**, não um analisador de lead — analisar lead é o trabalho do Mapa de Calor. Isso mantém os dois sistemas com fronteiras claras.

- **3 agentes = 1 serviço, prompt trocado por papel.** Não são três sistemas; é o mesmo serviço escolhendo o prompt conforme quem está logado. Os prompts já existem.

---

## 4. O roadmap em 9 etapas

A regra que orienta tudo: **cada etapa entrega algo testável isoladamente**. Se algo quebra numa etapa, o problema só pode estar no que ela trouxe — porque tudo antes já foi testado. Nunca debugar duas camadas novas ao mesmo tempo.

### Fase A — Fundação (tela)
**Etapa 1 — Tela mock.** A tela de chat no painel, com respostas fictícias (sem backend). Serve para validar o visual e o fluxo de envio. *Mora no front.* **(CONCLUÍDA.)**

### Fase B — Dados
**Etapa 2 — Tabelas no Supabase.** As duas tabelas (conversas e mensagens), com segurança (RLS), ligadas ao login. Suporta várias conversas, título por IA e busca (o schema já fica pronto para isso). *Primeiro artefato do projeto novo.* **(EM ANDAMENTO.)**

### Fase C — Esqueleto do cérebro
**Etapa 3 — Serviço Python no ar.** O serviço FastAPI sobe, responde num `/health`, e valida o mesmo login do Supabase para saber quem é o usuário e o papel. Sem inteligência ainda.

### Fase D — Inteligência
**Etapa 4 — Chat real.** O serviço recebe a mensagem, escolhe o prompt do papel, chama a IA e grava a resposta.
**Etapa 5 — Ligar o front.** A tela troca o mock pelo serviço real. **Marco: chat usável ponta a ponta.**

### Fase E — Memória
**Etapa 6 — Resumo rolante.** O serviço passa a resumir o histórico, dando memória de conversa longa.

### Fase F — Contexto
**Etapa 7 — Leitura de arquivo.** A IA passa a ler arquivos para responder com mais contexto.
**Etapa 8 — Ferramenta Clint (só leitura).** A IA consulta o Clint para buscar informação, sem nunca escrever.

### Fase G — Produção
**Etapa 9 — Container + Traefik.** O serviço é empacotado e sobe na VPS, no mesmo docker-compose/Traefik existente.

---

## 5. O que está fora deste projeto

- **Não duplica o Mapa de Calor.** Não ranqueia leads, não analisa lead específico, não calcula score.
- **Sem compartilhamento entre usuários, pastas, arquivamento ou tags.** (Título por IA e busca, sim — estão no escopo.)
- **Não treina IA própria.** Usa a API de IA existente.
- **A tela em si** já foi entregue na Etapa 1; este projeto novo é o backend do chat.

---

## 6. Estado atual

| Peça | Status | Onde |
|---|---|---|
| Tela (mock) | **Concluída** | Front (Etapa 1) |
| Tabelas (Supabase) | **Specs prontas, a aplicar** | Projeto novo (Etapa 2) |
| Serviço Python | Planejado | Projeto novo (Etapa 3+) |
| Front ligado ao real | Planejado | Etapa 5 (marco) |
| Memória / arquivo / Clint / deploy | Planejado | Etapas 6–9 |

---

## 7. Princípios orientadores

- **Cada etapa estabiliza algo antes da próxima começar.** Nunca debugar duas camadas novas ao mesmo tempo.
- **Toda regra mora no cérebro (o serviço Python).** A tela só apresenta.
- **Segurança em dois lugares:** RLS no banco *e* validação no serviço. Divergência entre eles é falha silenciosa.
- **Código novo e separado; banco compartilhado** — por necessidade do login.
- **Mock-first no front:** a tela trabalha com dados fictícios até o serviço real estar pronto (Etapa 5).
- **Fronteira clara com o Mapa de Calor:** o chat orienta por papel; não analisa lead. Quem analisa lead é o Mapa de Calor.

---

## 8. Resumo de uma página

**Produto:** um chat no painel onde cada papel (admin/closer/SDR) conversa com o seu guia de IA, com histórico, memória e contexto (arquivos + Clint só leitura).

**Arquitetura:** três peças (entrada → cérebro → saída) conectadas pelo banco. O cérebro é um serviço Python próprio, separado da API do Mapa de Calor, rodando em container próprio na VPS. Banco: a mesma Supabase (login compartilhado).

**Caminho:** 9 etapas, cada uma testável. Tela → tabelas → esqueleto → inteligência → ligar front → memória → arquivo → Clint → deploy.

**Estado:** tela feita; tabelas a aplicar; serviço e demais etapas planejados.

**Princípio:** nunca construir duas camadas novas sem testar; toda regra no cérebro; fronteira clara com o Mapa de Calor.
