# 05 — Roteiro de Pitch (até 4 minutos)

## Estrutura em Blocos de Tempo

---

### BLOCO 1 — Grupo + Problema (20 segundos)

> "Bom dia! Somos o Grupo [nome], do curso de [curso] da FMU.
> O problema que resolvemos é simples: a ISY.ONE administra servidores Linux e,
> hoje, cada tarefa de manutenção exige um técnico conectado via SSH, digitando
> comandos manualmente — sem rastreamento, sem controle de acesso, com risco de
> erro humano."

---

### BLOCO 2 — Solução e Arquitetura (40 segundos)

> "Nossa solução é o **IsyShell**: uma API REST em Python que transforma scripts
> de manutenção em endpoints HTTP seguros.
>
> A arquitetura tem 7 módulos: a **API FastAPI** que recebe as requisições; um
> **módulo de autenticação** que suporta token de admin e tokens por usuário;
> um **executor seguro** com subprocess sem shell=True — bloqueando command injection;
> um **banco SQLite** que registra cada execução com duração e responsável;
> um **sistema de usuários** com planos freemium e rate limiting;
> um módulo de **analytics** com métricas de uso em tempo real;
> e tudo rodando num **container Docker** com volume para os scripts."

*(aqui você pode mostrar o diagrama em diagrama_arquitetura.md)*

---

### BLOCO 3 — Demo ao vivo (40 segundos)

**Sequência recomendada:**
1. `docker-compose up` — mostrar o container subindo
2. Abrir `http://localhost:8000/docs` — mostrar o Swagger automático
3. `GET /health` — API respondendo
4. `POST /usuarios/registrar` — criar conta de cliente
5. `POST /scripts/1/executar` com o token do usuário — executar e mostrar JSON com `duracao_segundos`
6. `GET /logs` — mostrar auditoria automática vinculada ao usuário
7. `GET /analytics/resumo` com token admin — mostrar métricas do dia

---

### BLOCO 4 — Diferenciais (30 segundos)

> "Além dos requisitos obrigatórios, implementamos três diferenciais:
>
> Primeiro, um **sistema freemium completo**: cada cliente tem conta própria,
> com plano free (10 execuções/dia), pro (500/dia) ou enterprise (ilimitado).
> O acesso a scripts específicos também é controlado por plano.
>
> Segundo, um **painel de analytics** para o administrador: scripts mais usados,
> clientes mais ativos, taxa de falha do dia e tempo médio de execução por script.
>
> Terceiro, a **integração com Stripe**: quando um cliente faz upgrade de plano
> no site, o webhook atualiza o banco automaticamente — sem intervenção manual."

---

### BLOCO 5 — Próximos Passos (30 segundos)

> "Com mais tempo, evoluiríamos para: substituir o token fixo por **JWT com
> expiração** — o FastAPI tem suporte nativo; adicionar **execução agendada**
> com cron para scripts recorrentes; um **frontend web** para o painel de
> analytics; **alertas no Discord** quando scripts falham; e suporte a
> **múltiplos servidores** numa mesma instância da API.
> O projeto está estruturado para crescer — cada módulo é independente e
> documentado para facilitar a evolução."

---

## Possíveis Perguntas da Banca

**P: "Por que não usaram um banco de dados mais robusto, como PostgreSQL?"**
> SQLite é suficiente para o volume de execuções num servidor de manutenção.
> Não requer servidor separado, o deploy fica mais simples e a persistência via
> volume Docker resolve o problema de dados. Seria a primeira evolução numa
> versão de produção.

**P: "E se dois scripts forem executados ao mesmo tempo?"**
> O SQLite com `check_same_thread=False` e o FastAPI com uvicorn assíncrono
> lidam com múltiplas requisições simultâneas. Para alta concorrência,
> migraríamos para SQLAlchemy com connection pooling — está documentado como
> próximo passo.

**P: "O token fixo não é inseguro?"**
> Para o hackathon é suficiente, e está coberto pela troca dinâmica via
> `PUT /config/token`. Em produção, substituiríamos por JWT com expiração,
> ou OAuth2 — o FastAPI tem suporte nativo para ambos.

**P: "Como garantem que alguém não vai cadastrar um script malicioso?"**
> O endpoint de cadastro exige token de administrador. Além disso, a whitelist
> garante que só scripts pré-aprovados são executados — o usuário nunca
> informa um caminho de arquivo, apenas um ID.

**P: "Por que FastAPI e não Flask ou Django?"**
> FastAPI gera documentação Swagger automática em /docs — isso foi decisivo
> para a demo. É também mais rápido que Flask para APIs assíncronas e mais
> simples que Django para um projeto deste tamanho.

**P: "O que significa subprocess sem shell=True?"**
> shell=True passa o comando para o interpretador /bin/sh, que permite
> encadear comandos com ; e |. Passando o comando como lista, cada argumento
> é tratado como dado — nunca como código. Isso bloqueia command injection.

**P: "Como funciona o rate limiting do plano free?"**
> Antes de cada execução, contamos quantas vezes aquele usuario_id aparece
> na tabela execucoes com date(horario) igual a hoje. Se atingiu o limite do
> plano, devolvemos HTTP 429. Simples, sem dependências externas.

**P: "Como o Stripe atualiza o plano automaticamente?"**
> O Stripe envia um POST ao nosso endpoint /webhooks/stripe quando o pagamento
> é confirmado. Verificamos o price_id no metadata da sessão, mapeamos para
> o plano correspondente e fazemos UPDATE na tabela usuarios. Em produção,
> validaríamos a assinatura criptográfica do Stripe para garantir autenticidade.
