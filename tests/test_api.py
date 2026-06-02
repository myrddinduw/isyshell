import os
import tempfile
import pytest

# Define o banco temporario ANTES de qualquer import da app
_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_PATH"] = _db_path
os.environ["SCRIPTS_PATH"]  = os.path.join(os.path.dirname(__file__), "..", "scripts")

from fastapi.testclient import TestClient
from app.main import app

ADMIN_TOKEN   = "meu-token-secreto-troque-isso"
HEADERS_ADMIN = {"X-Isy-Token": ADMIN_TOKEN}


@pytest.fixture(scope="session")
def client():
    # O context manager dispara os eventos startup/shutdown da app
    with TestClient(app) as c:
        yield c


def _registrar(client, email, senha="senha1234"):
    r = client.post("/usuarios/registrar", json={"email": email, "senha": senha})
    return r.json()["usuario"]


# ---------------------------------------------------------------------------
# Saude
# ---------------------------------------------------------------------------

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# Autenticacao
# ---------------------------------------------------------------------------

def test_token_invalido_retorna_401(client):
    r = client.get("/scripts", headers={"X-Isy-Token": "token-errado"})
    assert r.status_code == 401

def test_sem_token_retorna_422(client):
    r = client.get("/scripts")
    assert r.status_code == 422

def test_token_admin_valido(client):
    r = client.get("/scripts", headers=HEADERS_ADMIN)
    assert r.status_code == 200

def test_usuario_comum_nao_acessa_rota_admin(client):
    u = _registrar(client, "user_auth@test.com")
    r = client.get("/analytics/resumo", headers={"X-Isy-Token": u["token"]})
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# Usuarios
# ---------------------------------------------------------------------------

def test_registrar_usuario(client):
    r = client.post("/usuarios/registrar", json={"email": "novo@test.com", "senha": "senha1234"})
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "sucesso"
    assert "token" in data["usuario"]
    assert data["usuario"]["plano"] == "free"

def test_registrar_email_duplicado_retorna_400(client):
    client.post("/usuarios/registrar", json={"email": "dup@test.com", "senha": "senha1234"})
    r = client.post("/usuarios/registrar", json={"email": "dup@test.com", "senha": "senha1234"})
    assert r.status_code == 400

def test_registrar_senha_curta_retorna_400(client):
    r = client.post("/usuarios/registrar", json={"email": "curta@test.com", "senha": "123"})
    assert r.status_code == 400

def test_login_correto(client):
    client.post("/usuarios/registrar", json={"email": "login@test.com", "senha": "senha1234"})
    r = client.post("/usuarios/login", json={"email": "login@test.com", "senha": "senha1234"})
    assert r.status_code == 200
    assert "token" in r.json()["usuario"]

def test_login_senha_errada_retorna_401(client):
    client.post("/usuarios/registrar", json={"email": "fail@test.com", "senha": "senha1234"})
    r = client.post("/usuarios/login", json={"email": "fail@test.com", "senha": "errada"})
    assert r.status_code == 401

def test_meu_perfil(client):
    u = _registrar(client, "perfil@test.com")
    r = client.get("/usuarios/meu-perfil", headers={"X-Isy-Token": u["token"]})
    assert r.status_code == 200
    assert r.json()["usuario"]["email"] == "perfil@test.com"
    assert r.json()["usuario"]["limite_diario"] == 10

def test_alterar_plano_como_admin(client):
    u = _registrar(client, "plano@test.com")
    r = client.put(f"/usuarios/{u['id']}/plano", json={"plano": "pro"}, headers=HEADERS_ADMIN)
    assert r.status_code == 200

def test_alterar_plano_invalido_retorna_400(client):
    u = _registrar(client, "plano2@test.com")
    r = client.put(f"/usuarios/{u['id']}/plano", json={"plano": "vip"}, headers=HEADERS_ADMIN)
    assert r.status_code == 400

def test_listar_usuarios_somente_admin(client):
    r = client.get("/usuarios", headers=HEADERS_ADMIN)
    assert r.status_code == 200

    u = _registrar(client, "list@test.com")
    r2 = client.get("/usuarios", headers={"X-Isy-Token": u["token"]})
    assert r2.status_code == 403


# ---------------------------------------------------------------------------
# Scripts
# ---------------------------------------------------------------------------

def test_listar_scripts(client):
    r = client.get("/scripts", headers=HEADERS_ADMIN)
    assert r.status_code == 200
    assert r.json()["total"] >= 2

def test_cadastrar_script_somente_admin(client):
    payload = {"nome": "Teste", "caminho": "teste.sh", "descricao": "", "params_info": "", "status": "ativo", "plano_minimo": "free"}
    u = _registrar(client, "nonadmin@test.com")
    r = client.post("/scripts", json=payload, headers={"X-Isy-Token": u["token"]})
    assert r.status_code == 403

def test_atualizar_script_inexistente_retorna_404(client):
    r = client.put("/scripts/9999", json={"status": "inativo"}, headers=HEADERS_ADMIN)
    assert r.status_code == 404

def test_script_plano_minimo_bloqueia_usuario_free(client):
    client.post("/scripts", json={
        "nome": "Script Pro", "caminho": "pro.sh",
        "descricao": "", "params_info": "", "status": "ativo", "plano_minimo": "pro"
    }, headers=HEADERS_ADMIN)

    scripts = client.get("/scripts", headers=HEADERS_ADMIN).json()["scripts"]
    script_pro = next((s for s in scripts if s["plano_minimo"] == "pro"), None)
    assert script_pro is not None

    u = _registrar(client, "free_block@test.com")
    r = client.post(f"/scripts/{script_pro['id']}/executar",
                    json={"parametros": []}, headers={"X-Isy-Token": u["token"]})
    assert r.status_code == 403

def test_usuario_free_nao_ve_script_pro(client):
    u = _registrar(client, "free_list@test.com")
    scripts = client.get("/scripts", headers={"X-Isy-Token": u["token"]}).json()["scripts"]
    assert all(s["plano_minimo"] == "free" for s in scripts)


# ---------------------------------------------------------------------------
# Execucao
# ---------------------------------------------------------------------------

def test_executar_script_inexistente(client):
    r = client.post("/scripts/9999/executar", json={"parametros": []}, headers=HEADERS_ADMIN)
    assert r.status_code == 200
    assert r.json()["status"] in ("erro", "falha")

def test_executar_parametro_perigoso(client):
    r = client.post("/scripts/1/executar",
                    json={"parametros": ["; rm -rf /"]}, headers=HEADERS_ADMIN)
    assert r.status_code == 200
    assert r.json()["status"] in ("erro", "falha")

def test_execucao_retorna_duracao(client):
    r = client.post("/scripts/1/executar", json={"parametros": []}, headers=HEADERS_ADMIN)
    assert r.status_code == 200
    assert "duracao_segundos" in r.json()


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------

def test_rate_limit_plano_free(client):
    u = _registrar(client, "ratelimit@test.com")

    # Insere 10 execucoes manualmente no banco para simular o limite atingido
    from app.database import get_connection
    from datetime import datetime, timezone
    conn = get_connection()
    for _ in range(10):
        conn.execute(
            "INSERT INTO execucoes (script_id, usuario_id, params_usados, horario, status_retorno) VALUES (?,?,?,?,?)",
            (1, u["id"], "", datetime.now(timezone.utc).isoformat(), "sucesso")
        )
    conn.commit()
    conn.close()

    r = client.post("/scripts/1/executar", json={"parametros": []},
                    headers={"X-Isy-Token": u["token"]})
    assert r.status_code == 429


# ---------------------------------------------------------------------------
# Logs
# ---------------------------------------------------------------------------

def test_logs_usuario_ve_apenas_proprios(client):
    u = _registrar(client, "logs@test.com")
    r = client.get("/logs", headers={"X-Isy-Token": u["token"]})
    assert r.status_code == 200

def test_logs_admin_ve_todos(client):
    r = client.get("/logs", headers=HEADERS_ADMIN)
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

def test_analytics_resumo(client):
    r = client.get("/analytics/resumo", headers=HEADERS_ADMIN)
    assert r.status_code == 200
    resumo = r.json()["resumo"]
    assert "total_execucoes" in resumo
    assert "falhas" in resumo
    assert "taxa_falha_pct" in resumo

def test_analytics_scripts_mais_usados(client):
    r = client.get("/analytics/scripts-mais-usados", headers=HEADERS_ADMIN)
    assert r.status_code == 200
    assert "ranking" in r.json()

def test_analytics_clientes_mais_ativos(client):
    r = client.get("/analytics/clientes-mais-ativos", headers=HEADERS_ADMIN)
    assert r.status_code == 200

def test_analytics_falhas(client):
    r = client.get("/analytics/falhas", headers=HEADERS_ADMIN)
    assert r.status_code == 200

def test_analytics_bloqueado_para_usuario(client):
    u = _registrar(client, "analytics@test.com")
    for endpoint in ["/analytics/resumo", "/analytics/scripts-mais-usados",
                     "/analytics/clientes-mais-ativos", "/analytics/falhas"]:
        r = client.get(endpoint, headers={"X-Isy-Token": u["token"]})
        assert r.status_code == 403, f"Esperado 403 em {endpoint}, recebeu {r.status_code}"


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def test_trocar_token_curto_retorna_400(client):
    r = client.put("/config/token", json={"novo_token": "abc"}, headers=HEADERS_ADMIN)
    assert r.status_code == 400
