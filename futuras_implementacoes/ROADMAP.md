# Futuras Implementações — Roadmap do IsyShell

Este documento lista funcionalidades planejadas para versões futuras do IsyShell,
organizadas por prioridade e complexidade.

---

## Alta Prioridade

### Alertas de Falha via Discord
**Arquivo base:** `futuras_implementacoes/alerts.py`

Quando um script falha, a API envia automaticamente uma mensagem num canal do Discord
com o nome do script, os parâmetros usados e o erro reportado.

- Configurável por variável de ambiente `DISCORD_WEBHOOK_URL`
- Sem impacto na resposta da API (chamada assíncrona)
- Desligável sem alterar código

**Como implementar:** chamar `enviar_alerta_falha()` em `main.py` após detectar
`status_retorno == "falha"` na rota `/scripts/{id}/executar`.

---

### Autenticação JWT (substituir token fixo)
O token fixo de admin atual não expira e não identifica o usuário que o usa.
JWT (JSON Web Token) resolve isso:

- Token com data de expiração (ex: 24h)
- Renovação automática via refresh token
- Payload com `email` e `plano` embutidos — sem precisar consultar o banco a cada requisição

O FastAPI tem suporte nativo via `python-jose` e `passlib`.

---

### E-mail de boas-vindas e recuperação de senha
Ao cadastrar, enviar um e-mail de confirmação.
Adicionar rota `POST /usuarios/recuperar-senha` que envia link com token temporário.

Bibliotecas: `fastapi-mail` ou integração com SendGrid/Resend.

---

## Média Prioridade

### Execução Agendada (Cron)
Permitir agendar scripts para rodar automaticamente em horários específicos.

```
POST /agendamentos
{
  "script_id": 1,
  "cron": "0 2 * * *",   ← todo dia às 02:00
  "parametros": ["/var/log", "30"]
}
```

Biblioteca sugerida: `APScheduler` — leve e compatível com FastAPI.

---

### Controle de Acesso por Papel (RBAC)
Hoje existem dois papéis: admin e usuário. Adicionar papéis intermediários:

| Papel         | Permissões |
|---|---|
| `visualizador` | Só lê logs e lista scripts |
| `operador`     | Executa scripts, vê seus logs |
| `gerente`      | Tudo do operador + analytics |
| `admin`        | Acesso total |

---

### Upload de Scripts via API
Hoje os scripts .sh precisam ser copiados manualmente para a pasta `scripts/`.
Adicionar rota para upload direto:

```
POST /scripts/upload
Content-Type: multipart/form-data
Body: arquivo .sh + metadados
```

Com validação do conteúdo: rejeitar scripts com comandos proibidos (rm -rf, etc).

---

### Paginação nos endpoints de listagem
Os endpoints `/scripts`, `/logs` e `/usuarios` retornam todos os registros de uma vez.
Adicionar suporte a paginação:

```
GET /logs?pagina=2&por_pagina=20
```

Resposta incluiria `total`, `pagina`, `por_pagina`, `proxima_pagina`.

---

## Baixa Prioridade / Longo Prazo

### Frontend Web (Dashboard)
Interface visual para o painel de analytics e gerenciamento de scripts.

Sugestões de tecnologia: React + Tailwind CSS, ou Next.js.
A API já está pronta — o frontend só precisa consumir os endpoints existentes.

---

### Suporte a Múltiplos Servidores
Hoje a API roda em um único servidor. Evoluir para gerenciar scripts em
vários servidores remotamente:

```
scripts/
├── servidor-sp/
│   └── backup.sh
└── servidor-rj/
    └── limpeza.sh
```

Cada servidor teria seu agente IsyShell; a API central distribuiria os comandos.

---

### Banco de Dados PostgreSQL (para produção)
SQLite é ótimo para desenvolvimento, mas tem limitações em alta concorrência.
Migração para PostgreSQL com SQLAlchemy:

- Connection pooling nativo
- Suporte a múltiplas instâncias da API em paralelo (horizontal scaling)
- Queries mais robustas para analytics com volume alto

---

### Integração com Grafana / Prometheus
Exportar métricas no formato Prometheus para visualização em dashboards Grafana:

```
GET /metrics   ← endpoint no formato Prometheus
```

Permitiria alertas automáticos (ex: taxa de falha > 10% nos últimos 5 minutos).

---

### Versionamento de Scripts
Guardar o histórico de versões de cada script:

- Ver qual versão rodou em cada execução do log
- Rollback para versão anterior com um clique
- Diff visual entre versões

---

### Execução Assíncrona com Fila
Scripts demorados (backup de banco, compressão de arquivos) travam a requisição
por até 30 segundos. Com uma fila:

```
POST /scripts/1/executar → retorna imediatamente: {"job_id": "abc123"}
GET  /jobs/abc123         → retorna status: "em andamento" ou resultado
```

Bibliotecas: Celery + Redis, ou implementação leve com Python `asyncio`.
