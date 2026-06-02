# schemas.py — Define os "moldes" (formatos) dos dados que a API aceita e devolve.
#
# O que é Pydantic? É uma biblioteca que valida automaticamente os dados.
# Se o usuário mandar um número onde esperamos texto, ela já rejeita com um
# erro claro, antes mesmo de o código tentar processar.

from pydantic import BaseModel, EmailStr
from typing import Optional, List


# ==============================================================
# MOLDES DE SCRIPTS
# ==============================================================

class ScriptCriar(BaseModel):
    """Dados necessários para cadastrar um novo script."""
    nome:         str
    caminho:      str           # Caminho do arquivo .sh dentro da pasta de scripts
    descricao:    str  = ""     # Descrição curta do que o script faz
    params_info:  str  = ""     # Explicação dos parâmetros que o script aceita
    status:       str  = "ativo"       # "ativo" ou "inativo"
    plano_minimo: str  = "free"        # Plano mínimo para acessar este script


class ScriptAtualizar(BaseModel):
    """Dados para editar um script existente. Todos os campos são opcionais."""
    nome:         Optional[str] = None
    descricao:    Optional[str] = None
    params_info:  Optional[str] = None
    status:       Optional[str] = None
    plano_minimo: Optional[str] = None


class ExecutarRequest(BaseModel):
    """Dados enviados quando o usuário quer executar um script."""
    # Lista de parâmetros que serão passados ao script, ex: ["--dias", "30"]
    parametros: List[str] = []


# ==============================================================
# MOLDES DE USUÁRIOS (freemium)
# ==============================================================

class UsuarioRegistrar(BaseModel):
    """Dados para criar uma nova conta."""
    email: str   # Ex: "cliente@empresa.com"
    senha: str   # Mínimo 8 caracteres — será armazenada como hash, nunca em texto puro


class UsuarioLogin(BaseModel):
    """Credenciais para fazer login e obter o token de API."""
    email: str
    senha: str


class AtualizarPlano(BaseModel):
    """Dados para mudar o plano de um usuário (somente admin)."""
    plano: str  # "free", "pro" ou "enterprise"


# ==============================================================
# MOLDES DE CONFIGURAÇÃO
# ==============================================================

class TrocarTokenRequest(BaseModel):
    """Dados para trocar o token global de administrador."""
    novo_token: str


# ==============================================================
# MOLDES DE SAÍDA — o que a API devolve
# ==============================================================

class RespostaBase(BaseModel):
    """Formato padrão de toda resposta da API. Sempre igual para facilitar o uso."""
    status:   str   # "sucesso" ou "erro"
    mensagem: str   # Descrição legível do resultado


class ScriptResponse(RespostaBase):
    """Resposta ao listar ou cadastrar um script."""
    dados: Optional[dict] = None


class ExecutarResponse(RespostaBase):
    """Resposta ao executar um script."""
    codigo_retorno:    Optional[int]   = None  # 0 = sucesso, >0 = erro do script
    stdout:            Optional[str]   = None  # Saída normal do script
    stderr:            Optional[str]   = None  # Saída de erros do script
    duracao_segundos:  Optional[float] = None  # Tempo de execução em segundos


class LogResponse(BaseModel):
    """Um registro do histórico de execuções."""
    id:              int
    script_id:       int
    usuario_id:      Optional[int]   = None
    nome_script:     Optional[str]   = None
    params_usados:   str
    horario:         str
    status_retorno:  str
    duracao_segundos: Optional[float] = None
    stdout:          str
    stderr:          str
