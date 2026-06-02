# 09 — Modelo Freemium e Integração de Pagamentos

## Visão Geral

O IsyShell pode ser oferecido como um serviço pago com plano gratuito (freemium).
Este documento explica como o modelo funciona de ponta a ponta,
desde o cadastro do usuário até o upgrade automático via Stripe.

---

## O Modelo Freemium

```
┌─────────────────────────────────────────────────────┐
│                  PLANOS ISYSHELL                     │
├──────────────┬──────────────┬───────────────────────┤
│    FREE       │     PRO      │      ENTERPRISE        │
│  Gratuito     │  R$ X/mês   │     R$ Y/mês           │
├──────────────┼──────────────┼───────────────────────┤
│ 10 exec/dia  │ 500 exec/dia │ Ilimitado              │
│ Scripts free │ Scripts free │ Todos os scripts       │
│              │ + pro        │                        │
└──────────────┴──────────────┴───────────────────────┘
```

O usuário começa no plano **free** ao se cadastrar e pode fazer upgrade a qualquer momento.

---

## Fluxo Completo de Upgrade

```
1. Usuário está logado no site → clica "Assinar Pro"
        ↓
2. Site cria uma sessão de pagamento no Stripe (backend)
   O site deve incluir no metadata: { price_id: "price_ID_do_plano_pro" }
        ↓
3. Usuário é redirecionado para a página de pagamento do Stripe
        ↓
4. Usuário paga com cartão
        ↓
5. Stripe confirma o pagamento e envia um POST para:
   https://sua-api.com/webhooks/stripe
        ↓
6. IsyShell recebe o evento "checkout.session.completed"
   Verifica o price_id no metadata → descobre que é o plano "pro"
   Atualiza no banco: UPDATE usuarios SET plano = 'pro' WHERE email = '...'
        ↓
7. Na próxima requisição do usuário, ele já tem acesso Pro
```

---

## Configuração do Stripe

### 1. Variáveis de ambiente necessárias

Adicione ao seu `docker-compose.yml` ou `.env`:

```yaml
# docker-compose.yml
environment:
  - STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxxxxxxxxx
  - STRIPE_PRICE_PRO=price_1AbCdEfGhIjKlMnOpQrStUv
  - STRIPE_PRICE_ENTERPRISE=price_2AbCdEfGhIjKlMnOpQrStUv
```

### 2. Registrar o webhook no painel do Stripe

```
Painel Stripe → Developers → Webhooks → Add endpoint

URL:    https://sua-api.com/webhooks/stripe
Eventos a ouvir:
  ✅ checkout.session.completed
  ✅ customer.subscription.deleted
  ✅ invoice.payment_failed
```

Após criar, copie o **Signing secret** (`whsec_...`) e coloque em `STRIPE_WEBHOOK_SECRET`.

### 3. Ativar a verificação de assinatura (produção)

No arquivo `app/payments.py`, há um bloco comentado com as instruções:

```python
# 1. Instalar a biblioteca do Stripe:
#    pip install stripe
#    (adicione "stripe" ao requirements.txt)

# 2. Descomente o bloco de verificação em processar_webhook_stripe():
# import stripe
# try:
#     evento = stripe.Webhook.construct_event(
#         corpo_bytes, assinatura, STRIPE_WEBHOOK_SECRET
#     )
# except stripe.error.SignatureVerificationError:
#     raise HTTPException(400, "Assinatura Stripe inválida.")
```

> **Por que isso é importante?**
> Sem verificar a assinatura, qualquer pessoa que descubra a URL do webhook
> poderia enviar um POST falso fingindo um pagamento e obter upgrade de plano grátis.
> A assinatura garante que o evento veio mesmo do Stripe.

---

## Endpoint do Webhook

```
POST /webhooks/stripe
```

Rota pública — o Stripe não envia token. A segurança é a assinatura do payload.

### Eventos tratados

| Evento Stripe                      | O que faz                              |
|------------------------------------|----------------------------------------|
| `checkout.session.completed`       | Atualiza plano para pro/enterprise     |
| `customer.subscription.deleted`    | Rebaixa plano para free                |
| `invoice.payment_failed`           | Rebaixa plano para free                |

### Como o sistema descobre qual plano ativar?

O site, ao criar a sessão de pagamento no Stripe, deve incluir o `price_id` no metadata:

```python
# Exemplo em Python (no seu site/backend)
import stripe

session = stripe.checkout.Session.create(
    customer_email=email_do_usuario,
    payment_method_types=["card"],
    line_items=[{"price": "price_1AbCdEfG...", "quantity": 1}],
    mode="subscription",
    success_url="https://seusite.com/sucesso",
    cancel_url="https://seusite.com/cancelar",
    metadata={
        "price_id": "price_1AbCdEfG..."  # ← IsyShell usa isso para saber qual plano
    }
)
```

---

## Upgrade Manual (para testes e suporte)

O administrador pode mudar o plano de qualquer usuário sem passar pelo Stripe:

```
PUT /usuarios/{id}/plano
Header: X-Isy-Token: <token-admin>
Body:   { "plano": "pro" }
```

Útil para:
- Testes durante o desenvolvimento
- Cortesias para clientes selecionados
- Corrigir inconsistências após falha no webhook

---

## Arquivos relacionados

| Arquivo           | Responsabilidade                              |
|-------------------|-----------------------------------------------|
| `app/payments.py` | Lógica do webhook Stripe                      |
| `app/users.py`    | `atualizar_plano_usuario()` — usada pelo webhook |
| `app/main.py`     | Rota `POST /webhooks/stripe` e `PUT /usuarios/{id}/plano` |

---

## Diagrama de Arquitetura (freemium completo)

```
[Site / App Mobile]
        │
        ├── POST /usuarios/registrar → cria conta free
        ├── POST /usuarios/login     → recupera token
        ├── POST /scripts/1/executar → executa (com limite de plano)
        │
        └── "Assinar Pro" → [Stripe Checkout]
                                    │
                            pagamento confirmado
                                    │
                            POST /webhooks/stripe
                                    │
                            UPDATE usuarios SET plano = 'pro'
                                    │
                            usuário agora tem acesso Pro
```
