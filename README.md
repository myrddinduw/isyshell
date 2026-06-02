# IsyShell — API REST para Execução Segura de Scripts Linux

Projeto desenvolvido para o Hackathon FMU + ISY.ONE 2026.1.

**Objetivo:** substituir o acesso manual via SSH por uma API segura, auditada e
containerizada para executar scripts de manutenção em servidores Linux —
com suporte a contas de usuário, planos freemium e analytics de uso.

---

## Pré-requisitos

- [Docker](https://docs.docker.com/get-docker/) instalado
- [Docker Compose](https://docs.docker.com/compose/install/) instalado
- Git (opcional, para clonar o repositório)

Verifique se estão instalados:
```bash
docker --version
docker-compose --version
```

---

## Como rodar do zero (passo a passo)

### 1. Entre na pasta do projeto
```bash
cd isysproject
```

### 2. Crie a pasta de dados (para o banco SQLite persistir)
```bash
mkdir -p data
```

### 3. Suba o container
```bash
docker-compose up --build
```

Você verá o log:
```
✅ IsyShell iniciada! Acesse /docs para ver a documentação interativa.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### 4. Acesse a documentação interativa no navegador
```
http://localhost:8000/docs
```

> A documentação Swagger permite testar todos os endpoints diretamente no
> navegador, sem precisar de curl ou Postman.

---

## Autenticação: dois modos

### Modo Admin (token global)
O token inicial é: `meu-token-secreto-troque-isso`
Use no header de todas as requisições: `X-Isy-Token: meu-token-secreto-troque-isso`

### Modo Usuário (freemium)
Cada cliente cria sua própria conta e recebe um token pessoal com limite por plano.

---

## Primeira execução (modo admin)

### Verificar que a API está no ar
```bash
curl http://localhost:8000/health
```

### Listar os scripts pré-cadastrados
```bash
curl http://localhost:8000/scripts \
  -H "X-Isy-Token: meu-token-secreto-troque-isso"
```

### Executar um script (ID 1 — Limpar Logs)
```bash
curl -X POST http://localhost:8000/scripts/1/executar \
  -H "Content-Type: application/json" \
  -H "X-Isy-Token: meu-token-secreto-troque-isso" \
  -d '{"parametros": ["/tmp/demo_logs", "7"]}'
```

### Consultar o log de auditoria
```bash
curl http://localhost:8000/logs \
  -H "X-Isy-Token: meu-token-secreto-troque-isso"
```

### Trocar o token de administrador
```bash
curl -X PUT http://localhost:8000/config/token \
  -H "Content-Type: application/json" \
  -H "X-Isy-Token: meu-token-secreto-troque-isso" \
  -d '{"novo_token": "novo-token-super-seguro"}'
```

---

## Sistema Freemium (usuários e planos)

### Criar uma conta
```bash
curl -X POST http://localhost:8000/usuarios/registrar \
  -H "Content-Type: application/json" \
  -d '{"email": "cliente@empresa.com", "senha": "minhasenha123"}'
```
> A resposta inclui o `token` — use-o como `X-Isy-Token` nas próximas requisições.

### Login (recuperar token)
```bash
curl -X POST http://localhost:8000/usuarios/login \
  -H "Content-Type: application/json" \
  -d '{"email": "cliente@empresa.com", "senha": "minhasenha123"}'
```

### Ver perfil e plano atual
```bash
curl http://localhost:8000/usuarios/meu-perfil \
  -H "X-Isy-Token: <seu-token>"
```

### Limites por plano

| Plano        | Execuções/dia | Acesso a scripts    |
|---|---|---|
| free         | 10            | Scripts marcados `free` |
| pro          | 500           | Scripts `free` + `pro`  |
| enterprise   | Ilimitado     | Todos os scripts        |

---

## Analytics (somente admin)

```bash
# Resumo do dia (total, falhas, tempo médio)
curl http://localhost:8000/analytics/resumo \
  -H "X-Isy-Token: meu-token-secreto-troque-isso"

# Scripts mais executados
curl http://localhost:8000/analytics/scripts-mais-usados \
  -H "X-Isy-Token: meu-token-secreto-troque-isso"

# Clientes com mais chamados
curl http://localhost:8000/analytics/clientes-mais-ativos \
  -H "X-Isy-Token: meu-token-secreto-troque-isso"

# Falhas do dia com detalhes de erro
curl http://localhost:8000/analytics/falhas \
  -H "X-Isy-Token: meu-token-secreto-troque-isso"
```

---

## Rodar em background (modo produção)

```bash
# Subir em background (não prende o terminal)
docker-compose up --build -d

# Ver logs
docker-compose logs -f

# Parar tudo
docker-compose down
```

---

## Estrutura de Arquivos

```
isysproject/
├── app/
│   ├── main.py        # Roteador principal — todas as rotas da API
│   ├── auth.py        # Autenticação — verifica token de usuário ou admin
│   ├── database.py    # Banco SQLite — tabelas e funções auxiliares
│   ├── executor.py    # Execução segura de scripts com subprocess
│   ├── schemas.py     # Moldes Pydantic para validação de dados
│   ├── users.py       # Lógica de usuários, planos e rate limiting
│   ├── analytics.py   # Consultas de métricas e estatísticas
│   └── payments.py    # Webhook Stripe para upgrades automáticos
├── scripts/           # Scripts .sh (volume Docker — editável sem rebuild)
├── docs/              # Documentação completa
├── futuras_implementacoes/  # Funcionalidades planejadas
├── data/              # Banco de dados SQLite (gerado automaticamente)
├── .env.example       # Variáveis de ambiente necessárias
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## Documentação Completa

| Arquivo | Conteúdo |
|---|---|
| `docs/01_VISAO_GERAL.md` | O problema e a solução |
| `docs/02_COMO_FUNCIONA.md` | Fluxo, arquivos e exemplos curl |
| `docs/03_SEGURANCA.md` | Command injection e proteções |
| `docs/04_DOCKER.md` | Docker explicado para leigos |
| `docs/05_ROTEIRO_PITCH.md` | Roteiro e respostas para a banca |
| `docs/06_GLOSSARIO.md` | Termos técnicos em uma linha |
| `docs/07_USUARIOS_E_PLANOS.md` | Sistema freemium, planos e rate limiting |
| `docs/08_ANALYTICS.md` | Métricas de uso e como interpretá-las |
| `docs/09_FREEMIUM_E_PAGAMENTOS.md` | Integração Stripe passo a passo |
| `docs/diagrama_arquitetura.md` | Diagrama Mermaid da arquitetura |

---

## Checklist dos Requisitos

- [x] API REST com FastAPI (Swagger automático em /docs)
- [x] Listar e executar scripts com subprocess
- [x] Captura de stdout e stderr
- [x] JSON padronizado em todas as respostas
- [x] Autenticação via X-Isy-Token (HTTP 401 para token inválido)
- [x] Proteção contra command injection (sem shell=True, lista de args, regex, whitelist)
- [x] Cadastro, edição e listagem de scripts
- [x] Troca dinâmica de token sem reiniciar
- [x] Log de auditoria com horário, script, parâmetros e status
- [x] Endpoint de consulta do histórico
- [x] Dockerfile com python:3.11-slim
- [x] docker-compose com volume para scripts
- [x] Sistema de usuários com planos freemium (free/pro/enterprise)
- [x] Rate limiting por plano (execuções/dia)
- [x] Controle de acesso por plano nos scripts (plano_minimo)
- [x] Analytics: resumo diário, scripts mais usados, clientes mais ativos, falhas
- [x] Tempo de execução registrado por script (duracao_segundos)
- [x] Webhook Stripe para upgrade automático de plano
- [x] Hash seguro de senhas com PBKDF2-HMAC-SHA256
