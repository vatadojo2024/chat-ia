# Etapa 2 — Tabelas no Supabase — Requisitos

**Projeto:** Chat IA-Guia — **backend** (projeto NOVO, separado do front)
**Etapa:** 2 de 9 (Fase B — Fundação de dados)
**Versão:** 1.1
**Método:** SDD — este documento é a fonte da verdade. O código (a migration) é derivado dele.

---

## Objetivo da etapa

Criar no Supabase as **duas tabelas** que guardam as conversas do chat e suas mensagens, ligadas ao usuário logado, com **segurança de acesso (RLS)** para que cada pessoa veja só as próprias conversas. Nenhum serviço, API ou tela nesta etapa — só o banco.

**Onde isto vive:** num **projeto novo** (pasta/repo próprios), separado do front. A tela do chat (Etapa 1) já existe no front; o que começa aqui é o **backend** do chat. Esta migration é o **primeiro artefato** do projeto novo. As tabelas, porém, ficam na **MESMA instância Supabase** do Mapa de Calor — porque o login é compartilhado (mesmas contas, mesmo Auth, mesma RLS por `auth.uid()`).

**Escopo:** o sistema suporta várias conversas por usuário, **título gerado por IA** e **busca**. NÃO tem compartilhamento entre usuários, pastas, arquivamento nem tags. (Título-por-IA e busca: o schema dá suporte agora; a lógica de gerar título e a tela de busca vêm em etapas próprias.)

---

## Glossário rápido (em português claro)

- **Supabase:** o banco de dados Postgres do projeto (o mesmo que o Mapa de Calor já usa).
- **Projeto novo:** uma pasta/repositório separado, só do chat — não é o front nem o backend do Mapa de Calor.
- **Tabela:** uma "planilha" do banco; cada linha é um registro.
- **Conversa:** uma thread de chat de um usuário com o seu agente. Um usuário pode ter várias.
- **Mensagem:** uma fala dentro de uma conversa — do usuário ou da IA.
- **Migration:** um arquivo de SQL que cria/altera tabelas, versionado (como os 0009–0012 do Mapa de Calor).
- **RLS (segurança em nível de linha):** regra do banco que limita cada usuário a ver só as suas próprias linhas.
- **service_role:** a chave administrativa do Supabase; ignora a RLS. Será usada pelo serviço de IA (etapas futuras) para escrever.
- **auth.uid():** dentro da RLS, o identificador do usuário logado. É como o banco sabe "de quem é esta linha".
- **Busca:** procurar conversas/mensagens por texto (título e conteúdo). Aqui criamos só o índice que torna isso rápido.
- **Papel:** a função do usuário (admin/gestor/closer/sdr); define com qual agente a conversa é.
- **Autor:** quem escreveu a mensagem (usuário ou IA). Termo separado de "papel" de propósito.

---

## Requisitos

### RF-01 — Tabela de conversas

**Como** sistema,
**quero** uma tabela que guarde cada conversa de chat,
**para** organizar as mensagens por thread e por dono.

Critérios de aceite:
- QUANDO a migration rodar ENTÃO o sistema DEVE criar a tabela de conversas com, no mínimo: identificador próprio, dono (usuário), papel (qual agente), título, resumo, marcador de até onde resumiu, e datas de criação/atualização.
- O sistema DEVE usar um nome de tabela próprio que NÃO colida com tabelas existentes do Mapa de Calor.

### RF-02 — Tabela de mensagens

**Como** sistema,
**quero** uma tabela que guarde cada mensagem,
**para** reconstruir a conversa em ordem.

Critérios de aceite:
- QUANDO a migration rodar ENTÃO o sistema DEVE criar a tabela de mensagens com, no mínimo: identificador próprio, referência à conversa, autor (`usuario`|`ia`), conteúdo, status (`pendente`|`pronta`|`erro`), anexos e data de criação.
- QUANDO uma conversa for apagada ENTÃO o sistema DEVE apagar as mensagens dela junto (cascata).
- Os campos DEVEM corresponder ao contrato definido na Etapa 1 (`autor`, `conteudo`, `status`, `anexos`).

### RF-03 — Cada usuário só acessa o que é seu (RLS)

**Como** usuário,
**quero** que minhas conversas sejam privadas,
**para** que ninguém veja meu histórico.

Critérios de aceite:
- ENQUANTO a RLS estiver ativa, um usuário DEVE conseguir ler/criar/alterar/apagar apenas conversas onde ele é o dono (`user_id = auth.uid()`).
- ENQUANTO a RLS estiver ativa, um usuário DEVE acessar apenas mensagens de conversas que são dele.
- QUANDO um acesso usar a chave service_role (o serviço de IA, etapas futuras) ENTÃO ele PODE escrever sem ser barrado pela RLS.

### RF-04 — Múltiplas conversas por usuário

**Como** usuário,
**quero** poder ter mais de uma conversa,
**para** separar assuntos sem perder histórico.

Critérios de aceite:
- O modelo DEVE permitir que um mesmo usuário tenha N conversas, cada uma com suas mensagens.
- O sistema DEVE permitir listar as conversas de um usuário ordenadas pela mais recente.

### RF-05 — Resumo e marcador (preparados para a memória, vazios agora)

**Como** desenvolvedor,
**quero** os campos de resumo já no schema,
**para** a etapa de memória (Etapa 6) não exigir nova migration.

Critérios de aceite:
- A tabela de conversas DEVE ter um campo de resumo (texto, nulo por padrão) e um marcador de até onde o resumo cobre.
- Nesta etapa esses campos ficam VAZIOS; nenhuma lógica de resumo é implementada aqui.

### RF-06 — Anexos como campo simples (previsto para arquivo, vazio agora)

**Como** desenvolvedor,
**quero** o campo de anexos já previsto na mensagem,
**para** a etapa de arquivo (Fase F) não mudar o schema.

Critérios de aceite:
- A mensagem DEVE ter um campo de anexos no formato de lista (jsonb), com padrão vazio.
- Nesta etapa não há upload; o campo só existe, vazio. NÃO criar tabela separada de anexos.

### RF-07 — Domínios controlados

**Como** sistema,
**quero** valores controlados nos campos categóricos,
**para** evitar dado inválido.

Critérios de aceite:
- `papel` DEVE aceitar apenas `admin`, `gestor`, `closer`, `sdr` (CHECK ou enum).
- `autor` DEVE aceitar apenas `usuario`, `ia`.
- `status` DEVE aceitar apenas `pendente`, `pronta`, `erro`.
- Identificadores DEVEM ser uuid.

### RF-08 — Suporte a título gerado por IA

**Como** usuário,
**quero** que cada conversa ganhe um título automático,
**para** reconhecer minhas conversas na lista sem nomeá-las à mão.

Critérios de aceite:
- A tabela de conversas DEVE ter o campo `titulo` (texto, nulo permitido). `titulo` nulo significa "ainda sem título".
- Nesta etapa NÃO se gera título (isso é lógica de uma etapa futura); o schema apenas suporta o campo ser preenchido depois pela IA.

### RF-09 — Suporte a busca por texto

**Como** usuário,
**quero** buscar nas minhas conversas,
**para** reencontrar onde falei de um assunto.

Critérios de aceite:
- O schema DEVE permitir busca eficiente por texto no título da conversa e no conteúdo das mensagens (índice apropriado criado nesta etapa).
- Nesta etapa NÃO há endpoint nem tela de busca (vêm em etapa futura); só o índice que a torna viável.

---

## Requisitos não-funcionais

- **RNF-01 — Migration versionada e idempotente:** seguir o padrão das migrations do Mapa de Calor (0009–0012); rodar duas vezes não dá erro nem duplica.
- **RNF-02 — Projeto novo, mesma Supabase:** a migration vive no projeto novo do chat (pasta/repo próprios), mas é aplicada na MESMA instância Supabase do Mapa de Calor. Nomes de tabela próprios, sem colidir com `leads`, `users`, etc.
- **RNF-03 — Coerência de segurança:** RLS ativa nas duas tabelas; o serviço de IA usará service_role para escrever. A RLS protege qualquer leitura direta do front.
- **RNF-04 — Não tocar no que existe:** não alterar nem apagar nenhuma tabela/coluna do schema atual do Mapa de Calor.

---

## Fora de escopo (não fazer nesta etapa)

- Serviço Python, API ou tela (vêm nas Etapas 3, 4, 5).
- Lógica de **gerar** título por IA (etapa futura) — aqui só o campo.
- Endpoint/tela de **busca** (etapa futura) — aqui só o índice.
- Lógica de resumo rolante (Etapa 6) — aqui só os campos.
- Upload/leitura de arquivo (Fase F) — aqui só o campo de anexos.
- Compartilhamento entre usuários, pastas, arquivamento, tags.
