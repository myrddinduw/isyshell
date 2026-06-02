# 03 — Segurança: Command Injection e Como Nos Protegemos

## O que é Command Injection?

**Command Injection** (Injeção de Comando) é um tipo de ataque onde um invasor
consegue executar comandos maliciosos no servidor, aproveitando uma falha na forma
como o programa usa dados enviados pelo usuário.

### Exemplo de ataque (código VULNERÁVEL — NÃO faça isso!)

Imagine que a API fizesse assim:

```python
# CÓDIGO ERRADO E PERIGOSO — nunca faça isso!
import subprocess
import os

def executar_script_errado(nome_script, parametros):
    # Monta o comando como uma string concatenando tudo
    comando = f"bash /scripts/{nome_script} {parametros}"
    # shell=True passa o comando para o /bin/sh interpretar
    resultado = subprocess.run(comando, shell=True, capture_output=True, text=True)
    return resultado.stdout
```

Se um usuário mal-intencionado enviar como parâmetro:
```
nome_script = "limpar_logs.sh"
parametros  = "; rm -rf /"
```

O comando que seria executado no servidor seria:
```bash
bash /scripts/limpar_logs.sh ; rm -rf /
```

O `;` separa dois comandos — o segundo, `rm -rf /`, **apagaria todos os arquivos do servidor**!

---

## Nossas 4 Camadas de Proteção

### Proteção 1 — Lista Branca (Whitelist) — `executor.py`

```python
# Só executamos scripts que existam no banco E com status = 'ativo'
script = cursor.execute(
    "SELECT * FROM scripts WHERE id = ? AND status = 'ativo'",
    (script_id,)
).fetchone()
```

**Por quê funciona?** O usuário nunca envia um caminho de arquivo — ele envia um
número de ID. A API decide qual arquivo executar. Um invasor não pode mandar
`caminho = "../../../etc/passwd"` porque a API ignora isso completamente.

---

### Proteção 2 — Sem `shell=True` — `executor.py`

```python
# CERTO: comando como lista, sem shell=True
comando = ["bash", caminho_completo] + parametros
resultado = subprocess.run(comando, capture_output=True, text=True)

# ERRADO (nunca faça):
# subprocess.run(f"bash {caminho} {parametros}", shell=True)
```

**Por quê funciona?** Com a lista, o sistema operacional trata cada item como um
argumento separado, nunca como código. O `; rm -rf /` vira literalmente a string
`"; rm -rf /"` passada como argumento ao script — não é executado como comando.

---

### Proteção 3 — Validação de Parâmetros com Regex — `executor.py`

```python
# Só aceita letras, números, traços, pontos, barras e espaços
REGEX_PARAMETRO_SEGURO = re.compile(r'^[\w\-\.\/\s]+$')

def parametro_e_seguro(param: str) -> bool:
    return bool(REGEX_PARAMETRO_SEGURO.match(param))
```

**Por quê funciona?** Caracteres como `;`, `|`, `&`, `$`, `` ` `` são usados para
encadear comandos ou executar subcomandos no shell. Ao rejeitar qualquer parâmetro
que contenha esses caracteres, impossibilitamos a maioria dos ataques, mesmo que
alguma outra proteção falhe.

---

### Proteção 4 — Token de Autenticação — `auth.py`

```python
def verificar_token(x_isy_token: str = Header(...)):
    token_valido = obter_token_do_banco()
    if x_isy_token != token_valido:
        raise HTTPException(status_code=401, ...)
```

**Por quê funciona?** Sem o token correto, nenhuma rota de execução pode ser
acessada. O token é guardado no banco, então pode ser trocado a qualquer hora
sem reiniciar o servidor. Recomendação: use um token longo e aleatório em produção.

---

## Resumo Visual

```
Requisição chega
      ↓
[Token correto?] ──── NÃO ──→ HTTP 401, para aqui
      ↓ SIM
[Script ID existe e está ativo?] ──── NÃO ──→ Erro "Script não encontrado"
      ↓ SIM
[Arquivo .sh existe no disco?] ──── NÃO ──→ Erro "Arquivo não encontrado"
      ↓ SIM
[Todos os parâmetros são seguros?] ──── NÃO ──→ Erro "Parâmetro perigoso"
      ↓ SIM
subprocess.run(["bash", caminho, ...params], shell=False)
      ↓
Resultado gravado no banco de auditoria
      ↓
JSON de resposta devolvido
```
