# users.py — Lógica de negócio dos usuários do sistema freemium.
#
# Este módulo cuida de:
#   - Cadastro de novos usuários (com hash seguro de senha)
#   - Login (verificação de senha + retorno do token de API)
#   - Verificação de limite de execuções por plano (rate limiting)
#   - Verificação se o plano do usuário permite acessar um script
#   - Atualização de plano (usada pelo admin e pelo webhook do Stripe)
#
# Não usamos bibliotecas externas — só módulos que já vêm com o Python:
#   hashlib  → cria hashes criptográficos seguros
#   secrets  → gera tokens e salts verdadeiramente aleatórios

import hashlib
import secrets
from datetime import date, datetime
from fastapi import HTTPException

from app.database import get_connection, obter_usuario_por_email


# ==============================================================
# CONFIGURAÇÃO DOS PLANOS
# ==============================================================

# Limite de execuções por dia para cada plano.
# None = sem limite.
LIMITES_POR_PLANO: dict = {
    "free":       10,
    "pro":        500,
    "enterprise": None
}

# Hierarquia numérica dos planos.
# Usada para comparar: "o plano X tem acesso ao nível Y?"
HIERARQUIA_PLANOS: dict = {
    "free":       0,
    "pro":        1,
    "enterprise": 2
}

PLANOS_VALIDOS = list(HIERARQUIA_PLANOS.keys())


# ==============================================================
# FUNÇÕES PRIVADAS DE SENHA
# ==============================================================

def _hash_senha(senha: str) -> str:
    """
    Transforma a senha em um hash seguro para guardar no banco.

    POR QUÊ nunca guardar senha pura?
    Se o banco for comprometido, o invasor obteria todas as senhas em texto claro.
    Com o hash, ele obtém apenas um código irreversível.

    Como funciona o PBKDF2?
    1. Gera um 'salt' aleatório (16 bytes) — garante que dois usuários com a
       mesma senha tenham hashes diferentes.
    2. Aplica SHA-256 com 260.000 iterações — torna ataques de força bruta
       extremamente lentos (padrão recomendado pelo NIST em 2024).
    3. Retorna "salt:hash" como texto para salvar no banco.
    """
    salt = secrets.token_hex(16)
    dk   = hashlib.pbkdf2_hmac("sha256", senha.encode(), salt.encode(), 260_000)
    return f"{salt}:{dk.hex()}"


def _verificar_senha(senha: str, hash_armazenado: str) -> bool:
    """
    Verifica se a senha fornecida no login bate com o hash salvo no banco.
    Refaz exatamente o mesmo processo do _hash_senha usando o mesmo salt.
    """
    try:
        salt, dk_hex = hash_armazenado.split(":", 1)
        dk = hashlib.pbkdf2_hmac("sha256", senha.encode(), salt.encode(), 260_000)
        return dk.hex() == dk_hex
    except Exception:
        return False


# ==============================================================
# CADASTRO E LOGIN
# ==============================================================

def registrar_usuario(email: str, senha: str) -> dict:
    """
    Cadastra um novo usuário com plano 'free'.
    Retorna os dados do usuário incluindo o token de API gerado.

    Lança HTTPException 400 se o e-mail já estiver cadastrado ou a senha for curta.
    """
    if obter_usuario_por_email(email):
        raise HTTPException(
            status_code=400,
            detail={"status": "erro", "mensagem": "E-mail já cadastrado."}
        )

    if len(senha) < 8:
        raise HTTPException(
            status_code=400,
            detail={"status": "erro", "mensagem": "A senha deve ter pelo menos 8 caracteres."}
        )

    # token_hex(32) gera 64 caracteres hexadecimais — suficientemente aleatório
    # para ser usado como chave de API
    token     = secrets.token_hex(32)
    hash_pw   = _hash_senha(senha)
    criado_em = datetime.utcnow().isoformat()

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO usuarios (email, senha_hash, plano, token, criado_em) VALUES (?,?,?,?,?)",
            (email, hash_pw, "free", token, criado_em)
        )
        conn.commit()
        novo_id = cursor.lastrowid
        conn.close()
        return {"id": novo_id, "email": email, "plano": "free", "token": token}
    except Exception as e:
        conn.close()
        raise HTTPException(
            status_code=400,
            detail={"status": "erro", "mensagem": str(e)}
        )


def autenticar_usuario(email: str, senha: str) -> dict:
    """
    Verifica as credenciais e retorna o token de API do usuário.
    Lança HTTPException 401 se o e-mail/senha estiverem errados ou a conta inativa.
    """
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM usuarios WHERE email = ? AND ativo = 1", (email,)
    ).fetchone()
    conn.close()

    # Mensagem genérica propositalmente — não revelamos qual campo está errado
    if not row or not _verificar_senha(senha, row["senha_hash"]):
        raise HTTPException(
            status_code=401,
            detail={"status": "erro", "mensagem": "E-mail ou senha incorretos."}
        )

    return {
        "id":    row["id"],
        "email": row["email"],
        "plano": row["plano"],
        "token": row["token"]
    }


# ==============================================================
# CONTROLE DE ACESSO E RATE LIMITING
# ==============================================================

def checar_limite_plano(usuario_id: int, plano: str) -> None:
    """
    Verifica se o usuário ainda tem execuções disponíveis hoje.
    Lança HTTPException 429 (Too Many Requests) se o limite foi atingido.

    O que é rate limiting?
    É a prática de limitar quantas vezes alguém pode usar um recurso num período.
    Aqui contamos as execuções do dia (UTC) na tabela execucoes.
    """
    limite = LIMITES_POR_PLANO.get(plano)
    if limite is None:
        return  # enterprise: sem limite, não precisa verificar

    hoje = date.today().isoformat()  # ex: "2026-06-02"

    conn = get_connection()
    total_hoje = conn.execute(
        "SELECT COUNT(*) AS total FROM execucoes WHERE usuario_id = ? AND date(horario) = ?",
        (usuario_id, hoje)
    ).fetchone()["total"]
    conn.close()

    if total_hoje >= limite:
        raise HTTPException(
            status_code=429,
            detail={
                "status":  "erro",
                "mensagem": (
                    f"Limite do plano '{plano}' atingido: {limite} execuções/dia. "
                    "Faça upgrade para continuar usando hoje."
                )
            }
        )


def usuario_pode_usar_script(plano_usuario: str, plano_minimo_script: str) -> bool:
    """
    Retorna True se o plano do usuário permite acessar o script.

    Exemplo:
      usuario_pode_usar_script("free", "pro")  → False
      usuario_pode_usar_script("pro",  "pro")  → True
      usuario_pode_usar_script("enterprise", "pro") → True
    """
    nivel_usuario = HIERARQUIA_PLANOS.get(plano_usuario,       0)
    nivel_minimo  = HIERARQUIA_PLANOS.get(plano_minimo_script, 0)
    return nivel_usuario >= nivel_minimo


# ==============================================================
# GERENCIAMENTO DE PLANOS (usado pelo admin e pelo Stripe)
# ==============================================================

def atualizar_plano_usuario(usuario_id: int, novo_plano: str) -> None:
    """
    Muda o plano de um usuário.
    Lança HTTPException 400 se o plano não existir.
    Lança HTTPException 404 se o usuário não existir.
    """
    if novo_plano not in PLANOS_VALIDOS:
        raise HTTPException(
            status_code=400,
            detail={
                "status":  "erro",
                "mensagem": f"Plano '{novo_plano}' inválido. Opções: {', '.join(PLANOS_VALIDOS)}"
            }
        )

    conn = get_connection()
    usuario = conn.execute(
        "SELECT id FROM usuarios WHERE id = ?", (usuario_id,)
    ).fetchone()

    if not usuario:
        conn.close()
        raise HTTPException(
            status_code=404,
            detail={"status": "erro", "mensagem": f"Usuário ID {usuario_id} não encontrado."}
        )

    conn.execute(
        "UPDATE usuarios SET plano = ? WHERE id = ?", (novo_plano, usuario_id)
    )
    conn.commit()
    conn.close()
