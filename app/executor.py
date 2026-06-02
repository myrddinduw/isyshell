# executor.py — O coração da segurança do projeto.
#
# Este arquivo executa os scripts .sh de forma SEGURA usando subprocess.
# Cada proteção está comentada com o MOTIVO de existir.

import subprocess
import re
import os
import time
from datetime import datetime

from app.database import get_connection

# Pasta onde os scripts .sh ficam dentro do container (mapeada pelo volume Docker)
PASTA_SCRIPTS = os.getenv("SCRIPTS_PATH", "/scripts")

# Expressão regular que define quais caracteres são PERMITIDOS em parâmetros.
# Qualquer coisa fora desse conjunto é considerada perigosa e rejeitada.
# Permitimos: letras, números, traços, underscores, pontos, barras e espaços.
REGEX_PARAMETRO_SEGURO = re.compile(r'^[\w\-\.\/\s]+$')


def parametro_e_seguro(param: str) -> bool:
    """
    Verifica se um parâmetro enviado pelo usuário é seguro para usar.

    POR QUÊ isso é necessário?
    Se não validarmos, um usuário mal-intencionado poderia enviar:
      parametros: ["; rm -rf /"]
    Isso é chamado de "command injection" — injeção de comando malicioso.
    Ao checar caractere por caractere, bloqueamos qualquer tentativa de abuso.
    """
    if not param or not param.strip():
        return False

    return bool(REGEX_PARAMETRO_SEGURO.match(param))


def executar_script(script_id: int, parametros: list, usuario_id: int = None) -> dict:
    """
    Executa um script .sh com segurança e registra o resultado no banco.

    Recebe:
      script_id  — o ID do script cadastrado no banco (NÃO um caminho qualquer)
      parametros — lista de strings com os argumentos a passar ao script
      usuario_id — ID do usuário que disparou a execução (None para admin)

    Retorna um dicionário com: codigo_retorno, stdout, stderr, status_retorno,
                               duracao_segundos, nome_script
    """
    conn = get_connection()
    cursor = conn.cursor()

    # PROTEÇÃO 1 — Lista branca (whitelist):
    # Só executamos scripts que existam no banco E estejam com status "ativo".
    # Nunca aceitamos um caminho de arquivo enviado diretamente pelo usuário.
    script = cursor.execute(
        "SELECT * FROM scripts WHERE id = ? AND status = 'ativo'",
        (script_id,)
    ).fetchone()

    if not script:
        conn.close()
        return {
            "codigo_retorno":    -1,
            "stdout":            "",
            "stderr":            "Script não encontrado ou inativo.",
            "status_retorno":    "erro",
            "duracao_segundos":  None,
            "nome_script":       None
        }

    caminho_completo = os.path.join(PASTA_SCRIPTS, script["caminho"])

    # PROTEÇÃO 2 — Verifica se o arquivo realmente existe no disco
    if not os.path.isfile(caminho_completo):
        conn.close()
        return {
            "codigo_retorno":    -1,
            "stdout":            "",
            "stderr":            f"Arquivo não encontrado: {caminho_completo}",
            "status_retorno":    "erro",
            "duracao_segundos":  None,
            "nome_script":       script["nome"]
        }

    # PROTEÇÃO 3 — Valida cada parâmetro individualmente contra injeção de comando
    for param in parametros:
        if not parametro_e_seguro(param):
            conn.close()
            return {
                "codigo_retorno":    -1,
                "stdout":            "",
                "stderr":            f"Parâmetro inválido ou perigoso detectado: '{param}'",
                "status_retorno":    "erro",
                "duracao_segundos":  None,
                "nome_script":       script["nome"]
            }

    # PROTEÇÃO 4 — Comando como LISTA, NÃO como string (sem shell=True):
    # Cada argumento é tratado como dado, nunca como código pelo shell.
    comando = ["bash", caminho_completo] + parametros
    horario = datetime.utcnow().isoformat()

    # Marca o tempo ANTES de rodar o script para calcular a duração depois
    inicio = time.time()

    try:
        resultado = subprocess.run(
            comando,
            capture_output=True,
            text=True,
            timeout=30
        )

        duracao_segundos = round(time.time() - inicio, 3)
        codigo_retorno   = resultado.returncode
        stdout           = resultado.stdout
        stderr           = resultado.stderr
        # Código 0 = sucesso (convenção Unix); qualquer outro = algum problema
        status_retorno   = "sucesso" if codigo_retorno == 0 else "falha"

    except subprocess.TimeoutExpired:
        duracao_segundos = round(time.time() - inicio, 3)
        codigo_retorno   = -2
        stdout           = ""
        stderr           = "Script excedeu o tempo limite de 30 segundos."
        status_retorno   = "falha"

    except Exception as e:
        duracao_segundos = round(time.time() - inicio, 3)
        codigo_retorno   = -3
        stdout           = ""
        stderr           = f"Erro interno ao executar o script: {str(e)}"
        status_retorno   = "falha"

    # Auditoria: grava o resultado no banco independentemente do sucesso.
    # Agora inclui usuario_id (quem executou) e duracao_segundos (quanto demorou).
    cursor.execute("""
        INSERT INTO execucoes
            (script_id, usuario_id, params_usados, horario, status_retorno, duracao_segundos, stdout, stderr)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        script_id,
        usuario_id,
        " ".join(parametros),
        horario,
        status_retorno,
        duracao_segundos,
        stdout,
        stderr
    ))
    conn.commit()
    conn.close()

    return {
        "codigo_retorno":    codigo_retorno,
        "stdout":            stdout,
        "stderr":            stderr,
        "status_retorno":    status_retorno,
        "duracao_segundos":  duracao_segundos,
        "nome_script":       script["nome"]
    }
