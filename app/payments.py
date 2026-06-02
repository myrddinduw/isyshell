# payments.py — Integração com Stripe para upgrades de plano automáticos.
#
# O que é um webhook?
# Quando um cliente faz um pagamento, o Stripe precisa avisar a sua API.
# Em vez de sua API ficar perguntando "tem pagamento novo?" a cada segundo,
# o Stripe envia um POST para um endereço seu (o webhook) logo após o evento.
#
# Fluxo completo:
#   1. Usuário clica "Assinar Pro" no site
#   2. Site redireciona para a página de pagamento do Stripe
#   3. Usuário paga
#   4. Stripe envia POST para  POST /webhooks/stripe  com os detalhes
#   5. Esta função atualiza o plano no banco
#   6. Na próxima requisição, o usuário já tem acesso Pro
#
# Para ativar a verificação de assinatura (produção):
#   pip install stripe
#   Configure STRIPE_WEBHOOK_SECRET no .env ou docker-compose.yml
#
# Variáveis de ambiente necessárias:
#   STRIPE_WEBHOOK_SECRET      — segredo do webhook (painel Stripe → Webhooks)
#   STRIPE_PRICE_PRO           — ID do preço Pro (ex: price_1AbCdEfG...)
#   STRIPE_PRICE_ENTERPRISE    — ID do preço Enterprise

import json
import os

from fastapi import HTTPException, Request

from app.database import get_connection
from app.users import atualizar_plano_usuario

# Mapeamento: ID do preço no Stripe → nome do plano no nosso sistema.
# Configure os IDs reais no painel do Stripe → Products → Prices.
STRIPE_PRECO_PARA_PLANO: dict = {
    os.getenv("STRIPE_PRICE_PRO",        "price_pro_placeholder"):        "pro",
    os.getenv("STRIPE_PRICE_ENTERPRISE", "price_enterprise_placeholder"): "enterprise",
}

STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")


async def processar_webhook_stripe(request: Request) -> dict:
    """
    Processa os eventos enviados pelo Stripe ao endpoint POST /webhooks/stripe.

    Eventos tratados:
      checkout.session.completed       → pagamento confirmado → upgrade de plano
      customer.subscription.deleted    → assinatura cancelada → rebaixar para free
      invoice.payment_failed           → cobrança recusada   → rebaixar para free

    Qualquer outro evento é ignorado com resposta {"status": "ignorado"}.
    """
    corpo_bytes = await request.body()
    assinatura  = request.headers.get("stripe-signature", "")

    # ----------------------------------------------------------------
    # VERIFICAÇÃO DE ASSINATURA (descomente em produção)
    #
    # O Stripe assina cada requisição com STRIPE_WEBHOOK_SECRET.
    # Verificar a assinatura garante que o evento veio mesmo do Stripe
    # e não de alguém tentando forjar um upgrade de plano.
    #
    # Para ativar:
    #   1. pip install stripe
    #   2. Descomente o bloco abaixo
    #   3. Configure STRIPE_WEBHOOK_SECRET no seu ambiente
    #
    # import stripe
    # try:
    #     evento = stripe.Webhook.construct_event(
    #         corpo_bytes, assinatura, STRIPE_WEBHOOK_SECRET
    #     )
    # except stripe.error.SignatureVerificationError:
    #     raise HTTPException(400, {"status": "erro", "mensagem": "Assinatura Stripe inválida."})
    # ----------------------------------------------------------------

    # Versão de desenvolvimento: lê o JSON sem verificar assinatura
    try:
        evento = json.loads(corpo_bytes)
    except Exception:
        raise HTTPException(
            status_code=400,
            detail={"status": "erro", "mensagem": "Payload JSON inválido."}
        )

    tipo_evento = evento.get("type", "")
    dados       = evento.get("data", {}).get("object", {})

    # ── Pagamento confirmado → fazer upgrade ──────────────────────────────────
    if tipo_evento == "checkout.session.completed":
        email_cliente = dados.get("customer_email", "")
        # O price_id vem no metadata que o site deve enviar ao criar a sessão Stripe
        price_id      = dados.get("metadata", {}).get("price_id", "")
        novo_plano    = STRIPE_PRECO_PARA_PLANO.get(price_id)

        if not email_cliente or not novo_plano:
            return {"status": "ignorado", "mensagem": "Dados insuficientes no evento."}

        usuario_id = _buscar_id_por_email(email_cliente)
        if usuario_id:
            atualizar_plano_usuario(usuario_id, novo_plano)
            return {
                "status":   "sucesso",
                "mensagem": f"Plano atualizado para '{novo_plano}' — {email_cliente}"
            }

    # ── Assinatura cancelada ou cobrança recusada → rebaixar para free ────────
    elif tipo_evento in ("customer.subscription.deleted", "invoice.payment_failed"):
        email_cliente = dados.get("customer_email", "")

        if email_cliente:
            usuario_id = _buscar_id_por_email(email_cliente)
            if usuario_id:
                atualizar_plano_usuario(usuario_id, "free")
                return {
                    "status":   "sucesso",
                    "mensagem": f"Plano rebaixado para 'free' — {email_cliente}"
                }

    return {"status": "ignorado", "mensagem": f"Evento '{tipo_evento}' não processado."}


def _buscar_id_por_email(email: str) -> int | None:
    """Retorna o ID do usuário com o e-mail informado, ou None se não existir."""
    conn = get_connection()
    row  = conn.execute(
        "SELECT id FROM usuarios WHERE email = ?", (email,)
    ).fetchone()
    conn.close()
    return row["id"] if row else None
