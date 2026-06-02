import httpx
import os
import logging

# URL do webhook configurada por variavel de ambiente.
# Compativel com qualquer servico que aceite POST com JSON (Discord, Slack, Teams, etc).
# Se nao configurada, os alertas sao silenciosamente ignorados.
ALERT_WEBHOOK_URL = os.getenv("ALERT_WEBHOOK_URL", None)

logger = logging.getLogger(__name__)


async def enviar_alerta_falha(nome_script: str, stderr: str, parametros: str):
    """
    Envia um alerta HTTP para o webhook configurado quando um script falha.
    Chamada de forma assincrona para nao bloquear a resposta da API.
    O payload segue o formato generico { "content": "..." }, compativel com
    Discord, Slack (via Incoming Webhooks) e qualquer endpoint que aceite JSON.
    """
    if not ALERT_WEBHOOK_URL:
        return

    payload = {
        "content": (
            f"[FALHA] IsyShell\n"
            f"Script: {nome_script}\n"
            f"Parametros: {parametros or '(nenhum)'}\n"
            f"Erro: {stderr[:500] or '(sem mensagem de erro)'}\n"
            f"Consulte /logs para detalhes."
        )
    }

    try:
        async with httpx.AsyncClient() as client:
            resposta = await client.post(ALERT_WEBHOOK_URL, json=payload, timeout=5.0)
            if resposta.status_code not in (200, 204):
                logger.warning(f"Alerta falhou — status {resposta.status_code}: {resposta.text}")
    except Exception as e:
        # Falha no sistema de alertas nao deve derrubar a API principal
        logger.warning(f"Nao foi possivel enviar alerta: {e}")
