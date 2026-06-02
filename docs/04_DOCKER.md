# 04 — Docker: Imagem, Container e Volume

## O que é Docker? (Para leigos)

Imagine que você precisa enviar uma receita de bolo para um amigo em outra cidade.
Mas você quer garantir que o bolo vai sair exatamente igual ao seu, não importa
a cozinha do amigo. A solução: enviar não só a receita, mas **a cozinha inteira**
— fogão, ingredientes, utensílios, tudo — empacotada numa caixa.

**Docker** é exatamente isso para software:
- **Imagem** = a "caixa" com tudo que o app precisa (sistema operacional, Python, código)
- **Container** = a caixa aberta e rodando — é a instância da imagem em execução
- **Volume** = uma janela na caixa que permite trocar arquivos com o mundo externo

Com Docker, "funciona na minha máquina" deixa de ser problema — funciona em qualquer lugar.

---

## O Dockerfile Explicado Linha a Linha

```dockerfile
# Define a imagem base: Python 3.11 numa versão mínima do Linux (~50MB)
FROM python:3.11-slim

# Define /app como a pasta padrão de trabalho dentro do container
WORKDIR /app

# Copia só o requirements.txt primeiro (otimização de cache do Docker)
COPY requirements.txt .

# Instala as dependências Python (resultado é cacheado enquanto requirements.txt não mudar)
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código da aplicação para dentro da imagem
COPY app/ ./app/

# Cria a pasta onde o SQLite vai salvar o banco de dados
RUN mkdir -p /app/data

# Documenta que o container usa a porta 8000 (não publica automaticamente)
EXPOSE 8000

# Comando executado quando o container inicia
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## O docker-compose.yml Explicado Linha a Linha

```yaml
services:          # lista de serviços (containers) a gerenciar
  isyshell:        # nome do serviço

    build: .       # constrói a imagem usando o Dockerfile da pasta atual

    container_name: isyshell-app  # nome fixo para identificar o container

    ports:
      - "8000:8000"  # porta_host:porta_container — acesse em localhost:8000

    volumes:
      # Monta ./scripts/ do host como /scripts no container (só leitura)
      - ./scripts:/scripts:ro

      # Persiste o banco SQLite em ./data/ no host (sobrevive ao container parar)
      - ./data:/app/data

    environment:
      - SCRIPTS_PATH=/scripts          # onde a API busca os scripts
      - DATABASE_PATH=/app/data/isyshell.db
      - DISCORD_WEBHOOK_URL=           # vazio = alertas desligados

    restart: unless-stopped  # reinicia automaticamente se travar
```

---

## Por que o Volume de Scripts é Importante?

Sem o volume:
```
Container contém: código + scripts gravados dentro da imagem
Problema: para adicionar um novo script, precisa rebuildar a imagem inteira
```

Com o volume:
```
Container lê: /scripts (que na verdade é ./scripts/ na sua máquina)
Benefício: adicione ou edite um .sh no seu computador — a API vê na hora, sem rebuild!
```

---

## Comandos Úteis

```bash
# Construir a imagem e subir o container em background
docker-compose up --build -d

# Ver os logs em tempo real
docker-compose logs -f

# Parar o container
docker-compose down

# Abrir um terminal dentro do container (para depuração)
docker-compose exec isyshell bash

# Verificar se o container está rodando
docker ps
```
