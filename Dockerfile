# Dockerfile — Receita para construir a imagem Docker do IsyShell.
#
# O que é uma imagem? É um "pacote" com tudo que o app precisa para rodar:
# o sistema operacional mínimo, o Python e o nosso código.
# O container é uma instância dessa imagem rodando.

# INSTRUÇÃO FROM: define a imagem base.
# "python:3.11-slim" = Python 3.11 em cima de um Debian mínimo (~50 MB).
# Usamos "slim" em vez da versão completa para deixar a imagem menor e mais segura
# (menos pacotes instalados = menos superfície de ataque).
FROM python:3.11-slim

# INSTRUÇÃO WORKDIR: define a pasta de trabalho dentro do container.
# Todos os comandos seguintes serão executados a partir de /app.
WORKDIR /app

# INSTRUÇÃO COPY (requirements primeiro): copiamos só o requirements.txt antes do código.
# POR QUÊ? O Docker guarda cada passo em "cache". Se só o código mudar,
# o Docker pula a instalação das bibliotecas e usa o cache — build mais rápido.
COPY requirements.txt .

# INSTRUÇÃO RUN: executa um comando durante a construção da imagem.
# --no-cache-dir = não guarda cache local do pip (economiza espaço na imagem)
RUN apt-get update && apt-get install -y --no-install-recommends tzdata && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r requirements.txt

# Copia o resto do código para dentro da imagem
COPY app/ ./app/

# Cria a pasta de dados onde o SQLite vai salvar o arquivo .db
RUN mkdir -p /app/data

# INSTRUÇÃO EXPOSE: documenta que o container usa a porta 8000.
# Isso não publica a porta automaticamente — o docker-compose faz isso.
EXPOSE 8000

# INSTRUÇÃO CMD: o comando que roda quando o container inicia.
# uvicorn = servidor web; app.main:app = módulo app/main.py, variável "app"
# --host 0.0.0.0 = aceita conexões de qualquer IP (necessário no Docker)
# --port 8000 = porta que o servidor vai escutar
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
