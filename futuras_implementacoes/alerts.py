# alerts.py — Diferencial: envia um alerta no Discord quando um script falha.
#
# Como funciona?
# O Discord permite que qualquer pessoa envie mensagens num canal via uma URL
# chamada "Webhook". Basta fazer um POST HTTP para essa URL com a mensagem.
# Usamos a biblioteca "httpx" (assíncrona, ideal para FastAPI) para fazer isso.
#
# Como configurar: no arquivo docker-compose.yml, defina a variável de ambiente:
#   DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/SEU/WEBHOOK
# Se a variável não estiver definida, o alerta é silenciosamente ignorado.

import httpx
import os
import logging

# Lê a URL do webhook da variável de ambiente. Retorna None se não estiver definida.
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", None)

# Logger para registrar erros do próprio sistema de alertas sem quebrar a API
logger = logging.getLogger(__name__)


async def enviar_alerta_falha(nome_script: str, stderr: str, parametros: str):
    """
    Envia uma mensagem de alerta para o canal do Discord configurado.
    É chamada somente quando um script termina com status de falha.

    Esta função é "async" porque o FastAPI trabalha de forma assíncrona:
    enquanto aguarda a resposta do Discord, ele pode atender outras requisições.
    """

    # Se a URL não estiver configurada, não faz nada — o recurso está desligado
    if not DISCORD_WEBHOOK_URL:
        return

    # Monta a mensagem com emojis para facilitar a leitura no Discord
    mensagem = (
        f"🚨 **IsyShell — Falha na Execução** 🚨\n"
        f"**Script:** `{nome_script}`\n"
        f"**Parâmetros usados:** `{parametros or '(nenhum)'}`\n"
        f"**Erro reportado:**\n```\n{stderr[:500] or '(sem mensagem de erro)'}\n```\n"
        f"*Verifique o log de auditoria em /logs para mais detalhes.*"
    )

    # O Discord espera um JSON com a chave "content" contendo o texto da mensagem
    payload = {"content": mensagem}

    try:
        # Fazemos a requisição de forma assíncrona com httpx
        async with httpx.AsyncClient() as client:
            resposta = await client.post(
                DISCORD_WEBHOOK_URL,
                json=payload,
                timeout=5.0  # Não espera mais que 5 segundos pelo Discord
            )

            if resposta.status_code not in (200, 204):
                logger.warning(
                    f"Alerta Discord falhou com status {resposta.status_code}: {resposta.text}"
                )

    except Exception as e:
        # Erros no sistema de alertas NÃO devem derrubar a API principal
        logger.warning(f"Não foi possível enviar alerta para o Discord: {e}")
