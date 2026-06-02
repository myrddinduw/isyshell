# database.py — Responsável por conectar ao banco SQLite e criar as tabelas.
#
# O que é SQLite? É um banco de dados que vive em um único arquivo (.db).
# Não precisa instalar nada separado — o Python já tem suporte nativo via "sqlite3".

import sqlite3
import os

# Caminho onde o arquivo do banco de dados será salvo dentro do container.
# A variável de ambiente DATABASE_PATH permite mudar isso sem editar o código.
DATABASE_PATH = os.getenv("DATABASE_PATH", "/app/data/isyshell.db")


def get_connection():
    """
    Abre (ou cria) a conexão com o banco SQLite.
    check_same_thread=False é necessário porque o FastAPI usa múltiplas threads.
    """
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    # row_factory faz com que cada linha retornada vire um dicionário,
    # tornando mais fácil acessar os campos pelo nome (ex: row["nome"])
    conn.row_factory = sqlite3.Row
    return conn


def inicializar_banco():
    """
    Cria todas as tabelas do projeto se ainda não existirem,
    e aplica migrações incrementais para bancos já existentes.
    É chamada uma única vez quando a API inicia.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # TABELA 1: scripts
    # Guarda o "cadastro" de cada script que a API pode executar.
    # plano_minimo define qual plano de usuário tem acesso ao script.
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

    # TABELA 2: execucoes
    # Registra cada execução de script — é o nosso log de auditoria.
    # usuario_id liga a execução ao usuário que a disparou (pode ser NULL para admin).
    # duracao_segundos permite calcular tempo médio de execução nas analytics.
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

    # TABELA 3: configuracoes
    # Guarda pares chave-valor, como o token global de administrador.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS configuracoes (
            chave TEXT PRIMARY KEY,
            valor TEXT NOT NULL
        )
    """)

    # TABELA 4: usuarios
    # Cada cliente do sistema freemium tem uma conta aqui.
    # plano pode ser: 'free', 'pro', 'enterprise'
    # token é o segredo único gerado no cadastro — funciona como senha de API.
    # ativo = 0 significa conta suspensa (sem apagar do histórico).
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

    # Token padrão do administrador — troque isso em produção!
    cursor.execute("""
        INSERT OR IGNORE INTO configuracoes (chave, valor)
        VALUES ('token', 'meu-token-secreto-troque-isso')
    """)

    # MIGRAÇÕES INCREMENTAIS
    # Adiciona colunas novas em tabelas que já existem no banco.
    # SQLite não tem "ALTER TABLE ADD COLUMN IF NOT EXISTS", então usamos
    # try/except: se a coluna já existe, o erro é silenciado e seguimos em frente.
    migracoes = [
        "ALTER TABLE scripts   ADD COLUMN plano_minimo       TEXT DEFAULT 'free'",
        "ALTER TABLE execucoes ADD COLUMN usuario_id         INTEGER DEFAULT NULL",
        "ALTER TABLE execucoes ADD COLUMN duracao_segundos   REAL    DEFAULT NULL",
    ]
    for sql in migracoes:
        try:
            cursor.execute(sql)
        except Exception:
            pass  # Coluna já existe — sem problema

    # Scripts padrão registrados automaticamente na primeira execução
    scripts_iniciais = [
        (
            "Limpar Logs",
            "limpar_logs.sh",
            "Remove arquivos .log mais antigos que N dias de uma pasta.",
            "pasta (padrão: /tmp/demo_logs), dias (padrão: 7)",
            "ativo",
            "free"
        ),
        (
            "Checar Docker",
            "checar_docker.sh",
            "Verifica o status dos containers Docker em execução.",
            "filtro_opcional (ex: isyshell)",
            "ativo",
            "free"
        ),
    ]
    cursor.executemany("""
        INSERT OR IGNORE INTO scripts (nome, caminho, descricao, params_info, status, plano_minimo)
        VALUES (?, ?, ?, ?, ?, ?)
    """, scripts_iniciais)

    conn.commit()
    conn.close()


# ==============================================================
# FUNÇÕES AUXILIARES — buscas frequentes no banco
# ==============================================================

def obter_token_do_banco() -> str:
    """Busca o token global de administrador no banco."""
    conn = get_connection()
    row = conn.execute(
        "SELECT valor FROM configuracoes WHERE chave = 'token'"
    ).fetchone()
    conn.close()
    return row["valor"] if row else ""


def obter_usuario_por_token(token: str) -> dict | None:
    """
    Busca um usuário ativo pelo seu token de API.
    Retorna um dicionário com os dados do usuário, ou None se não encontrado.
    """
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM usuarios WHERE token = ? AND ativo = 1", (token,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def obter_usuario_por_email(email: str) -> dict | None:
    """
    Busca um usuário pelo e-mail (independente de estar ativo).
    Usado para checar duplicatas no cadastro e para o login.
    """
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM usuarios WHERE email = ?", (email,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None
