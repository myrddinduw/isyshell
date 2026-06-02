# Estrutura das rotas:
#   /health                          → verificação de saúde (pública)
#   /scripts                         → gerenciar scripts
#   /logs                            → histórico de execuções
#   /config/token                    → trocar token de admin
#   /usuarios                        → cadastro, login, perfil (freemium)
#   /analytics                       → métricas e estatísticas (somente admin)
#   /webhooks/stripe                 → receber eventos de pagamento do Stripe

from fastapi import Depends, FastAPI, HTTPException, Request, status

from app.database import inicializar_banco, get_connection
from app.auth     import verificar_token, exigir_admin
from app.executor import executar_script
from app.users    import (
    registrar_usuario, autenticar_usuario,
    checar_limite_plano, usuario_pode_usar_script,
    atualizar_plano_usuario
)
from app.analytics import (
    resumo_periodo, scripts_mais_usados,
    clientes_mais_ativos, falhas_do_dia
)
from app.payments import processar_webhook_stripe
from app.schemas  import (
    ScriptCriar, ScriptAtualizar, ExecutarRequest,
    TrocarTokenRequest, UsuarioRegistrar, UsuarioLogin, AtualizarPlano,
    ScriptResponse, ExecutarResponse, LogResponse
)

app = FastAPI(
    title="IsyShell API",
    description=(
        "API REST para execução segura de shell scripts em servidores Linux. "
        "Suporte a planos freemium (free / pro / enterprise) com rate limiting, "
        "controle de acesso por plano e analytics de uso."
    ),
    version="1.0.0"
)


@app.on_event("startup")
def ao_iniciar():
    inicializar_banco()
    print("✅ IsyShell iniciada! Acesse /docs para ver a documentação interativa.")



# ROTA DE SAÚDE — pública, sem token

@app.get("/health", tags=["Sistema"])
def health_check():
    """Verifica se a API está no ar. Útil para ferramentas de monitoramento."""
    return {"status": "ok", "mensagem": "IsyShell está funcionando!"}


# ROTAS DE SCRIPTS — listar, cadastrar, editar, executar

@app.get("/scripts", tags=["Scripts"])
def listar_scripts(usuario: dict = Depends(verificar_token)):
    """
    Lista todos os scripts cadastrados.
    Usuários free veem apenas scripts com plano_minimo = 'free'.
    Usuários pro/enterprise veem todos.
    """
    conn = get_connection()

    # Admin e enterprise veem tudo; free e pro veem apenas o que lhes cabe
    plano = usuario["plano"]
    if plano == "free":
        scripts = conn.execute(
            "SELECT * FROM scripts WHERE plano_minimo = 'free' ORDER BY id"
        ).fetchall()
    elif plano == "pro":
        scripts = conn.execute(
            "SELECT * FROM scripts WHERE plano_minimo IN ('free','pro') ORDER BY id"
        ).fetchall()
    else:
        # enterprise e admin veem tudo
        scripts = conn.execute("SELECT * FROM scripts ORDER BY id").fetchall()

    conn.close()
    return {
        "status": "sucesso",
        "total":  len(scripts),
        "scripts": [dict(s) for s in scripts]
    }


@app.post("/scripts", tags=["Scripts"], status_code=201)
def cadastrar_script(dados: ScriptCriar, usuario: dict = Depends(exigir_admin)):
    """
    Cadastra um novo script. Restrito ao administrador.
    O campo 'plano_minimo' define quais planos podem executá-lo.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO scripts (nome, caminho, descricao, params_info, status, plano_minimo)
            VALUES (?,?,?,?,?,?)
            """,
            (dados.nome, dados.caminho, dados.descricao,
             dados.params_info, dados.status, dados.plano_minimo)
        )
        conn.commit()
        novo_id = cursor.lastrowid
        conn.close()
        return {
            "status":   "sucesso",
            "mensagem": f"Script '{dados.nome}' cadastrado com sucesso.",
            "id":       novo_id
        }
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=400, detail={"status": "erro", "mensagem": str(e)})


@app.put("/scripts/{script_id}", tags=["Scripts"])
def atualizar_script(
    script_id: int,
    dados: ScriptAtualizar,
    usuario: dict = Depends(exigir_admin)
):
    """
    Edita um script existente. Restrito ao administrador.
    Só atualiza os campos que foram enviados — os demais permanecem iguais.
    """
    conn = get_connection()
    script = conn.execute("SELECT * FROM scripts WHERE id = ?", (script_id,)).fetchone()

    if not script:
        conn.close()
        raise HTTPException(
            status_code=404,
            detail={"status": "erro", "mensagem": "Script não encontrado."}
        )

    nome         = dados.nome         or script["nome"]
    descricao    = dados.descricao    or script["descricao"]
    params       = dados.params_info  or script["params_info"]
    sts          = dados.status       or script["status"]
    plano_minimo = dados.plano_minimo or script["plano_minimo"]

    conn.execute(
        "UPDATE scripts SET nome=?, descricao=?, params_info=?, status=?, plano_minimo=? WHERE id=?",
        (nome, descricao, params, sts, plano_minimo, script_id)
    )
    conn.commit()
    conn.close()
    return {"status": "sucesso", "mensagem": f"Script ID {script_id} atualizado."}


@app.post("/scripts/{script_id}/executar", tags=["Scripts"])
def executar(
    script_id: int,
    body: ExecutarRequest,
    usuario: dict = Depends(verificar_token)
):
    """
    Executa um script ativo.

    Para usuários (não admin):
      1. Verifica se o plano permite executar este script (plano_minimo).
      2. Verifica se o limite diário de execuções não foi atingido (rate limiting).

    O resultado (stdout/stderr) e a duração são retornados no JSON
    e registrados automaticamente no log de auditoria.
    """
    # Verificações exclusivas para usuários cadastrados (admin tem acesso irrestrito)
    if usuario["tipo"] == "usuario":

        # Passo 1: verifica o plano mínimo do script
        conn = get_connection()
        script = conn.execute(
            "SELECT plano_minimo FROM scripts WHERE id = ? AND status = 'ativo'",
            (script_id,)
        ).fetchone()
        conn.close()

        if script and not usuario_pode_usar_script(usuario["plano"], script["plano_minimo"]):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "status":   "erro",
                    "mensagem": (
                        f"Seu plano '{usuario['plano']}' não tem acesso a este script. "
                        "Faça upgrade para continuar."
                    )
                }
            )

        # Passo 2: verifica o limite diário de execuções
        checar_limite_plano(usuario["id"], usuario["plano"])

    resultado = executar_script(script_id, body.parametros, usuario["id"])

    # HTTP 200 mesmo em falha do script — a API funcionou;
    # o script é que teve problema (código de retorno indica isso).
    return {
        "status":            resultado["status_retorno"],
        "mensagem":          "Execução concluída." if resultado["status_retorno"] == "sucesso"
                             else "O script terminou com erro.",
        "codigo_retorno":    resultado["codigo_retorno"],
        "stdout":            resultado["stdout"],
        "stderr":            resultado["stderr"],
        "duracao_segundos":  resultado["duracao_segundos"]
    }



# ROTAS DE LOGS — consultar histórico de execuções

@app.get("/logs", tags=["Auditoria"])
def consultar_logs(
    limite: int = 50,
    usuario: dict = Depends(verificar_token)
):
    """
    Retorna o histórico das últimas execuções.
    Usuários comuns veem apenas seus próprios logs.
    Administrador vê todos.
    """
    conn = get_connection()

    if usuario["tipo"] == "admin":
        # Admin vê tudo, com nome do script e e-mail do usuário
        registros = conn.execute(
            """
            SELECT e.*, s.nome AS nome_script, u.email AS email_usuario
            FROM execucoes e
            LEFT JOIN scripts  s ON e.script_id  = s.id
            LEFT JOIN usuarios u ON e.usuario_id = u.id
            ORDER BY e.id DESC
            LIMIT ?
            """,
            (limite,)
        ).fetchall()
    else:
        # Usuário vê apenas seus próprios registros
        registros = conn.execute(
            """
            SELECT e.*, s.nome AS nome_script
            FROM execucoes e
            LEFT JOIN scripts s ON e.script_id = s.id
            WHERE e.usuario_id = ?
            ORDER BY e.id DESC
            LIMIT ?
            """,
            (usuario["id"], limite)
        ).fetchall()

    conn.close()
    return {
        "status": "sucesso",
        "total":  len(registros),
        "logs":   [dict(r) for r in registros]
    }


# ROTA DE CONFIGURAÇÃO — trocar o token de administrador

@app.put("/config/token", tags=["Configuração"])
def trocar_token(
    dados: TrocarTokenRequest,
    usuario: dict = Depends(exigir_admin)
):
    """
    Troca o token global de administrador sem reiniciar a API.
    O novo token entra em vigor imediatamente.
    """
    if not dados.novo_token or len(dados.novo_token) < 8:
        raise HTTPException(
            status_code=400,
            detail={"status": "erro", "mensagem": "O novo token deve ter pelo menos 8 caracteres."}
        )

    conn = get_connection()
    conn.execute(
        "UPDATE configuracoes SET valor = ? WHERE chave = 'token'",
        (dados.novo_token,)
    )
    conn.commit()
    conn.close()

    return {
        "status":   "sucesso",
        "mensagem": "Token de admin atualizado com sucesso."
    }


# ROTAS DE USUÁRIOS — cadastro, login, perfil, plano

@app.post("/usuarios/registrar", tags=["Usuários"], status_code=201)
def registrar(dados: UsuarioRegistrar):
    """
    Cria uma nova conta com plano 'free'.
    Rota pública — não precisa de token.

    Retorna o token de API gerado, que deve ser usado como X-Isy-Token
    nas demais requisições.
    """
    novo = registrar_usuario(dados.email, dados.senha)
    return {
        "status":   "sucesso",
        "mensagem": "Conta criada com sucesso. Guarde seu token de API!",
        "usuario":  {
            "id":    novo["id"],
            "email": novo["email"],
            "plano": novo["plano"],
            "token": novo["token"]   # ← guarde este valor!
        }
    }


@app.post("/usuarios/login", tags=["Usuários"])
def login(dados: UsuarioLogin):
    """
    Autentica com e-mail e senha e retorna o token de API.
    Rota pública — não precisa de token.
    """
    autenticado = autenticar_usuario(dados.email, dados.senha)
    return {
        "status":   "sucesso",
        "mensagem": "Login realizado com sucesso.",
        "usuario":  {
            "id":    autenticado["id"],
            "email": autenticado["email"],
            "plano": autenticado["plano"],
            "token": autenticado["token"]
        }
    }


@app.get("/usuarios/meu-perfil", tags=["Usuários"])
def meu_perfil(usuario: dict = Depends(verificar_token)):
    """
    Retorna os dados do usuário autenticado.
    Útil para o site saber qual plano exibir na interface.
    """
    if usuario["tipo"] == "admin":
        return {
            "status":  "sucesso",
            "usuario": {"tipo": "admin", "plano": "enterprise", "email": "admin"}
        }

    conn = get_connection()
    row = conn.execute(
        "SELECT id, email, plano, criado_em FROM usuarios WHERE id = ?",
        (usuario["id"],)
    ).fetchone()
    conn.close()

    if not row:
        raise HTTPException(404, {"status": "erro", "mensagem": "Usuário não encontrado."})

    # Inclui informações do plano para o site exibir
    from app.users import LIMITES_POR_PLANO
    limite_diario = LIMITES_POR_PLANO.get(row["plano"])

    return {
        "status":  "sucesso",
        "usuario": {
            "id":            row["id"],
            "email":         row["email"],
            "plano":         row["plano"],
            "criado_em":     row["criado_em"],
            "limite_diario": limite_diario if limite_diario is not None else "ilimitado"
        }
    }


@app.get("/usuarios", tags=["Usuários"])
def listar_usuarios(
    limite: int = 50,
    usuario: dict = Depends(exigir_admin)
):
    """
    Lista todos os usuários cadastrados. Restrito ao administrador.
    Nunca retorna senha_hash nem token — apenas dados de perfil.
    """
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, email, plano, criado_em, ativo FROM usuarios ORDER BY id DESC LIMIT ?",
        (limite,)
    ).fetchall()
    conn.close()

    return {
        "status":   "sucesso",
        "total":    len(rows),
        "usuarios": [dict(r) for r in rows]
    }


@app.put("/usuarios/{usuario_id}/plano", tags=["Usuários"])
def alterar_plano(
    usuario_id: int,
    dados: AtualizarPlano,
    admin: dict = Depends(exigir_admin)
):
    """
    Muda o plano de um usuário manualmente. Restrito ao administrador.
    Use para correções manuais ou testes. O Stripe faz isso automaticamente em produção.
    """
    atualizar_plano_usuario(usuario_id, dados.plano)
    return {
        "status":   "sucesso",
        "mensagem": f"Plano do usuário ID {usuario_id} atualizado para '{dados.plano}'."
    }



# ROTAS DE ANALYTICS — métricas e estatísticas (somente admin)

@app.get("/analytics/resumo", tags=["Analytics"])
def analytics_resumo(
    data: str = None,
    admin: dict = Depends(exigir_admin)
):
    """
    Resumo do dia: total de execuções, sucessos, falhas, taxa de falha e tempo médio.

    Parâmetro de query (opcional):
      ?data=2026-06-01   — analisa um dia específico (formato AAAA-MM-DD)
      sem parâmetro      — usa o dia de hoje
    """
    return {"status": "sucesso", "resumo": resumo_periodo(data)}


@app.get("/analytics/scripts-mais-usados", tags=["Analytics"])
def analytics_scripts(
    limite: int = 10,
    admin: dict = Depends(exigir_admin)
):
    """
    Ranking dos scripts mais executados de todos os tempos,
    com contagem de sucessos, falhas e tempo médio de execução.

    Parâmetro de query (opcional):
      ?limite=5   — retorna apenas os 5 primeiros (padrão: 10)
    """
    return {
        "status":  "sucesso",
        "ranking": scripts_mais_usados(limite)
    }


@app.get("/analytics/clientes-mais-ativos", tags=["Analytics"])
def analytics_clientes(
    limite: int = 10,
    admin: dict = Depends(exigir_admin)
):
    """
    Ranking dos clientes com mais chamados à API,
    com total de execuções, falhas e data da última execução.

    Parâmetro de query (opcional):
      ?limite=5   — retorna apenas os 5 primeiros (padrão: 10)
    """
    return {
        "status":  "sucesso",
        "ranking": clientes_mais_ativos(limite)
    }


@app.get("/analytics/falhas", tags=["Analytics"])
def analytics_falhas(
    data: str = None,
    limite: int = 50,
    admin: dict = Depends(exigir_admin)
):
    """
    Lista detalhada das execuções com falha em um dia.
    Útil para diagnóstico rápido de problemas.

    Parâmetros de query (opcionais):
      ?data=2026-06-01   — analisa um dia específico (padrão: hoje)
      ?limite=20         — máximo de registros retornados (padrão: 50)
    """
    return {
        "status": "sucesso",
        "falhas": falhas_do_dia(data, limite)
    }



# WEBHOOK DO STRIPE — recebe eventos de pagamento

@app.post("/webhooks/stripe", tags=["Pagamentos"])
async def webhook_stripe(request: Request):
    """
    Endpoint chamado automaticamente pelo Stripe após eventos de pagamento.
    Rota pública — a segurança é feita pela verificação de assinatura do Stripe.

    Configure este URL no painel do Stripe:
      Developers → Webhooks → Add endpoint → https://sua-api.com/webhooks/stripe

    Eventos tratados:
      checkout.session.completed    → upgrade de plano
      customer.subscription.deleted → rebaixar para free
      invoice.payment_failed        → rebaixar para free
    """
    return await processar_webhook_stripe(request)
