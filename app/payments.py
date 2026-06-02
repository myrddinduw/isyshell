import json
import os

from fastapi import HTTPException, Request

from app.database import get_connection
from app.users import atualizar_plano_usuario

# Mapeamento de price_id do Stripe para plano interno.
# Configure os IDs reais em STRIPE_PRICE_PRO e STRIPE_PRICE_ENTERPRISE no ambiente.
STRIPE_PRECO_PARA_PLANO: dict = {
    os.getenv("STRIPE_PRICE_PRO",        "price_pro_placeholder"):        "pro",
    os.getenv("STRIPE_PRICE_ENTERPRISE", "price_enterprise_placeholder"): "enterprise",
}

STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")


async def processar_webhook_stripe(request: Request) -> dict:
    """
    Processa eventos do Stripe enviados ao endpoint POST /webhooks/stripe.

    Eventos tratados:
      checkout.session.completed    -> upgrade de plano
      customer.subscription.deleted -> rebaixar para free
      invoice.payment_failed        -> rebaixar para free
    """
    corpo_bytes = await request.body()
    assinatura  = request.headers.get("stripe-signature", "")

    # Em producao, verificar a assinatura garante que o evento veio do Stripe.
    # Para ativar: pip install stripe e descomentar o bloco abaixo.
    #
    # import stripe
    # try:
    #     evento = stripe.Webhook.construct_event(corpo_bytes, assinatura, STRIPE_WEBHOOK_SECRET)
    # except stripe.error.SignatureVerificationError:
    #     raise HTTPException(400, {"status": "erro", "mensagem": "Assinatura Stripe invalida."})

    try:
        evento = json.loads(corpo_bytes)
    except Exception:
        raise HTTPException(400, {"status": "erro", "mensagem": "Payload JSON invalido."})

    tipo_evento = evento.get("type", "")
    dados       = evento.get("data", {}).get("object", {})

    if tipo_evento == "checkout.session.completed":
        email_cliente = dados.get("customer_email", "")
        # price_id deve ser enviado no metadata da sessao Stripe pelo site
        price_id      = dados.get("metadata", {}).get("price_id", "")
        novo_plano    = STRIPE_PRECO_PARA_PLANO.get(price_id)

        if not email_cliente or not novo_plano:
            return {"status": "ignorado", "mensagem": "Dados insuficientes no evento."}

        usuario_id = _buscar_id_por_email(email_cliente)
        if usuario_id:
            atualizar_plano_usuario(usuario_id, novo_plano)
            return {"status": "sucesso", "mensagem": f"Plano atualizado para '{novo_plano}' — {email_cliente}"}

    elif tipo_evento in ("customer.subscription.deleted", "invoice.payment_failed"):
        email_cliente = dados.get("customer_email", "")
        if email_cliente:
            usuario_id = _buscar_id_por_email(email_cliente)
            if usuario_id:
                atualizar_plano_usuario(usuario_id, "free")
                return {"status": "sucesso", "mensagem": f"Plano rebaixado para 'free' — {email_cliente}"}

    return {"status": "ignorado", "mensagem": f"Evento '{tipo_evento}' nao processado."}


def _buscar_id_por_email(email: str) -> int | None:
    conn = get_connection()
    row  = conn.execute("SELECT id FROM usuarios WHERE email = ?", (email,)).fetchone()
    conn.close()
    return row["id"] if row else None
