# Etapa 4 — Ligar o buscar_conversa — Design

**Projeto:** Chat IA-Guia — **backend** (projeto novo)
**Versão:** 1.1 (DB8, prefixo, host interno)
**Método:** SDD — deriva do `requisitos.md` (mesma pasta) e orienta o `tasks.md`.

---

## 1. Visão geral

A ferramenta `buscar_conversa` já existe (ficou desligada por falta de `REDIS_URL`). Esta etapa a torna funcional: conecta no Redis no **banco 8** (closers), acha a conversa do lead pela chave, tolera o formato do valor, e trata erros — tudo só leitura.

---

## 2. Conexão (banco dos closers = DB8)

- Cliente de Redis usando o **host/porta** de `REDIS_URL`, selecionando o **banco 8** (via `REDIS_CLOSERS_DB`, padrão 8). A URL informada termina em `/0`, mas os closers estão no DB8 — então o banco é escolhido pela config, não pelo `/0` da URL.
- **Sem senha** (Redis interno, não exposto).
- **Aviso de rede:** `redis://redis:6379` usa o host `redis`, nome interno do Docker da VPS. Só resolve **dentro** dessa rede. Fora dela (máquina local) não conecta — ver seção 7.

---

## 3. Achar a conversa do lead em DB8

- Normalizar o número para `55DDDNUMERO`.
- Procurar a chave em DB8, nesta ordem (primeiro com dado vence):
  1. **`closer:<NUMERO>`** — o formato que o Vata informou.
  2. `aurelio:<NUMERO>` → `marcio:<NUMERO>` → `giba:<NUMERO>` — os prefixos por nome do prompt do Mestre, como reserva.
- Se o diagnóstico (seção 5) mostrar que o prefixo real é só um deles, o código pode ser enxugado para esse.
- (Opcional, se o prefixo real for por nome) usar o **nome-curto do closer logado** a partir do e-mail: `aureliomfranco@vata-dojo.com`→`aurelio`, `marcio_travassos@vata-dojo.com`→`marcio`, `gilberto@vata-dojo.com`→`giba`, para mirar direto a chave certa.

---

## 4. Tolerância de formato do valor

Ler o valor e transformar num **texto de conversa legível**, tentando, nesta ordem:
1. **Texto puro** (string) → usa direto.
2. **JSON** que seja lista de mensagens (itens com autor/papel + conteúdo) → junta em linhas `Quem: texto`.
3. **Lista do Redis** (chave do tipo lista) → lê os itens e junta igual.

---

## 5. Diagnóstico contra o dado real (uma vez)

Com acesso ao Redis, **listar algumas chaves do DB8** (varredura leve) para confirmar: (a) o prefixo real (`closer:` ou nome) e (b) o formato do valor. Ajustar o leitor ao que existe — não supor. Mesma disciplina do backfill do Mapa de Calor.

---

## 6. Erros (tratáveis, alinhados ao prompt)

- Chave não existe/vazia → "sem histórico desse lead com [closer]".
- Tentou tudo e nada → "esse lead não aparece no histórico".
- Redis inalcançável → mensagem curta de indisponibilidade.
- Sempre texto curto; a IA contorna; o serviço não cai.

---

## 7. Como testar este caso (por causa do host interno)

- **Local (encanamento):** como a máquina local não alcança `redis://redis:6379`, rodar um **Redis de mentira** (o próprio Claude Code pode subir um Redis local), pôr uma chave de exemplo `closer:5547999998888` com uma conversa de teste, apontar `REDIS_URL` pra esse Redis local e o banco pra 8, e confirmar que a ferramenta lê, tolera o formato e o Mestre responde. Isso valida o **código**, não o dado real.
- **Real (conversa de verdade):** acontece quando o serviço de chat roda **na VPS, na mesma rede do Redis** (passo de container) — aí `REDIS_URL=redis://redis:6379` com DB8 lê as conversas reais. Alternativa intermediária: um túnel até o Redis da VPS, se ele estiver acessível.

---

## 8. O que NÃO fazer

- NÃO escrever no Redis. NÃO construir a captura das conversas.
- NÃO mexer no resto da Etapa 4 (Clint, apagar, memória).
