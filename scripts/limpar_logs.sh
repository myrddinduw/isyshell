#!/bin/bash
# limpar_logs.sh — Remove arquivos de log mais antigos que N dias.
#
# Uso: bash limpar_logs.sh <pasta> <dias>
# Exemplo: bash limpar_logs.sh /var/log 7
#
# Este script é inofensivo para a demo — ele busca arquivos .log
# na pasta informada e lista/remove os que passaram do prazo.

# $1 = primeiro parâmetro (pasta dos logs), com valor padrão /tmp/demo_logs
PASTA="${1:-/tmp/demo_logs}"

# $2 = segundo parâmetro (dias), com valor padrão 7
DIAS="${2:-7}"

echo "=== IsyShell: Limpeza de Logs ==="
echo "Pasta alvo : $PASTA"
echo "Reter últimos: ${DIAS} dias"
echo "Data/hora: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# Cria a pasta de demo se não existir (só para a demonstração funcionar)
mkdir -p "$PASTA"

# Cria arquivos de log falsos para a demo, se a pasta estiver vazia
if [ -z "$(ls -A "$PASTA" 2>/dev/null)" ]; then
    echo "Criando arquivos de exemplo para demonstração..."
    touch -d "10 days ago" "$PASTA/antigo_01.log"
    touch -d "15 days ago" "$PASTA/antigo_02.log"
    touch -d "2 days ago"  "$PASTA/recente_01.log"
fi

# Conta quantos arquivos existem
TOTAL=$(find "$PASTA" -name "*.log" 2>/dev/null | wc -l)
echo "Total de arquivos .log encontrados: $TOTAL"

# Encontra arquivos mais antigos que DIAS
ANTIGOS=$(find "$PASTA" -name "*.log" -mtime +"$DIAS" 2>/dev/null)

if [ -z "$ANTIGOS" ]; then
    echo "Nenhum arquivo com mais de ${DIAS} dias encontrado. Nada a remover."
else
    echo ""
    echo "Arquivos para remoção (mais antigos que ${DIAS} dias):"
    echo "$ANTIGOS"
    # Descomentar a linha abaixo para realmente deletar (cuidado em produção!)
    # find "$PASTA" -name "*.log" -mtime +"$DIAS" -delete
    echo ""
    echo "MODO DEMO: listagem concluída sem deletar. Remova o comentário para ativar a deleção real."
fi

echo ""
echo "=== Limpeza concluída com sucesso! ==="
# Código de saída 0 = sucesso (convenção Unix)
exit 0
