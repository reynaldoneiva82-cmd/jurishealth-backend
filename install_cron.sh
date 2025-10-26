#!/bin/bash
#
# Script de Instalação do Cron Job
# =================================
#
# Este script configura o cron job para execução diária automática.
#
# Uso:
#   chmod +x install_cron.sh
#   ./install_cron.sh
#

echo "========================================"
echo "INSTALAÇÃO DO CRON JOB - JURISHEALTH"
echo "========================================"
echo ""

# Obter diretório atual
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo "Diretório do projeto: $SCRIPT_DIR"

# Tornar script Python executável
chmod +x "$SCRIPT_DIR/cron_daily_ingestion.py"
echo "✓ Script Python tornado executável"

# Criar diretório de logs
mkdir -p "$SCRIPT_DIR/logs"
echo "✓ Diretório de logs criado"

# Criar entrada do cron
CRON_ENTRY="0 8 * * * cd $SCRIPT_DIR && /usr/bin/python3 cron_daily_ingestion.py >> logs/cron.log 2>&1"

# Verificar se entrada já existe
if crontab -l 2>/dev/null | grep -q "cron_daily_ingestion.py"; then
    echo "⚠ Cron job já existe. Removendo entrada antiga..."
    crontab -l 2>/dev/null | grep -v "cron_daily_ingestion.py" | crontab -
fi

# Adicionar nova entrada
(crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -
echo "✓ Cron job instalado"

# Mostrar crontab atual
echo ""
echo "Crontab atual:"
echo "----------------------------------------"
crontab -l
echo "----------------------------------------"
echo ""

echo "✅ INSTALAÇÃO CONCLUÍDA!"
echo ""
echo "O script será executado:"
echo "  - Todo dia às 8h da manhã"
echo "  - Logs salvos em: $SCRIPT_DIR/logs/cron.log"
echo ""
echo "Para verificar logs:"
echo "  tail -f $SCRIPT_DIR/logs/cron.log"
echo ""
echo "Para remover o cron job:"
echo "  crontab -e"
echo "  (remover a linha com cron_daily_ingestion.py)"
echo ""

