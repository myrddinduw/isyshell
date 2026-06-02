# analytics.py — Consultas de métricas e estatísticas do sistema.
#
# Este módulo fornece dados para o painel de administração (dashboard).
# Todas as funções leem o banco e retornam dicionários prontos para virar JSON.
#
# Métricas disponíveis:
#   - resumo_periodo       → total/sucessos/falhas/tempo médio do dia
#   - scripts_mais_usados  → ranking de scripts por número de execuções
#   - clientes_mais_ativos → ranking de usuários por total de chamados
#   - falhas_do_dia        → lista detalhada de execuções com falha

from datetime import date
from app.database import get_connection


def resumo_periodo(data: str = None) -> dict:
    """
    Retorna um resumo das execuções de um dia específico.

    Parâmetro:
      data — string no formato 'AAAA-MM-DD' (ex: '2026-06-02').
             Se omitido, usa o dia de hoje (UTC).

    Retorna:
      {
        "data": "2026-06-02",
        "total_execucoes": 42,
        "sucesso": 38,
        "falhas": 4,
        "taxa_falha_pct": 9.5,
        "tempo_medio_segundos": 1.234
      }
    """
    if not data:
        data = date.today().isoformat()

    conn = get_connection()

    total = conn.execute(
        "SELECT COUNT(*) AS n FROM execucoes WHERE date(horario) = ?",
        (data,)
    ).fetchone()["n"]

    falhas = conn.execute(
        "SELECT COUNT(*) AS n FROM execucoes WHERE date(horario) = ? AND status_retorno != 'sucesso'",
        (data,)
    ).fetchone()["n"]

    # AVG retorna NULL se não houver linhas — tratamos com 'or None'
    media_row = conn.execute(
        """
        SELECT AVG(duracao_segundos) AS media
        FROM execucoes
        WHERE date(horario) = ? AND duracao_segundos IS NOT NULL
        """,
        (data,)
    ).fetchone()
    tempo_medio = media_row["media"] if media_row and media_row["media"] is not None else None

    conn.close()

    return {
        "data":                   data,
        "total_execucoes":        total,
        "sucesso":                total - falhas,
        "falhas":                 falhas,
        "taxa_falha_pct":         round(falhas / total * 100, 1) if total > 0 else 0.0,
        "tempo_medio_segundos":   round(tempo_medio, 3) if tempo_medio is not None else None,
    }


def scripts_mais_usados(limite: int = 10) -> list:
    """
    Retorna o ranking dos scripts mais executados de todos os tempos.

    Parâmetro:
      limite — quantos scripts retornar (padrão: 10)

    Cada item retornado:
      {
        "posicao": 1,
        "id": 2,
        "nome": "Checar Docker",
        "total_execucoes": 150,
        "sucessos": 148,
        "falhas": 2,
        "taxa_falha_pct": 1.3,
        "tempo_medio_segundos": 0.412
      }
    """
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT
            s.id,
            s.nome,
            COUNT(e.id)                                                         AS total_execucoes,
            SUM(CASE WHEN e.status_retorno = 'sucesso' THEN 1 ELSE 0 END)       AS sucessos,
            SUM(CASE WHEN e.status_retorno != 'sucesso' THEN 1 ELSE 0 END)      AS falhas,
            AVG(e.duracao_segundos)                                             AS tempo_medio_segundos
        FROM execucoes e
        JOIN scripts s ON e.script_id = s.id
        GROUP BY s.id, s.nome
        ORDER BY total_execucoes DESC
        LIMIT ?
        """,
        (limite,)
    ).fetchall()
    conn.close()

    return [
        {
            "posicao":              idx + 1,
            "id":                   r["id"],
            "nome":                 r["nome"],
            "total_execucoes":      r["total_execucoes"],
            "sucessos":             r["sucessos"],
            "falhas":               r["falhas"],
            "taxa_falha_pct":       round(r["falhas"] / r["total_execucoes"] * 100, 1)
                                    if r["total_execucoes"] > 0 else 0.0,
            "tempo_medio_segundos": round(r["tempo_medio_segundos"], 3)
                                    if r["tempo_medio_segundos"] is not None else None,
        }
        for idx, r in enumerate(rows)
    ]


def clientes_mais_ativos(limite: int = 10) -> list:
    """
    Retorna o ranking dos usuários com mais chamados à API.

    Apenas execuções vinculadas a um usuario_id são contadas.
    Execuções feitas pelo admin (usuario_id NULL) não aparecem aqui.

    Parâmetro:
      limite — quantos clientes retornar (padrão: 10)

    Cada item retornado:
      {
        "posicao": 1,
        "id": 3,
        "email": "cliente@empresa.com",
        "plano": "pro",
        "total_chamados": 320,
        "falhas": 5,
        "ultima_execucao": "2026-06-02T14:35:22"
      }
    """
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT
            u.id,
            u.email,
            u.plano,
            COUNT(e.id)                                                         AS total_chamados,
            SUM(CASE WHEN e.status_retorno != 'sucesso' THEN 1 ELSE 0 END)      AS falhas,
            MAX(e.horario)                                                      AS ultima_execucao
        FROM execucoes e
        JOIN usuarios u ON e.usuario_id = u.id
        GROUP BY u.id, u.email, u.plano
        ORDER BY total_chamados DESC
        LIMIT ?
        """,
        (limite,)
    ).fetchall()
    conn.close()

    return [
        {
            "posicao":         idx + 1,
            "id":              r["id"],
            "email":           r["email"],
            "plano":           r["plano"],
            "total_chamados":  r["total_chamados"],
            "falhas":          r["falhas"],
            "ultima_execucao": r["ultima_execucao"],
        }
        for idx, r in enumerate(rows)
    ]


def falhas_do_dia(data: str = None, limite: int = 50) -> list:
    """
    Retorna a lista detalhada de execuções com falha em um dia.

    Parâmetros:
      data   — 'AAAA-MM-DD' (padrão: hoje)
      limite — máximo de registros retornados (padrão: 50)

    Cada item retornado:
      {
        "id": 99,
        "horario": "2026-06-02T10:22:11",
        "nome_script": "Limpar Logs",
        "email_usuario": "cliente@empresa.com",
        "codigo_retorno": 1,
        "stderr": "Permission denied: /var/log/app"
      }
    """
    if not data:
        data = date.today().isoformat()

    conn = get_connection()
    rows = conn.execute(
        """
        SELECT
            e.id,
            e.horario,
            e.codigo_retorno,
            e.stderr,
            e.duracao_segundos,
            s.nome  AS nome_script,
            u.email AS email_usuario
        FROM execucoes e
        LEFT JOIN scripts  s ON e.script_id  = s.id
        LEFT JOIN usuarios u ON e.usuario_id = u.id
        WHERE date(e.horario) = ? AND e.status_retorno != 'sucesso'
        ORDER BY e.id DESC
        LIMIT ?
        """,
        (data, limite)
    ).fetchall()
    conn.close()

    return [
        {
            "id":                r["id"],
            "horario":           r["horario"],
            "nome_script":       r["nome_script"],
            "email_usuario":     r["email_usuario"],
            "codigo_retorno":    r["codigo_retorno"],
            "duracao_segundos":  r["duracao_segundos"],
            "stderr":            r["stderr"],
        }
        for r in rows
    ]
