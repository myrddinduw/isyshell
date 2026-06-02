<<<<<<< HEAD
# Estrutura das rotas:
#   /health                          → verificação de saúde (pública)
#   /scripts                         → gerenciar scripts
#   /logs                            → histórico de execuções
#   /config/token                    → trocar token de admin
#   /usuarios                        → cadastro, login, perfil (freemium)
#   /analytics                       → métricas e estatísticas (somente admin)
#   /webhooks/stripe                 → receber eventos de pagamento do Stripe

=======
>>>>>>> 6781cb0 (Limpeza geral do codigo)
from fastapi import Depends, FastAPI, HTTPException, Request, status

from app.database import inicializar_banco, get_connection
from app.auth     import verificar_token, exigir_admin
from app.executor import executar_script
from app.users    import (
    registrar_usuario, autenticar_usuario,
    checar_limite_plano, usuario_pode_usar_script,
    atualizar_plano_usuario, LIMITES_POR_PLANO,
)
from app.analytics import resumo_periodo, scripts_mais_usados, clientes_mais_ativos, falhas_do_dia
from app.payments  import processar_webhook_stripe
from app.schemas   import (
    ScriptCriar, ScriptAtualizar, ExecutarRequest, TrocarTokenRequest,
    UsuarioRegistrar, UsuarioLogin, AtualizarPlano,
)

app = FastAPI(
    title="IsyShell API",
    description=(
        "API REST para execucao segura de shell scripts em servidores Linux. "
        "Suporte a planos freemium (free / pro / enterprise) com rate limiting, "
        "controle de acesso por plano e analytics de uso."
    ),
    version="1.0.0",
)


@app.on_event("startup")
def ao_iniciar():
    inicializar_banco()
    print("IsyShell iniciada. Acesse /docs para a documentacao interativa.")


<<<<<<< HEAD

# ROTA DE SAÚDE — pública, sem token
=======
# --- Saude ---------------------------------------------------------------
>>>>>>> 6781cb0 (Limpeza geral do codigo)

@app.get("/health", tags=["Sistema"])
def health_check():
    """Verifica se a API esta no ar."""
    return {"status": "ok", "mensagem": "IsyShell esta funcionando!"}


<<<<<<< HEAD
# ROTAS DE SCRIPTS — listar, cadastrar, editar, executar
=======
# --- Scripts -------------------------------------------------------------
>>>>>>> 6781cb0 (Limpeza geral do codigo)

@app.get("/scripts", tags=["Scripts"])
def listar_scripts(usuario: dict = Depends(verificar_token)):
    """Lista scripts acessiveis pelo plano do chamador."""
    conn  = get_connection()
    plano = usuario["plano"]

    if plano == "free":
        scripts = conn.execute("SELECT * FROM scripts WHERE plano_minimo = 'free' ORDER BY id").fetchall()
    elif plano == "pro":
        scripts = conn.execute("SELECT * FROM scripts WHERE plano_minimo IN ('free','pro') ORDER BY id").fetchall()
    else:
        scripts = conn.execute("SELECT * FROM scripts ORDER BY id").fetchall()

    conn.close()
    return {"status": "sucesso", "total": len(scripts), "scripts": [dict(s) for s in scripts]}


@app.post("/scripts", tags=["Scripts"], status_code=201)
def cadastrar_script(dados: ScriptCriar, usuario: dict = Depends(exigir_admin)):
    """Cadastra um novo script. Somente admin. O campo plano_minimo controla o acesso por plano."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO scripts (nome, caminho, descricao, params_info, status, plano_minimo) VALUES (?,?,?,?,?,?)",
            (dados.nome, dados.caminho, dados.descricao, dados.params_info, dados.status, dados.plano_minimo),
        )
        conn.commit()
        novo_id = cursor.lastrowid
        conn.close()
        return {"status": "sucesso", "mensagem": f"Script '{dados.nome}' cadastrado.", "id": novo_id}
    except Exception as e:
        conn.close()
        raise HTTPException(400, {"status": "erro", "mensagem": str(e)})


@app.put("/scripts/{script_id}", tags=["Scripts"])
def atualizar_script(script_id: int, dados: ScriptAtualizar, usuario: dict = Depends(exigir_admin)):
    """Edita um script existente. Somente admin. Campos omitidos mantem o valor atual."""
    conn   = get_connection()
    script = conn.execute("SELECT * FROM scripts WHERE id = ?", (script_id,)).fetchone()

    if not script:
        conn.close()
        raise HTTPException(404, {"status": "erro", "mensagem": "Script nao encontrado."})

    conn.execute(
        "UPDATE scripts SET nome=?, descricao=?, params_info=?, status=?, plano_minimo=? WHERE id=?",
        (
            dados.nome         or script["nome"],
            dados.descricao    or script["descricao"],
            dados.params_info  or script["params_info"],
            dados.status       or script["status"],
            dados.plano_minimo or script["plano_minimo"],
            script_id,
        ),
    )
    conn.commit()
    conn.close()
    return {"status": "sucesso", "mensagem": f"Script ID {script_id} atualizado."}


@app.post("/scripts/{script_id}/executar", tags=["Scripts"])
def executar(script_id: int, body: ExecutarRequest, usuario: dict = Depends(verificar_token)):
    """
    Executa um script ativo e retorna stdout, stderr, codigo_retorno e duracao_segundos.
    Para usuarios (nao admin): verifica plano_minimo do script e limite diario do plano.
    A execucao e registrada automaticamente no log de auditoria independentemente do resultado.
    """
    if usuario["tipo"] == "usuario":
        conn   = get_connection()
        script = conn.execute(
            "SELECT plano_minimo FROM scripts WHERE id = ? AND status = 'ativo'", (script_id,)
        ).fetchone()
        conn.close()

        if script and not usuario_pode_usar_script(usuario["plano"], script["plano_minimo"]):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                {"status": "erro", "mensagem": f"Plano '{usuario['plano']}' sem acesso a este script."},
            )

        checar_limite_plano(usuario["id"], usuario["plano"])

    resultado = executar_script(script_id, body.parametros, usuario["id"])

    # HTTP 200 mesmo quando o script falha: a API funcionou corretamente;
    # o codigo_retorno e status indicam o resultado do script em si.
    return {
        "status":           resultado["status_retorno"],
        "mensagem":         "Execucao concluida." if resultado["status_retorno"] == "sucesso" else "O script terminou com erro.",
        "codigo_retorno":   resultado["codigo_retorno"],
        "stdout":           resultado["stdout"],
        "stderr":           resultado["stderr"],
        "duracao_segundos": resultado["duracao_segundos"],
    }


<<<<<<< HEAD

# ROTAS DE LOGS — consultar histórico de execuções
=======
# --- Logs ----------------------------------------------------------------
>>>>>>> 6781cb0 (Limpeza geral do codigo)

@app.get("/logs", tags=["Auditoria"])
def consultar_logs(limite: int = 50, usuario: dict = Depends(verificar_token)):
    """Historico de execucoes. Admin ve todos; usuarios veem apenas os proprios."""
    conn = get_connection()

    if usuario["tipo"] == "admin":
        registros = conn.execute(
            """SELECT e.*, s.nome AS nome_script, u.email AS email_usuario
               FROM execucoes e
               LEFT JOIN scripts  s ON e.script_id  = s.id
               LEFT JOIN usuarios u ON e.usuario_id = u.id
               ORDER BY e.id DESC LIMIT ?""",
            (limite,),
        ).fetchall()
    else:
        registros = conn.execute(
            """SELECT e.*, s.nome AS nome_script
               FROM execucoes e
               LEFT JOIN scripts s ON e.script_id = s.id
               WHERE e.usuario_id = ?
               ORDER BY e.id DESC LIMIT ?""",
            (usuario["id"], limite),
        ).fetchall()

    conn.close()
    return {"status": "sucesso", "total": len(registros), "logs": [dict(r) for r in registros]}


<<<<<<< HEAD
# ROTA DE CONFIGURAÇÃO — trocar o token de administrador
=======
# --- Configuracao --------------------------------------------------------
>>>>>>> 6781cb0 (Limpeza geral do codigo)

@app.put("/config/token", tags=["Configuracao"])
def trocar_token(dados: TrocarTokenRequest, usuario: dict = Depends(exigir_admin)):
    """Troca o token global de admin sem reiniciar a API. Somente admin."""
    if not dados.novo_token or len(dados.novo_token) < 8:
        raise HTTPException(400, {"status": "erro", "mensagem": "Token deve ter pelo menos 8 caracteres."})

    conn = get_connection()
    conn.execute("UPDATE configuracoes SET valor = ? WHERE chave = 'token'", (dados.novo_token,))
    conn.commit()
    conn.close()
    return {"status": "sucesso", "mensagem": "Token atualizado com sucesso."}


<<<<<<< HEAD
# ROTAS DE USUÁRIOS — cadastro, login, perfil, plano
=======
# --- Usuarios ------------------------------------------------------------
>>>>>>> 6781cb0 (Limpeza geral do codigo)

@app.post("/usuarios/registrar", tags=["Usuarios"], status_code=201)
def registrar(dados: UsuarioRegistrar):
    """Cria conta com plano free. Rota publica. Retorna o token de API gerado."""
    novo = registrar_usuario(dados.email, dados.senha)
    return {
        "status":  "sucesso",
        "mensagem": "Conta criada. Guarde o token de API.",
        "usuario": {"id": novo["id"], "email": novo["email"], "plano": novo["plano"], "token": novo["token"]},
    }


@app.post("/usuarios/login", tags=["Usuarios"])
def login(dados: UsuarioLogin):
    """Autentica com email e senha. Rota publica. Retorna o token de API."""
    u = autenticar_usuario(dados.email, dados.senha)
    return {
        "status":  "sucesso",
        "mensagem": "Login realizado.",
        "usuario": {"id": u["id"], "email": u["email"], "plano": u["plano"], "token": u["token"]},
    }


@app.get("/usuarios/meu-perfil", tags=["Usuarios"])
def meu_perfil(usuario: dict = Depends(verificar_token)):
    """Retorna perfil e limite diario do usuario autenticado."""
    if usuario["tipo"] == "admin":
        return {"status": "sucesso", "usuario": {"tipo": "admin", "plano": "enterprise"}}

    conn = get_connection()
    row  = conn.execute(
        "SELECT id, email, plano, criado_em FROM usuarios WHERE id = ?", (usuario["id"],)
    ).fetchone()
    conn.close()

    if not row:
        raise HTTPException(404, {"status": "erro", "mensagem": "Usuario nao encontrado."})

    limite = LIMITES_POR_PLANO.get(row["plano"])
    return {
        "status":  "sucesso",
        "usuario": {
            "id":            row["id"],
            "email":         row["email"],
            "plano":         row["plano"],
            "criado_em":     row["criado_em"],
            "limite_diario": limite if limite is not None else "ilimitado",
        },
    }


@app.get("/usuarios", tags=["Usuarios"])
def listar_usuarios(limite: int = 50, usuario: dict = Depends(exigir_admin)):
    """Lista usuarios cadastrados sem expor senha_hash ou token. Somente admin."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, email, plano, criado_em, ativo FROM usuarios ORDER BY id DESC LIMIT ?", (limite,)
    ).fetchall()
    conn.close()
    return {"status": "sucesso", "total": len(rows), "usuarios": [dict(r) for r in rows]}


@app.put("/usuarios/{usuario_id}/plano", tags=["Usuarios"])
def alterar_plano(usuario_id: int, dados: AtualizarPlano, admin: dict = Depends(exigir_admin)):
    """Altera o plano de um usuario manualmente. Somente admin."""
    atualizar_plano_usuario(usuario_id, dados.plano)
    return {"status": "sucesso", "mensagem": f"Plano do usuario ID {usuario_id} atualizado para '{dados.plano}'."}


<<<<<<< HEAD

# ROTAS DE ANALYTICS — métricas e estatísticas (somente admin)
=======
# --- Analytics -----------------------------------------------------------
>>>>>>> 6781cb0 (Limpeza geral do codigo)

@app.get("/analytics/resumo", tags=["Analytics"])
def analytics_resumo(data: str = None, admin: dict = Depends(exigir_admin)):
    """Total de execucoes, falhas, taxa de falha e tempo medio de um dia. Somente admin. ?data=AAAA-MM-DD"""
    return {"status": "sucesso", "resumo": resumo_periodo(data)}


@app.get("/analytics/scripts-mais-usados", tags=["Analytics"])
def analytics_scripts(limite: int = 10, admin: dict = Depends(exigir_admin)):
    """Ranking de scripts por execucoes, com taxa de falha e tempo medio. Somente admin."""
    return {"status": "sucesso", "ranking": scripts_mais_usados(limite)}


@app.get("/analytics/clientes-mais-ativos", tags=["Analytics"])
def analytics_clientes(limite: int = 10, admin: dict = Depends(exigir_admin)):
    """Ranking de clientes por total de chamados. Somente admin."""
    return {"status": "sucesso", "ranking": clientes_mais_ativos(limite)}


@app.get("/analytics/falhas", tags=["Analytics"])
def analytics_falhas(data: str = None, limite: int = 50, admin: dict = Depends(exigir_admin)):
    """Lista detalhada de execucoes com falha em um dia. Somente admin. ?data=AAAA-MM-DD"""
    return {"status": "sucesso", "falhas": falhas_do_dia(data, limite)}


<<<<<<< HEAD

# WEBHOOK DO STRIPE — recebe eventos de pagamento
=======
# --- Webhook Stripe ------------------------------------------------------
>>>>>>> 6781cb0 (Limpeza geral do codigo)

@app.post("/webhooks/stripe", tags=["Pagamentos"])
async def webhook_stripe(request: Request):
    """
    Recebe eventos do Stripe e atualiza planos automaticamente.
    Rota publica — autenticada pela assinatura HMAC do Stripe.
    Configure em: Stripe Dashboard -> Developers -> Webhooks -> Add endpoint.
    """
    return await processar_webhook_stripe(request)
