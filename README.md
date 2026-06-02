# IsyShell — API REST para Execução Segura de Scripts Linux

Projeto desenvolvido para o Hackathon FMU + ISY.ONE 2026.1.

**Objetivo:** substituir o acesso manual via SSH por uma API segura, auditada e
containerizada para executar scripts de manutenção em servidores Linux.

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

## Primeira execução: cadastrar e rodar um script

### Token padrão
O token inicial é: `meu-token-secreto-troque-isso`
Envie-o sempre no header: `X-Isy-Token: meu-token-secreto-troque-isso`

### Passo 1 — Verificar que a API está no ar
```bash
curl http://localhost:8000/health
```

### Passo 2 — Cadastrar o script de limpeza de logs
```bash
curl -X POST http://localhost:8000/scripts \
  -H "Content-Type: application/json" \
  -H "X-Isy-Token: meu-token-secreto-troque-isso" \
  -d '{
    "nome": "Limpar Logs Antigos",
    "caminho": "limpar_logs.sh",
    "descricao": "Remove arquivos de log mais antigos que N dias",
    "params_info": "Parâmetros: <pasta> <numero_de_dias>",
    "status": "ativo"
  }'
```

### Passo 3 — Cadastrar o script de checagem Docker
```bash
curl -X POST http://localhost:8000/scripts \
  -H "Content-Type: application/json" \
  -H "X-Isy-Token: meu-token-secreto-troque-isso" \
  -d '{
    "nome": "Checar Containers Docker",
    "caminho": "checar_docker.sh",
    "descricao": "Exibe status dos containers Docker em execução",
    "params_info": "Parâmetro opcional: filtro por nome",
    "status": "ativo"
  }'
```

### Passo 4 — Listar os scripts cadastrados
```bash
curl http://localhost:8000/scripts \
  -H "X-Isy-Token: meu-token-secreto-troque-isso"
```

### Passo 5 — Executar o script de limpeza (ID 1)
```bash
curl -X POST http://localhost:8000/scripts/1/executar \
  -H "Content-Type: application/json" \
  -H "X-Isy-Token: meu-token-secreto-troque-isso" \
  -d '{"parametros": ["/tmp/demo_logs", "7"]}'
```

### Passo 6 — Consultar o log de auditoria
```bash
curl http://localhost:8000/logs \
  -H "X-Isy-Token: meu-token-secreto-troque-isso"
```

---

## Trocar o token de autenticação

```bash
curl -X PUT http://localhost:8000/config/token \
  -H "Content-Type: application/json" \
  -H "X-Isy-Token: meu-token-secreto-troque-isso" \
  -d '{"novo_token": "novo-token-super-seguro-2024"}'
```

---

## Configurar alertas no Discord (diferencial)

1. No seu servidor Discord, crie um canal e vá em **Configurações do canal → Integrações → Webhooks → Novo Webhook**.
2. Copie a URL gerada.
3. Edite o `docker-compose.yml` e coloque a URL na variável:
   ```yaml
   - DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/SEU_WEBHOOK_AQUI
   ```
4. Reinicie o container:
   ```bash
   docker-compose down && docker-compose up --build
   ```

Quando qualquer script falhar, o bot enviará uma mensagem automática no canal.

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
isyshell/
├── app/
│   ├── main.py        # Roteador principal da API
│   ├── auth.py        # Validação do token X-Isy-Token
│   ├── database.py    # Banco SQLite e tabelas
│   ├── executor.py    # Execução segura de scripts
│   ├── schemas.py     # Modelos de dados Pydantic
│   └── alerts.py      # Alerta Discord (diferencial)
├── scripts/           # Scripts .sh (volume Docker)
├── docs/              # Documentação completa
├── data/              # Banco de dados SQLite (gerado automaticamente)
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
- [x] Alerta Discord em falhas (diferencial)
