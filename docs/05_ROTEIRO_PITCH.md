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
> A arquitetura tem 5 camadas: a **API FastAPI** que recebe as requisições, um
> **módulo de autenticação** com token no cabeçalho HTTP, um **executor seguro**
> que usa subprocess sem shell=True — isso bloqueia command injection —,
> um **banco SQLite** que registra cada execução automaticamente, e tudo rodando
> dentro de um **container Docker** com volume para os scripts."

*(aqui você pode mostrar o diagrama em diagrama_arquitetura.md)*

---

### BLOCO 3 — Demo ao vivo (30 segundos)

**Sequência recomendada:**
1. `docker-compose up` — mostrar o container subindo
2. Abrir `http://localhost:8000/docs` — mostrar o Swagger automático
3. No Swagger: `GET /health` — API respondendo
4. `POST /scripts` — cadastrar o limpar_logs.sh
5. `POST /scripts/1/executar` — executar e mostrar o JSON com stdout
6. `GET /logs` — mostrar o registro de auditoria gerado automaticamente

---

### BLOCO 4 — Diferencial (40 segundos)

> "Além dos requisitos obrigatórios, implementamos um **alerta via Webhook do
> Discord**: quando um script falha, a API dispara automaticamente uma mensagem
> no canal de monitoramento da equipe, com o nome do script, os parâmetros
> usados e o erro reportado.
>
> Esse recurso é configurável por variável de ambiente — uma linha no
> docker-compose.yml — e pode ser desligado sem alterar código.
> Isso porque entendemos que numa operação real, tempo de resposta a falhas
> é crítico."

---

### BLOCO 5 — Próximos Passos (30 segundos)

> "Com mais tempo, evoluiríamos para: autenticação com JWT (mais robusta que
> token fixo), suporte a execução agendada (cron), interface web para o painel
> de auditoria, e integração com sistemas de monitoramento como Grafana ou
> Prometheus. O projeto está estruturado para crescer — cada módulo é independente
> e documentado para facilitar a evolução."

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
> Para um hackathon é suficiente, e está coberto pela troca dinâmica via
> `PUT /config/token`. Em produção, substituiríamos por JWT com expiração,
> ou OAuth2 — o FastAPI tem suporte nativo para ambos.

**P: "Como garantem que alguém não vai cadastrar um script malicioso?"**
> O endpoint de cadastro também exige token. Em produção, acrescentaríamos
> um papel de administrador separado e auditoria de cadastros, mas a
> whitelist já garante que só scripts pré-aprovados são executados.

**P: "Por que FastAPI e não Flask ou Django?"**
> FastAPI gera documentação Swagger automática em /docs — isso foi decisivo
> para a demo. É também mais rápido que Flask para APIs assíncronas e mais
> simples que Django para um projeto deste tamanho.

**P: "O que significa subprocess sem shell=True?"**
> shell=True passa o comando para o interpretador /bin/sh, que permite
> encadear comandos com ; e |. Passando o comando como lista, cada argumento
> é tratado como dado — nunca como código. Isso bloqueia command injection.
