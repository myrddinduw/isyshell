# 08 — Analytics: Métricas e Estatísticas de Uso

## O que foi adicionado?

O IsyShell inclui um painel de analytics acessível apenas pelo **administrador**. Ele responde perguntas como:

- Quantas execuções falharam hoje?
- Qual script é mais utilizado?
- Qual cliente mais consome a API?
- Quanto tempo em média cada script leva?

Todas as métricas vêm diretamente do banco SQLite — sem ferramentas externas.

---

## Novos campos no banco

Para calcular as métricas, dois campos foram adicionados à tabela `execucoes`:

| Campo              | Tipo    | O que guarda                                  |
|--------------------|---------|-----------------------------------------------|
| `usuario_id`       | INTEGER | ID do usuário que disparou a execução         |
| `duracao_segundos` | REAL    | Tempo de execução em segundos (ex: `0.412`)   |

Esses campos são preenchidos automaticamente pelo `executor.py` em toda execução.

---

## Endpoints de Analytics

Todos exigem o token de administrador no header `X-Isy-Token`.

---

### `GET /analytics/resumo` — Resumo do dia

Retorna um panorama geral de um dia específico.

```
GET /analytics/resumo
GET /analytics/resumo?data=2026-06-01
```

```json
{
  "status": "sucesso",
  "resumo": {
    "data": "2026-06-02",
    "total_execucoes": 87,
    "sucesso": 82,
    "falhas": 5,
    "taxa_falha_pct": 5.7,
    "tempo_medio_segundos": 1.234
  }
}
```

| Campo                  | Significado                                  |
|------------------------|----------------------------------------------|
| `total_execucoes`      | Quantidade total de execuções no dia         |
| `sucesso`              | Execuções com código de retorno 0            |
| `falhas`               | Execuções com qualquer erro                  |
| `taxa_falha_pct`       | Percentual de falhas (`falhas/total × 100`)  |
| `tempo_medio_segundos` | Média do campo `duracao_segundos` no dia     |

---

### `GET /analytics/scripts-mais-usados` — Ranking de scripts

```
GET /analytics/scripts-mais-usados
GET /analytics/scripts-mais-usados?limite=5
```

```json
{
  "status": "sucesso",
  "ranking": [
    {
      "posicao": 1,
      "id": 2,
      "nome": "Checar Docker",
      "total_execucoes": 320,
      "sucessos": 318,
      "falhas": 2,
      "taxa_falha_pct": 0.6,
      "tempo_medio_segundos": 0.412
    },
    {
      "posicao": 2,
      "id": 1,
      "nome": "Limpar Logs",
      "total_execucoes": 154,
      "sucessos": 150,
      "falhas": 4,
      "taxa_falha_pct": 2.6,
      "tempo_medio_segundos": 2.105
    }
  ]
}
```

**Casos de uso:**
- Identificar qual script precisa de mais atenção (alto volume + alta falha)
- Decidir quais scripts vale otimizar (alto tempo médio + muito uso)

---

### `GET /analytics/clientes-mais-ativos` — Ranking de clientes

```
GET /analytics/clientes-mais-ativos
GET /analytics/clientes-mais-ativos?limite=5
```

```json
{
  "status": "sucesso",
  "ranking": [
    {
      "posicao": 1,
      "id": 3,
      "email": "integracao@empresa.com",
      "plano": "enterprise",
      "total_chamados": 1240,
      "falhas": 12,
      "ultima_execucao": "2026-06-02T14:35:22"
    }
  ]
}
```

**Casos de uso:**
- Identificar clientes que estão perto do limite do plano (candidatos a upgrade)
- Detectar uso anormal (muitas chamadas em pouco tempo)
- Priorizar suporte para clientes mais ativos

---

### `GET /analytics/falhas` — Falhas detalhadas

```
GET /analytics/falhas
GET /analytics/falhas?data=2026-06-01&limite=20
```

```json
{
  "status": "sucesso",
  "falhas": [
    {
      "id": 99,
      "horario": "2026-06-02T10:22:11",
      "nome_script": "Limpar Logs",
      "email_usuario": "dev@startup.io",
      "codigo_retorno": 1,
      "duracao_segundos": 0.203,
      "stderr": "Permission denied: /var/log/app"
    }
  ]
}
```

**Casos de uso:**
- Diagnóstico rápido: qual script está falhando e por quê (`stderr`)
- Identificar se o problema é de um cliente específico ou global
- Monitorar regressões após atualizações nos scripts

---

## Como as métricas são calculadas

Tudo usa SQL direto no SQLite — simples e sem dependências externas:

```sql
-- Taxa de falha do dia
SELECT
    COUNT(*) AS total,
    SUM(CASE WHEN status_retorno != 'sucesso' THEN 1 ELSE 0 END) AS falhas,
    AVG(duracao_segundos) AS tempo_medio
FROM execucoes
WHERE date(horario) = '2026-06-02'
```

```sql
-- Scripts mais usados
SELECT s.nome, COUNT(e.id) AS total
FROM execucoes e
JOIN scripts s ON e.script_id = s.id
GROUP BY s.id
ORDER BY total DESC
LIMIT 10
```

---

## Arquivo relacionado

| Arquivo           | Responsabilidade                        |
|-------------------|-----------------------------------------|
| `app/analytics.py`| Todas as consultas de métricas          |
| `app/executor.py` | Grava `duracao_segundos` e `usuario_id` |
| `app/main.py`     | Rotas `/analytics/*` (somente admin)    |
