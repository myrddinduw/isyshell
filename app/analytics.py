from datetime import date
from app.database import get_connection


def resumo_periodo(data: str = None) -> dict:
    """Retorna totais de execucoes, falhas, taxa de falha e tempo medio de um dia (padrao: hoje)."""
    if not data:
        data = date.today().isoformat()

    conn = get_connection()

    total  = conn.execute(
        "SELECT COUNT(*) AS n FROM execucoes WHERE date(horario) = ?", (data,)
    ).fetchone()["n"]

    falhas = conn.execute(
        "SELECT COUNT(*) AS n FROM execucoes WHERE date(horario) = ? AND status_retorno != 'sucesso'", (data,)
    ).fetchone()["n"]

    row        = conn.execute(
        "SELECT AVG(duracao_segundos) AS media FROM execucoes WHERE date(horario) = ? AND duracao_segundos IS NOT NULL",
        (data,)
    ).fetchone()
    tempo_medio = row["media"] if row and row["media"] is not None else None
    conn.close()

    return {
        "data":                 data,
        "total_execucoes":      total,
        "sucesso":              total - falhas,
        "falhas":               falhas,
        "taxa_falha_pct":       round(falhas / total * 100, 1) if total > 0 else 0.0,
        "tempo_medio_segundos": round(tempo_medio, 3) if tempo_medio is not None else None,
    }


def scripts_mais_usados(limite: int = 10) -> list:
    """Ranking dos scripts por total de execucoes, com taxa de falha e tempo medio."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT
            s.id, s.nome,
            COUNT(e.id)                                                    AS total_execucoes,
            SUM(CASE WHEN e.status_retorno = 'sucesso' THEN 1 ELSE 0 END)  AS sucessos,
            SUM(CASE WHEN e.status_retorno != 'sucesso' THEN 1 ELSE 0 END) AS falhas,
            AVG(e.duracao_segundos)                                        AS tempo_medio_segundos
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
            "taxa_falha_pct":       round(r["falhas"] / r["total_execucoes"] * 100, 1) if r["total_execucoes"] > 0 else 0.0,
            "tempo_medio_segundos": round(r["tempo_medio_segundos"], 3) if r["tempo_medio_segundos"] is not None else None,
        }
        for idx, r in enumerate(rows)
    ]


def clientes_mais_ativos(limite: int = 10) -> list:
    """Ranking de usuarios por total de chamados. Execucoes de admin (usuario_id NULL) sao excluidas."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT
            u.id, u.email, u.plano,
            COUNT(e.id)                                                    AS total_chamados,
            SUM(CASE WHEN e.status_retorno != 'sucesso' THEN 1 ELSE 0 END) AS falhas,
            MAX(e.horario)                                                 AS ultima_execucao
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
            "posicao":        idx + 1,
            "id":             r["id"],
            "email":          r["email"],
            "plano":          r["plano"],
            "total_chamados": r["total_chamados"],
            "falhas":         r["falhas"],
            "ultima_execucao": r["ultima_execucao"],
        }
        for idx, r in enumerate(rows)
    ]


def falhas_do_dia(data: str = None, limite: int = 50) -> list:
    """Lista detalhada de execucoes com falha em um dia (padrao: hoje)."""
    if not data:
        data = date.today().isoformat()

    conn = get_connection()
    rows = conn.execute(
        """
        SELECT
            e.id, e.horario, e.stderr, e.duracao_segundos,
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

    return [dict(r) for r in rows]
