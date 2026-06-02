# 07 — Usuários, Planos e Rate Limiting

## O que foi adicionado?

O IsyShell inclui um sistema completo de **contas de usuário** e **planos freemium**. Cada cliente tem sua própria conta com plano e limite de uso — além do token global de administrador já existente.

---

## Os Planos

| Plano        | Execuções/dia | Acesso a scripts |
|---|---|---|
| **free**       | 10            | Scripts marcados como `free` |
| **pro**        | 500           | Scripts `free` + `pro`       |
| **enterprise** | Ilimitado     | Todos os scripts             |
| **admin**      | Ilimitado     | Todos (token global)         |

> **Como definir o nível de um script?**
> No cadastro do script, use o campo `plano_minimo`:
> - `"free"` → qualquer usuário acessa
> - `"pro"` → somente pro e enterprise
> - `"enterprise"` → somente enterprise e admin

---

## Fluxo do usuário

```
1. POST /usuarios/registrar   → cria conta free, recebe token de API
2. POST /usuarios/login       → recupera o token esquecido
3. Usa X-Isy-Token nas demais requisições
4. GET /usuarios/meu-perfil  → vê plano atual e limite diário
```

---

## Endpoints de usuário

### `POST /usuarios/registrar` — público (sem token)

Cria uma nova conta com plano **free**.

```json
// Corpo da requisição (JSON)
{
  "email": "cliente@empresa.com",
  "senha": "minhasenha123"
}

// Resposta
{
  "status": "sucesso",
  "mensagem": "Conta criada com sucesso. Guarde seu token de API!",
  "usuario": {
    "id": 1,
    "email": "cliente@empresa.com",
    "plano": "free",
    "token": "a3f7c2e9d1b8..."   ← use este valor no header X-Isy-Token
  }
}
```

> **Importante:** guarde o token em lugar seguro. Ele é a sua senha de API.
> Se perdê-lo, use `/usuarios/login` para recuperar.

---

### `POST /usuarios/login` — público (sem token)

Autentica com e-mail e senha, retorna o token.

```json
// Corpo
{ "email": "cliente@empresa.com", "senha": "minhasenha123" }

// Resposta
{ "status": "sucesso", "usuario": { "token": "a3f7c2e9d1b8..." } }
```

---

### `GET /usuarios/meu-perfil` — requer token

Mostra o perfil do usuário logado, incluindo plano e limite diário restante.

```json
// Resposta
{
  "status": "sucesso",
  "usuario": {
    "id": 1,
    "email": "cliente@empresa.com",
    "plano": "free",
    "criado_em": "2026-06-02T10:00:00",
    "limite_diario": 10
  }
}
```

---

### `GET /usuarios` — somente admin

Lista todos os usuários cadastrados (sem senhas ou tokens).

---

### `PUT /usuarios/{id}/plano` — somente admin

Muda o plano de um usuário manualmente.

```json
// Corpo
{ "plano": "pro" }

// Resposta
{ "status": "sucesso", "mensagem": "Plano do usuário ID 1 atualizado para 'pro'." }
```

---

## Como funciona a segurança das senhas?

Nunca guardamos a senha em texto puro. Usamos o algoritmo **PBKDF2-HMAC-SHA256** com 260.000 iterações:

```
senha "minhasenha123" + salt aleatório → hash irreversível
```

Se o banco for comprometido, o invasor obtém apenas o hash — não a senha.

---

## Rate Limiting (controle de uso)

O rate limiting é verificado **antes** de cada execução de script. A lógica está em `app/users.py`:

```python
# Conta quantas execuções o usuário já fez hoje
total_hoje = SELECT COUNT(*) FROM execucoes
             WHERE usuario_id = ? AND date(horario) = hoje

if total_hoje >= limite_do_plano:
    → HTTP 429: "Limite atingido. Faça upgrade."
```

| Código HTTP | Significado |
|---|---|
| `200` | Execução realizada com sucesso |
| `403` | Script requer plano superior |
| `429` | Limite diário do plano atingido |

---

## Arquivos relacionados

| Arquivo | Responsabilidade |
|---|---|
| `app/users.py`    | Hash de senha, registro, login, rate limiting |
| `app/auth.py`     | Verifica token e retorna perfil do chamador   |
| `app/database.py` | Tabela `usuarios` e helpers de busca          |
| `app/schemas.py`  | Moldes `UsuarioRegistrar`, `UsuarioLogin`, `AtualizarPlano` |
