#!/bin/bash
# checar_docker.sh — Verifica o status dos containers Docker em execução.
#
# Uso: bash checar_docker.sh [filtro_opcional]
# Exemplo sem filtro: bash checar_docker.sh
# Exemplo com filtro: bash checar_docker.sh isyshell
#
# Retorna informações sobre containers ativos e parados.

FILTRO="${1:-}"

echo "=== IsyShell: Diagnóstico de Containers Docker ==="
echo "Data/hora: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# Verifica se o comando docker está disponível neste ambiente
if ! command -v docker &>/dev/null; then
    echo "AVISO: O comando 'docker' não está disponível neste container."
    echo "Em produção, este script seria executado no servidor host."
    echo ""
    echo "Simulação do que seria exibido:"
    echo "  CONTAINER ID   IMAGE          STATUS         NAMES"
    echo "  a1b2c3d4e5f6   isyshell_app   Up 2 hours     isyshell-app-1"
    echo "  f6e5d4c3b2a1   nginx:latest   Up 5 minutes   webserver"
    echo ""
    echo "=== Diagnóstico simulado concluído ==="
    exit 0
fi

# Lista containers em execução
echo "--- Containers em execução ---"
if [ -z "$FILTRO" ]; then
    docker ps --format "table {{.ID}}\t{{.Image}}\t{{.Status}}\t{{.Names}}"
else
    docker ps --format "table {{.ID}}\t{{.Image}}\t{{.Status}}\t{{.Names}}" | grep "$FILTRO"
fi

echo ""
echo "--- Containers parados (últimos 5) ---"
docker ps -a --filter "status=exited" --format "table {{.ID}}\t{{.Image}}\t{{.Status}}\t{{.Names}}" | head -6

echo ""
# Conta containers ativos
ATIVOS=$(docker ps -q | wc -l)
echo "Total de containers ativos: $ATIVOS"

echo ""
echo "=== Diagnóstico concluído! ==="
exit 0
