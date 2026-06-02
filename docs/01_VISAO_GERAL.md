# 01 — Visão Geral do Projeto IsyShell

## O Problema

A **ISY.ONE** é uma empresa que administra servidores Linux para seus clientes.
Hoje, quando algo precisa ser feito no servidor — limpar logs antigos, reiniciar um serviço, verificar o status dos containers — um técnico precisa:

1. Abrir um terminal.
2. Fazer login via **SSH** (protocolo de acesso remoto seguro).
3. Digitar o comando manualmente.
4. Verificar se funcionou.

Isso tem vários problemas:
- **Demora**: cada operação exige uma pessoa especializada conectada ao servidor.
- **Risco humano**: um erro de digitação pode apagar arquivos ou derrubar um serviço.
- **Sem rastreamento**: não há registro automático de quem fez o quê e quando.
- **Não escalável**: com dezenas de servidores, fazer isso manualmente é inviável.

## A Solução: IsyShell

O **IsyShell** é uma **API REST** que funciona como um "painel de controle remoto" para o servidor. Em vez de fazer login via SSH, qualquer sistema autorizado (um site, um aplicativo, um bot) pode enviar uma requisição HTTP para executar scripts pré-aprovados, com segurança total.

```
ANTES (manual):
Técnico → SSH → Servidor → digita comando → vê o resultado

DEPOIS (com IsyShell):
Sistema/Pessoa → HTTP → IsyShell API → executa script aprovado → retorna resultado em JSON
```

---

## O que é uma API REST? (Explicação para leigos)

Imagine que você está num restaurante:
- O **cardápio** lista o que você pode pedir (os endpoints disponíveis).
- O **garçom** recebe seu pedido, leva para a cozinha e traz o resultado (a API).
- A **cozinha** faz o trabalho real (o servidor Linux rodando os scripts).
- Você **nunca entra na cozinha** — só faz pedidos pelo garçom (isso é segurança!).

Uma **API REST** funciona assim:
- Você envia uma requisição HTTP para um endereço (ex: `http://servidor:8000/scripts/1/executar`).
- A API processa o pedido e devolve uma resposta em **JSON** (um formato de texto estruturado).
- Você não precisa saber como o servidor funciona por dentro — só precisa saber o que pedir e como interpretar a resposta.

**REST** significa "Representational State Transfer" — um conjunto de boas práticas para criar APIs web simples e previsíveis.

---

## Resumo dos Benefícios

| Problema Antigo | Solução com IsyShell |
|---|---|
| Acesso SSH manual | Requisição HTTP automatizada |
| Sem controle de acesso | Token X-Isy-Token obrigatório |
| Sem registro de ações | Log automático no banco SQLite |
| Risco de comando errado | Lista branca de scripts aprovados |
| Sem alertas de falha | Webhook Discord em tempo real |
