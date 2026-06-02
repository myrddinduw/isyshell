# IsyShell — API REST para Execução Segura de Scripts Linux

Hackathon FMU + ISY.ONE 2026.1

Substitui o acesso manual via SSH por uma API segura, auditada e containerizada para executar scripts de manutenção em servidores Linux.

---

## Como rodar

```bash
mkdir -p data
docker-compose up --build
```

Acesse a documentação interativa (Swagger): `http://localhost:8000/docs`

---

## Autenticação

Todas as rotas (exceto `/health`, `/usuarios/registrar` e `/usuarios/login`) exigem o header:

```
X-Isy-Token: meu-token-secreto-troque-isso
```

---

## Endpoints principais

| Método | Rota | Descrição |
|---|---|---|
| GET | `/health` | Verifica se a API está no ar |
| GET | `/scripts` | Lista scripts disponíveis |
| POST | `/scripts/{id}/executar` | Executa um script |
| GET | `/logs` | Histórico de execuções |
| POST | `/usuarios/registrar` | Cria conta (plano free) |
| POST | `/usuarios/login` | Login — retorna token |
| GET | `/analytics/resumo` | Métricas do dia (admin) |
| GET | `/analytics/scripts-mais-usados` | Ranking de scripts (admin) |
| GET | `/analytics/clientes-mais-ativos` | Ranking de clientes (admin) |
| GET | `/analytics/falhas` | Falhas do dia (admin) |
| POST | `/webhooks/stripe` | Atualiza plano após pagamento |

---

## Planos freemium

| Plano | Execuções/dia | Acesso |
|---|---|---|
| free | 10 | Scripts marcados `free` |
| pro | 500 | Scripts `free` + `pro` |
| enterprise | Ilimitado | Todos |

---

## Checklist

- [x] API REST com FastAPI e Swagger automático em `/docs`
- [x] Execução de scripts via subprocess sem `shell=True`
- [x] Proteção contra command injection (whitelist, regex, lista de args)
- [x] Autenticação por token com HTTP 401/403
- [x] Log de auditoria automático com duração de execução
- [x] Containerizado com Docker e volume para scripts
- [x] Sistema freemium com planos e rate limiting
- [x] Analytics de uso em tempo real
- [x] Hash de senhas com PBKDF2-HMAC-SHA256
- [x] Webhook Stripe para upgrade automático de plano
- [x] 31 testes automatizados — todos passando
