import hashlib
import secrets
from datetime import date, datetime
from fastapi import HTTPException

from app.database import get_connection, obter_usuario_por_email

# Limites de execucoes por dia por plano. None = sem limite.
LIMITES_POR_PLANO: dict = {
    "free":       10,
    "pro":        500,
    "enterprise": None,
}

# Hierarquia numerica usada para comparar niveis de plano.
HIERARQUIA_PLANOS: dict = {
    "free":       0,
    "pro":        1,
    "enterprise": 2,
}

PLANOS_VALIDOS = list(HIERARQUIA_PLANOS.keys())


def _hash_senha(senha: str) -> str:
    # PBKDF2-HMAC-SHA256 com 260.000 iteracoes e salt aleatorio (padrao NIST SP 800-132).
    # Formato armazenado: "salt:hash_hex"
    salt = secrets.token_hex(16)
    dk   = hashlib.pbkdf2_hmac("sha256", senha.encode(), salt.encode(), 260_000)
    return f"{salt}:{dk.hex()}"


def _verificar_senha(senha: str, hash_armazenado: str) -> bool:
    try:
        salt, dk_hex = hash_armazenado.split(":", 1)
        dk = hashlib.pbkdf2_hmac("sha256", senha.encode(), salt.encode(), 260_000)
        return dk.hex() == dk_hex
    except Exception:
        return False


def registrar_usuario(email: str, senha: str) -> dict:
    """Cria conta com plano free. Retorna dados do usuario incluindo o token de API."""
    if obter_usuario_por_email(email):
        raise HTTPException(400, {"status": "erro", "mensagem": "E-mail ja cadastrado."})

    if len(senha) < 8:
        raise HTTPException(400, {"status": "erro", "mensagem": "Senha deve ter pelo menos 8 caracteres."})

    token     = secrets.token_hex(32)
    criado_em = datetime.utcnow().isoformat()

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO usuarios (email, senha_hash, plano, token, criado_em) VALUES (?,?,?,?,?)",
            (email, _hash_senha(senha), "free", token, criado_em)
        )
        conn.commit()
        novo_id = cursor.lastrowid
        conn.close()
        return {"id": novo_id, "email": email, "plano": "free", "token": token}
    except Exception as e:
        conn.close()
        raise HTTPException(400, {"status": "erro", "mensagem": str(e)})


def autenticar_usuario(email: str, senha: str) -> dict:
    """Valida credenciais e retorna o token de API. Retorna 401 se invalido."""
    conn = get_connection()
    row  = conn.execute("SELECT * FROM usuarios WHERE email = ? AND ativo = 1", (email,)).fetchone()
    conn.close()

    # Mensagem generica intencional: nao revelar qual campo esta errado.
    if not row or not _verificar_senha(senha, row["senha_hash"]):
        raise HTTPException(401, {"status": "erro", "mensagem": "E-mail ou senha incorretos."})

    return {"id": row["id"], "email": row["email"], "plano": row["plano"], "token": row["token"]}


def checar_limite_plano(usuario_id: int, plano: str) -> None:
    """Retorna 429 se o usuario atingiu o limite de execucoes do dia."""
    limite = LIMITES_POR_PLANO.get(plano)
    if limite is None:
        return

    hoje       = date.today().isoformat()
    conn       = get_connection()
    total_hoje = conn.execute(
        "SELECT COUNT(*) AS total FROM execucoes WHERE usuario_id = ? AND date(horario) = ?",
        (usuario_id, hoje)
    ).fetchone()["total"]
    conn.close()

    if total_hoje >= limite:
        raise HTTPException(
            429,
            {"status": "erro", "mensagem": f"Limite do plano '{plano}' atingido: {limite} execucoes/dia."}
        )


def usuario_pode_usar_script(plano_usuario: str, plano_minimo_script: str) -> bool:
    """Retorna True se o plano do usuario e igual ou superior ao plano minimo do script."""
    return HIERARQUIA_PLANOS.get(plano_usuario, 0) >= HIERARQUIA_PLANOS.get(plano_minimo_script, 0)


def atualizar_plano_usuario(usuario_id: int, novo_plano: str) -> None:
    """Atualiza o plano de um usuario. Retorna 400 se o plano for invalido, 404 se o usuario nao existir."""
    if novo_plano not in PLANOS_VALIDOS:
        raise HTTPException(400, {"status": "erro", "mensagem": f"Plano invalido. Opcoes: {', '.join(PLANOS_VALIDOS)}"})

    conn    = get_connection()
    usuario = conn.execute("SELECT id FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()

    if not usuario:
        conn.close()
        raise HTTPException(404, {"status": "erro", "mensagem": f"Usuario ID {usuario_id} nao encontrado."})

    conn.execute("UPDATE usuarios SET plano = ? WHERE id = ?", (novo_plano, usuario_id))
    conn.commit()
    conn.close()
