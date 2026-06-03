import subprocess
import re
import os
import time
from datetime import datetime

from app.database import get_connection

PASTA_SCRIPTS = os.getenv("SCRIPTS_PATH", "/scripts")

# Caracteres permitidos em parametros: letras, numeros, traco, ponto, barra, espaco.
# Rejeita ; | & $ ` e outros operadores de shell para bloquear command injection.
REGEX_PARAMETRO_SEGURO = re.compile(r'^[\w\-\.\/\s]+$')


def parametro_e_seguro(param: str) -> bool:
    if not param or not param.strip():
        return False
    return bool(REGEX_PARAMETRO_SEGURO.match(param))


def executar_script(script_id: int, parametros: list, usuario_id: int = None) -> dict:
    """
    Executa um script .sh com quatro camadas de protecao contra command injection:
      1. Whitelist: apenas scripts cadastrados e ativos no banco podem ser executados.
      2. Existencia: verifica se o arquivo .sh existe no disco.
      3. Validacao de parametros: bloqueia caracteres perigosos via regex.
      4. subprocess como lista sem shell=True: argumentos sao dados, nunca codigo.
    Registra o resultado e a duracao no log de auditoria.
    """
    conn = get_connection()
    cursor = conn.cursor()

    script = cursor.execute(
        "SELECT * FROM scripts WHERE id = ? AND status = 'ativo'", (script_id,)
    ).fetchone()

    if not script:
        conn.close()
        return {"codigo_retorno": -1, "stdout": "", "stderr": "Script nao encontrado ou inativo.",
                "status_retorno": "erro", "duracao_segundos": None, "nome_script": None}

    caminho_completo = os.path.join(PASTA_SCRIPTS, script["caminho"])

    if not os.path.isfile(caminho_completo):
        conn.close()
        return {"codigo_retorno": -1, "stdout": "", "stderr": f"Arquivo nao encontrado: {caminho_completo}",
                "status_retorno": "erro", "duracao_segundos": None, "nome_script": script["nome"]}

    for param in parametros:
        if not parametro_e_seguro(param):
            conn.close()
            return {"codigo_retorno": -1, "stdout": "", "stderr": f"Parametro invalido: '{param}'",
                    "status_retorno": "erro", "duracao_segundos": None, "nome_script": script["nome"]}

    comando = ["bash", caminho_completo] + parametros
    horario = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    inicio  = time.time()

    try:
        resultado        = subprocess.run(comando, capture_output=True, text=True, timeout=30)
        duracao_segundos = round(time.time() - inicio, 3)
        codigo_retorno   = resultado.returncode
        stdout           = resultado.stdout
        stderr           = resultado.stderr
        status_retorno   = "sucesso" if codigo_retorno == 0 else "falha"

    except subprocess.TimeoutExpired:
        duracao_segundos = round(time.time() - inicio, 3)
        codigo_retorno, stdout, stderr, status_retorno = -2, "", "Timeout: script excedeu 30 segundos.", "falha"

    except Exception as e:
        duracao_segundos = round(time.time() - inicio, 3)
        codigo_retorno, stdout, stderr, status_retorno = -3, "", f"Erro interno: {e}", "falha"

    cursor.execute(
        """INSERT INTO execucoes
           (script_id, usuario_id, params_usados, horario, status_retorno, duracao_segundos, stdout, stderr)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (script_id, usuario_id, " ".join(parametros), horario, status_retorno, duracao_segundos, stdout, stderr)
    )
    conn.commit()
    conn.close()

    return {
        "codigo_retorno":   codigo_retorno,
        "stdout":           stdout,
        "stderr":           stderr,
        "status_retorno":   status_retorno,
        "duracao_segundos": duracao_segundos,
        "nome_script":      script["nome"],
    }
