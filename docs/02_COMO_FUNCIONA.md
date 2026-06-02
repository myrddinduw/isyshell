# 02 — Como o IsyShell Funciona

## Mapa dos Arquivos

```
isyshell/
├── app/
│   ├── main.py      → A "recepção" da API: registra todas as rotas
│   ├── auth.py      → O "porteiro": verifica o token antes de deixar entrar
│   ├── database.py  → O "arquivo": cria e acessa o banco SQLite
│   ├── executor.py  → O "operário seguro": roda os scripts com proteções
│   ├── schemas.py   → Os "formulários": define o formato dos dados
│   └── alerts.py    → O "mensageiro": avisa no Discord quando algo falha
├── scripts/         → Gaveta de scripts aprovados (volume Docker)
├── Dockerfile       → Receita da imagem
└── docker-compose.yml → Configuração do container
```

---

## Fluxo Completo: o que acontece quando você executa um script

```
1. Você envia: POST /scripts/1/executar
               Header: X-Isy-Token: meu-token
               Body:   {"parametros": ["--dias", "7"]}

2. FastAPI recebe a requisição e chama verificar_token() (auth.py)
   → Busca o token no banco (database.py)
   → Token certo? Continua. Token errado? HTTP 401, para aqui.

3. A rota em main.py chama executar_script(1, ["--dias", "7"]) (executor.py)
   → Busca o script ID=1 no banco — ele existe e está ativo? Continua.
   → Valida cada parâmetro — sem caracteres perigosos? Continua.
   → Monta o comando: ["bash", "/scripts/limpar_logs.sh", "--dias", "7"]
   → Executa com subprocess.run() — SEM shell=True
   → Captura stdout e stderr
   → Grava o resultado no banco (tabela execucoes)

4. Se o script falhou, main.py chama enviar_alerta_falha() (alerts.py)
   → Se DISCORD_WEBHOOK_URL estiver configurado, posta mensagem no canal

5. A API retorna o JSON de resposta:
   {
     "status": "sucesso",
     "codigo_retorno": 0,
     "stdout": "=== Limpeza concluída! ===",
     "stderr": ""
   }
```

---

## Rotas da API (Endpoints)

### `GET /health` — Verificar se a API está no ar
**Não exige token.**
```bash
curl http://localhost:8000/health
```
Resposta:
```json
{"status": "ok", "mensagem": "IsyShell está funcionando!"}
```

---

### `GET /scripts` — Listar scripts cadastrados
```bash
curl http://localhost:8000/scripts \
  -H "X-Isy-Token: meu-token-secreto-troque-isso"
```
Resposta:
```json
{
  "status": "sucesso",
  "total": 2,
  "scripts": [
    {"id": 1, "nome": "Limpar Logs", "caminho": "limpar_logs.sh", "status": "ativo"},
    {"id": 2, "nome": "Checar Docker", "caminho": "checar_docker.sh", "status": "ativo"}
  ]
}
```

---

### `POST /scripts` — Cadastrar um novo script
```bash
curl -X POST http://localhost:8000/scripts \
  -H "X-Isy-Token: meu-token-secreto-troque-isso" \
  -H "Content-Type: application/json" \
  -d '{
    "nome": "Limpar Logs",
    "caminho": "limpar_logs.sh",
    "descricao": "Remove arquivos de log antigos",
    "params_info": "Parâmetros: <pasta> <dias>",
    "status": "ativo"
  }'
```

---

### `PUT /scripts/{id}` — Editar ou desativar um script
```bash
# Desativar o script ID 1
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
Resposta:
```json
{
  "status": "sucesso",
  "mensagem": "Execução concluída.",
  "codigo_retorno": 0,
  "stdout": "=== IsyShell: Limpeza de Logs ===\nNenhum arquivo encontrado...",
  "stderr": ""
}
```

---

### `GET /logs` — Consultar histórico de execuções
```bash
# Últimas 10 execuções
curl "http://localhost:8000/logs?limite=10" \
  -H "X-Isy-Token: meu-token-secreto-troque-isso"
```

---

### `PUT /config/token` — Trocar o token
```bash
curl -X PUT http://localhost:8000/config/token \
  -H "X-Isy-Token: meu-token-secreto-troque-isso" \
  -H "Content-Type: application/json" \
  -d '{"novo_token": "novo-token-super-seguro-2024"}'
```
