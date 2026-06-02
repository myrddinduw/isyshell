# 02 — Como o IsyShell Funciona

## Mapa dos Arquivos

```
isysproject/
├── app/
│   ├── main.py       → A "recepção": registra todas as rotas e orquestra os módulos
│   ├── auth.py       → O "porteiro": verifica token (usuário ou admin) antes de deixar entrar
│   ├── database.py   → O "arquivo": cria e acessa o banco SQLite, helpers de busca
│   ├── executor.py   → O "operário seguro": roda scripts com proteções, mede duração
│   ├── schemas.py    → Os "formulários": define o formato esperado de todos os dados
│   ├── users.py      → O "RH": cadastro, login, hash de senha, rate limiting por plano
│   ├── analytics.py  → O "contador": calcula métricas e estatísticas de uso
│   └── payments.py   → O "financeiro": recebe eventos do Stripe e atualiza planos
├── scripts/          → Gaveta de scripts aprovados (volume Docker)
├── Dockerfile        → Receita da imagem
└── docker-compose.yml → Configuração do container
```

---

## Fluxo Completo: o que acontece ao executar um script

```
1. Você envia: POST /scripts/1/executar
               Header: X-Isy-Token: <token>
               Body:   {"parametros": ["--dias", "7"]}

2. FastAPI chama verificar_token() (auth.py)
   → É token de usuário cadastrado? Retorna perfil {id, plano, email}
   → É o token global de admin? Retorna perfil admin
   → Nenhum dos dois? HTTP 401 — para aqui.

3. Se for usuário (não admin):
   → Verifica se o plano dele permite este script (plano_minimo)
   → Verifica se não atingiu o limite diário do plano (rate limiting)
   → Plano insuficiente? HTTP 403. Limite atingido? HTTP 429.

4. main.py chama executar_script(1, ["--dias", "7"], usuario_id) (executor.py)
   → Busca o script ID=1 no banco — existe e está ativo? Continua.
   → Verifica se o arquivo .sh existe no disco. Continua.
   → Valida cada parâmetro — sem caracteres perigosos? Continua.
   → Marca o horário de início (time.time())
   → Monta o comando: ["bash", "/scripts/limpar_logs.sh", "--dias", "7"]
   → Executa com subprocess.run() — SEM shell=True
   → Captura stdout, stderr e código de retorno
   → Calcula duração em segundos
   → Grava tudo no banco (tabela execucoes), incluindo usuario_id e duracao_segundos

5. A API retorna o JSON de resposta:
   {
     "status": "sucesso",
     "codigo_retorno": 0,
     "stdout": "=== Limpeza concluída! ===",
     "stderr": "",
     "duracao_segundos": 0.312
   }
```

---

## Rotas da API (Endpoints)

### `GET /health` — Verificar se a API está no ar
**Pública — não exige token.**
```bash
curl http://localhost:8000/health
```
```json
{"status": "ok", "mensagem": "IsyShell está funcionando!"}
```

---

### `GET /scripts` — Listar scripts cadastrados
Usuários free veem apenas scripts com `plano_minimo = "free"`.
Pro e enterprise veem todos os que o plano permite.
```bash
curl http://localhost:8000/scripts \
  -H "X-Isy-Token: meu-token-secreto-troque-isso"
```
```json
{
  "status": "sucesso",
  "total": 2,
  "scripts": [
    {"id": 1, "nome": "Limpar Logs", "caminho": "limpar_logs.sh", "plano_minimo": "free", "status": "ativo"},
    {"id": 2, "nome": "Checar Docker", "caminho": "checar_docker.sh", "plano_minimo": "free", "status": "ativo"}
  ]
}
```

---

### `POST /scripts` — Cadastrar um novo script (somente admin)
```bash
curl -X POST http://localhost:8000/scripts \
  -H "X-Isy-Token: meu-token-secreto-troque-isso" \
  -H "Content-Type: application/json" \
  -d '{
    "nome": "Backup Banco",
    "caminho": "backup_db.sh",
    "descricao": "Faz backup do banco de dados",
    "params_info": "Parâmetros: <destino>",
    "status": "ativo",
    "plano_minimo": "pro"
  }'
```

---

### `PUT /scripts/{id}` — Editar ou desativar um script (somente admin)
```bash
curl -X PUT http://localhost:8000/scripts/1 \
  -H "X-Isy-Token: meu-token-secreto-troque-isso" \
  -H "Content-Type: application/json" \
  -d '{"status": "inativo"}'
```

---

### `POST /scripts/{id}/executar` — Executar um script
```bash
curl -X POST http://localhost:8000/scripts/1/executar \
  -H "X-Isy-Token: meu-token-secreto-troque-isso" \
  -H "Content-Type: application/json" \
  -d '{"parametros": ["/tmp/demo_logs", "7"]}'
```
```json
{
  "status": "sucesso",
  "mensagem": "Execução concluída.",
  "codigo_retorno": 0,
  "stdout": "=== IsyShell: Limpeza de Logs ===\nNenhum arquivo encontrado...",
  "stderr": "",
  "duracao_segundos": 0.312
}
```

---

### `GET /logs` — Consultar histórico de execuções
Usuários comuns veem apenas seus próprios logs. Admin vê todos.
```bash
curl "http://localhost:8000/logs?limite=10" \
  -H "X-Isy-Token: meu-token-secreto-troque-isso"
```

---

### `PUT /config/token` — Trocar o token de admin (somente admin)
```bash
curl -X PUT http://localhost:8000/config/token \
  -H "X-Isy-Token: meu-token-secreto-troque-isso" \
  -H "Content-Type: application/json" \
  -d '{"novo_token": "novo-token-super-seguro"}'
```

---

## Rotas de Usuários

### `POST /usuarios/registrar` — Criar conta (pública)
```bash
curl -X POST http://localhost:8000/usuarios/registrar \
  -H "Content-Type: application/json" \
  -d '{"email": "cliente@empresa.com", "senha": "minhasenha123"}'
```
```json
{
  "status": "sucesso",
  "mensagem": "Conta criada com sucesso. Guarde seu token de API!",
  "usuario": {"id": 1, "email": "cliente@empresa.com", "plano": "free", "token": "a3f7c2..."}
}
```

### `POST /usuarios/login` — Login (pública)
```bash
curl -X POST http://localhost:8000/usuarios/login \
  -H "Content-Type: application/json" \
  -d '{"email": "cliente@empresa.com", "senha": "minhasenha123"}'
```

### `GET /usuarios/meu-perfil` — Ver perfil e plano
```bash
curl http://localhost:8000/usuarios/meu-perfil \
  -H "X-Isy-Token: <seu-token>"
```

### `PUT /usuarios/{id}/plano` — Mudar plano (somente admin)
```bash
curl -X PUT http://localhost:8000/usuarios/1/plano \
  -H "X-Isy-Token: meu-token-secreto-troque-isso" \
  -H "Content-Type: application/json" \
  -d '{"plano": "pro"}'
```

---

## Rotas de Analytics (somente admin)

```bash
# Resumo do dia
curl "http://localhost:8000/analytics/resumo" \
  -H "X-Isy-Token: meu-token-secreto-troque-isso"

# Scripts mais usados (top 5)
curl "http://localhost:8000/analytics/scripts-mais-usados?limite=5" \
  -H "X-Isy-Token: meu-token-secreto-troque-isso"

# Clientes mais ativos
curl "http://localhost:8000/analytics/clientes-mais-ativos" \
  -H "X-Isy-Token: meu-token-secreto-troque-isso"

# Falhas do dia com detalhes de erro
curl "http://localhost:8000/analytics/falhas" \
  -H "X-Isy-Token: meu-token-secreto-troque-isso"
```
