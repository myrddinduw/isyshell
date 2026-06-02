# auth.py — Verifica se quem chama a API tem permissão.
#
# Aceita dois tipos de autenticação:
#
#   1. Token de USUÁRIO cadastrado (tabela usuarios)
#      → retorna: {"tipo": "usuario", "id": 1, "plano": "free", "email": "..."}
#
#   2. Token global de ADMINISTRADOR (tabela configuracoes)
#      → retorna: {"tipo": "admin", "id": None, "plano": "enterprise", "email": "admin"}
#
# O retorno é sempre um dicionário — as rotas usam esse dict para checar
# plano, limites e permissões sem precisar consultar o banco de novo.

from fastapi import Depends, Header, HTTPException, status
from app.database import obter_token_do_banco, obter_usuario_por_token


def verificar_token(x_isy_token: str = Header(...)) -> dict:
    """
    Dependência principal de autenticação do FastAPI.

    Ao colocar  usuario: dict = Depends(verificar_token)  como parâmetro
    de uma rota, o FastAPI executa esta função antes de processar a requisição.
    Se o token for inválido, a requisição é barrada aqui mesmo com HTTP 401.
    """
    # Passo 1: verifica se o token pertence a algum usuário cadastrado
    usuario = obter_usuario_por_token(x_isy_token)
    if usuario:
        return {
            "tipo":  "usuario",
            "id":    usuario["id"],
            "plano": usuario["plano"],
            "email": usuario["email"]
        }

    # Passo 2: verifica se é o token global de administrador (compatibilidade
    # com o sistema original — continua funcionando sem nenhuma migração manual)
    if x_isy_token == obter_token_do_banco():
        return {
            "tipo":  "admin",
            "id":    None,
            "plano": "enterprise",
            "email": "admin"
        }

    # Se chegou aqui, o token não é válido
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "status": "erro",
            "mensagem": "Token inválido ou ausente. Envie o header X-Isy-Token correto."
        }
    )


def exigir_admin(usuario: dict = Depends(verificar_token)) -> dict:
    """
    Dependência extra para rotas restritas ao administrador.

    Uso numa rota:
        @app.get("/rota-secreta")
        def rota(usuario: dict = Depends(exigir_admin)):
            ...

    Usuários comuns (tipo "usuario") recebem HTTP 403 (proibido).
    Apenas o token global de administrador passa por essa barreira.
    """
    if usuario["tipo"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "status": "erro",
                "mensagem": "Acesso restrito ao administrador. Use o token de admin."
            }
        )
    return usuario
