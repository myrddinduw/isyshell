from pydantic import BaseModel
from typing import Optional, List


class ScriptCriar(BaseModel):
    nome:         str
    caminho:      str
    descricao:    str = ""
    params_info:  str = ""
    status:       str = "ativo"
    plano_minimo: str = "free"


class ScriptAtualizar(BaseModel):
    nome:         Optional[str] = None
    descricao:    Optional[str] = None
    params_info:  Optional[str] = None
    status:       Optional[str] = None
    plano_minimo: Optional[str] = None


class ExecutarRequest(BaseModel):
    parametros: List[str] = []


class UsuarioRegistrar(BaseModel):
    email: str
    senha: str


class UsuarioLogin(BaseModel):
    email: str
    senha: str


class AtualizarPlano(BaseModel):
    plano: str


class TrocarTokenRequest(BaseModel):
    novo_token: str


class RespostaBase(BaseModel):
    status:   str
    mensagem: str


class ExecutarResponse(RespostaBase):
    codigo_retorno:   Optional[int]   = None
    stdout:           Optional[str]   = None
    stderr:           Optional[str]   = None
    duracao_segundos: Optional[float] = None


class LogResponse(BaseModel):
    id:               int
    script_id:        int
    usuario_id:       Optional[int]   = None
    nome_script:      Optional[str]   = None
    params_usados:    str
    horario:          str
    status_retorno:   str
    duracao_segundos: Optional[float] = None
    stdout:           str
    stderr:           str
