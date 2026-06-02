# 06 — Glossário de Termos Técnicos

| Termo | Definição |
|---|---|
| **API** | Interface de Programação de Aplicações — um conjunto de regras que define como dois sistemas se comunicam. |
| **REST** | Estilo de arquitetura para APIs web que usa URLs e métodos HTTP (GET, POST, PUT, DELETE). |
| **Endpoint** | Um endereço específico da API que executa uma ação, ex: `/scripts/1/executar`. |
| **JSON** | JavaScript Object Notation — formato de texto para trocar dados estruturados, ex: `{"chave": "valor"}`. |
| **HTTP** | Protocolo de comunicação da web; define como navegadores e servidores trocam mensagens. |
| **Header** | Cabeçalho de uma requisição HTTP; carrega metadados como o token de autenticação. |
| **Token** | Senha temporária ou chave secreta usada para provar identidade numa API. |
| **X-Isy-Token** | Header personalizado deste projeto para autenticação; o prefixo "X-" indica header personalizado. |
| **Autenticação** | Processo de verificar quem é o usuário (provar identidade). |
| **Autorização** | Processo de verificar o que o usuário pode fazer (permissões). |
| **HTTP 401** | Código de resposta: "não autorizado" — credenciais ausentes ou inválidas. |
| **HTTP 403** | Código de resposta: "proibido" — autenticado, mas sem permissão para aquela ação. |
| **HTTP 404** | Código de resposta: "não encontrado" — recurso inexistente. |
| **HTTP 429** | Código de resposta: "muitas requisições" — limite de uso atingido (rate limiting). |
| **subprocess** | Módulo nativo do Python que permite executar comandos do sistema operacional. |
| **stdout** | "Standard Output" — a saída normal de um programa/script (o que aparece no terminal). |
| **stderr** | "Standard Error" — a saída de erros de um programa/script (erros e avisos). |
| **Código de retorno** | Número que um programa retorna ao terminar; 0 = sucesso, qualquer outro = algum problema. |
| **shell=True** | Opção do subprocess que passa o comando para o /bin/sh interpretar — perigoso com dados de usuário. |
| **Command Injection** | Ataque que insere comandos maliciosos em dados enviados para uma aplicação vulnerável. |
| **Whitelist** | Lista de valores permitidos; qualquer coisa fora da lista é rejeitada. |
| **Regex** | Expressão Regular — padrão de texto para validar ou buscar strings. Ex: `r'^[\w]+$'` aceita só letras. |
| **SQLite** | Banco de dados leve que vive num único arquivo .db, sem servidor separado. |
| **FastAPI** | Framework Python moderno para criar APIs REST, com validação automática e docs Swagger. |
| **Pydantic** | Biblioteca Python para validar e estruturar dados automaticamente usando type hints. |
| **Docker** | Plataforma que empacota aplicações em containers para garantir execução consistente. |
| **Imagem Docker** | "Receita" imutável com tudo que o app precisa para rodar. |
| **Container** | Instância rodando de uma imagem Docker — isolado do resto do sistema. |
| **Volume** | Mecanismo Docker que monta uma pasta do host dentro do container para compartilhar arquivos. |
| **docker-compose** | Ferramenta para definir e rodar múltiplos containers com um único arquivo de configuração. |
| **Uvicorn** | Servidor web ASGI para Python — é ele que "serve" a API FastAPI na porta 8000. |
| **Swagger** | Interface web gerada automaticamente pelo FastAPI em `/docs` para testar a API no navegador. |
| **Webhook** | URL que recebe requisições HTTP quando um evento ocorre em outro sistema (ex: pagamento confirmado). |
| **Variável de ambiente** | Valor de configuração passado ao programa pelo sistema operacional, sem precisar alterar código. |
| **SSH** | Secure Shell — protocolo para acesso remoto seguro a servidores Linux via terminal. |
| **ASGI** | Interface padrão para servidores web Python assíncronos — permite atender várias requisições ao mesmo tempo. |
| **Auditoria** | Registro detalhado de todas as ações realizadas num sistema, com data, hora e responsável. |
| **Shell script** | Arquivo de texto com comandos do terminal (bash) que podem ser executados em sequência. |
| **Freemium** | Modelo de negócio com plano gratuito limitado e planos pagos com mais recursos. |
| **Rate Limiting** | Técnica que limita quantas vezes um usuário pode usar um recurso num período (ex: 10/dia). |
| **Plano** | Nível de acesso de um usuário no sistema freemium: free, pro ou enterprise. |
| **Hash** | Resultado de uma função matemática irreversível; usado para armazenar senhas com segurança. |
| **PBKDF2** | Algoritmo padrão de hash para senhas; aplica SHA-256 com muitas iterações para dificultar ataques. |
| **Salt** | Valor aleatório adicionado à senha antes do hash; garante que senhas iguais gerem hashes diferentes. |
| **Stripe** | Plataforma de pagamentos online; usada para cobrar assinaturas e notificar upgrades via webhook. |
| **Analytics** | Análise de dados de uso do sistema para extrair métricas e estatísticas relevantes. |
| **Dashboard** | Painel visual com resumo de métricas em tempo real. |
| **Dependência (FastAPI)** | Função executada automaticamente pelo FastAPI antes de uma rota — usada para autenticação e validações. |
| **Migration** | Alteração incremental no esquema do banco de dados sem apagar dados existentes (ex: ADD COLUMN). |
