# Autenticacao via header X-Isy-Token.
# Aceita token de usuario cadastrado (tabela usuarios) ou token global de admin
# (tabela configuracoes). Retorna dict com {tipo, id, plano, email}.

from fastapi import Depends, Header, HTTPException, status
from app.database import obter_token_do_banco, obter_usuario_por_token


def verificar_token(x_isy_token: str = Header(...)) -> dict:
    """Valida o token e retorna o perfil do chamador. Retorna 401 se invalido."""
    usuario = obter_usuario_por_token(x_isy_token)
    if usuario:
        return {"tipo": "usuario", "id": usuario["id"], "plano": usuario["plano"], "email": usuario["email"]}

    if x_isy_token == obter_token_do_banco():
        return {"tipo": "admin", "id": None, "plano": "enterprise", "email": "admin"}

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"status": "erro", "mensagem": "Token invalido ou ausente."}
    )


def exigir_admin(usuario: dict = Depends(verificar_token)) -> dict:
    """Restringe a rota ao token de admin. Retorna 403 para usuarios comuns."""
    if usuario["tipo"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"status": "erro", "mensagem": "Acesso restrito ao administrador."}
        )
    return usuario
