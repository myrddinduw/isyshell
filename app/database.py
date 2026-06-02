import sqlite3
import os

DATABASE_PATH = os.getenv("DATABASE_PATH", "/app/data/isyshell.db")


def get_connection():
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def inicializar_banco():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scripts (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            nome         TEXT    NOT NULL,
            caminho      TEXT    NOT NULL UNIQUE,
            descricao    TEXT    DEFAULT '',
            params_info  TEXT    DEFAULT '',
            status       TEXT    DEFAULT 'ativo',
            plano_minimo TEXT    DEFAULT 'free'
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS execucoes (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            script_id        INTEGER NOT NULL,
            usuario_id       INTEGER DEFAULT NULL,
            params_usados    TEXT    DEFAULT '',
            horario          TEXT    NOT NULL,
            status_retorno   TEXT    NOT NULL,
            duracao_segundos REAL    DEFAULT NULL,
            stdout           TEXT    DEFAULT '',
            stderr           TEXT    DEFAULT '',
            FOREIGN KEY (script_id)  REFERENCES scripts(id),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS configuracoes (
            chave TEXT PRIMARY KEY,
            valor TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            email       TEXT    NOT NULL UNIQUE,
            senha_hash  TEXT    NOT NULL,
            plano       TEXT    NOT NULL DEFAULT 'free',
            token       TEXT    NOT NULL UNIQUE,
            criado_em   TEXT    NOT NULL,
            ativo       INTEGER NOT NULL DEFAULT 1
        )
    """)

    cursor.execute("""
        INSERT OR IGNORE INTO configuracoes (chave, valor)
        VALUES ('token', 'meu-token-secreto-troque-isso')
    """)

    # SQLite nao suporta ADD COLUMN IF NOT EXISTS; try/except ignora coluna ja existente
    for sql in [
        "ALTER TABLE scripts   ADD COLUMN plano_minimo       TEXT DEFAULT 'free'",
        "ALTER TABLE execucoes ADD COLUMN usuario_id         INTEGER DEFAULT NULL",
        "ALTER TABLE execucoes ADD COLUMN duracao_segundos   REAL    DEFAULT NULL",
    ]:
        try:
            cursor.execute(sql)
        except Exception:
            pass

    cursor.executemany(
        "INSERT OR IGNORE INTO scripts (nome, caminho, descricao, params_info, status, plano_minimo) VALUES (?,?,?,?,?,?)",
        [
            ("Limpar Logs",   "limpar_logs.sh",   "Remove arquivos .log mais antigos que N dias.", "pasta, dias",          "ativo", "free"),
            ("Checar Docker", "checar_docker.sh", "Lista containers Docker em execucao.",          "filtro_opcional",      "ativo", "free"),
        ]
    )

    conn.commit()
    conn.close()


def obter_token_do_banco() -> str:
    conn = get_connection()
    row = conn.execute("SELECT valor FROM configuracoes WHERE chave = 'token'").fetchone()
    conn.close()
    return row["valor"] if row else ""


def obter_usuario_por_token(token: str) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM usuarios WHERE token = ? AND ativo = 1", (token,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def obter_usuario_por_email(email: str) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM usuarios WHERE email = ?", (email,)).fetchone()
    conn.close()
    return dict(row) if row else None
