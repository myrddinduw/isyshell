# Roadmap — Futuras Implementacoes

---

## Alta Prioridade

### Alertas de Falha via Webhook
**Arquivo:** `futuras_implementacoes/alerts.py`

Envia um POST para qualquer URL configurada em `ALERT_WEBHOOK_URL` quando um script falha.
Compativel com Discord, Slack, Teams ou endpoint proprio.
Para ativar: chamar `enviar_alerta_falha()` em `main.py` apos detectar `status_retorno == "falha"`.

---

### Autenticacao JWT
Substituir o token fixo de admin por JWT com data de expiracao e refresh token.
O FastAPI tem suporte nativo via `python-jose` e `passlib`.

---

### Recuperacao de Senha
Rota `POST /usuarios/recuperar-senha` que envia link com token temporario por e-mail.
Bibliotecas sugeridas: `fastapi-mail` ou integracao com SendGrid.

---

## Media Prioridade

### Execucao Agendada (Cron)
Agendar scripts para rodar automaticamente em horarios definidos.
Biblioteca sugerida: `APScheduler` — leve e compativel com FastAPI.

---

### Controle de Acesso por Papel (RBAC)
Adicionar papeis intermediarios alem de admin/usuario:
`visualizador`, `operador`, `gerente`.

---

### Upload de Scripts via API
Rota `POST /scripts/upload` para enviar arquivos `.sh` diretamente pela API,
com validacao de conteudo para rejeitar comandos proibidos.

---

### Paginacao
Adicionar `?pagina=` e `?por_pagina=` nos endpoints `/scripts`, `/logs` e `/usuarios`.

---

## Longo Prazo

### Frontend Web
Interface visual para o painel de analytics e gerenciamento de scripts.
A API ja esta pronta para ser consumida.

---

### Suporte a Multiplos Servidores
Cada servidor rodaria um agente IsyShell; a API central distribuiria os comandos.

---

### Banco PostgreSQL
Migracao do SQLite para PostgreSQL via SQLAlchemy com connection pooling
para suportar alta concorrencia em producao.

---

### Integracao Grafana / Prometheus
Exportar metricas no formato Prometheus via `GET /metrics`
para visualizacao em dashboards Grafana e alertas automaticos.

---

### Versionamento de Scripts
Historico de versoes de cada script com rollback e diff entre versoes.

---

### Execucao Assincrona com Fila
Scripts de longa duracao retornam imediatamente um `job_id`.
O resultado e consultado depois via `GET /jobs/{job_id}`.
Bibliotecas sugeridas: Celery + Redis.
