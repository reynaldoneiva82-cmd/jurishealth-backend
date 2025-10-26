#!/usr/bin/env python3
"""
Cron Job - Ingestão Diária de Processos do TJMG
================================================

Este script é executado diariamente pelo cron para capturar novos processos.

Configuração do cron:
# Executar todo dia às 8h da manhã
0 8 * * * cd /path/to/backend && python3 cron_daily_ingestion.py >> logs/cron.log 2>&1

Ou via crontab -e:
0 8 * * * /usr/bin/python3 /home/ubuntu/jurishealth-backend-ATUALIZADO/cron_daily_ingestion.py
"""

import sys
import os
from datetime import datetime

# Adicionar diretório do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import SessionLocal
from tasks import run_daily_ingestion
from logger import logger

def main():
    """Função principal do cron job."""
    logger.info("=" * 80)
    logger.info(f"CRON JOB INICIADO - {datetime.now()}")
    logger.info("=" * 80)
    
    db = SessionLocal()
    
    try:
        result = run_daily_ingestion(db)
        
        if result["success"]:
            logger.info(f"✅ SUCESSO: {result['casos_criados']} casos criados")
            print(f"SUCCESS: {result['casos_criados']} casos criados")
            sys.exit(0)
        else:
            logger.error(f"❌ ERRO: {result.get('error', 'Erro desconhecido')}")
            print(f"ERROR: {result.get('error')}")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❌ ERRO CRÍTICO: {e}")
        import traceback
        traceback.print_exc()
        print(f"CRITICAL ERROR: {e}")
        sys.exit(1)
        
    finally:
        db.close()
        logger.info("=" * 80)
        logger.info(f"CRON JOB FINALIZADO - {datetime.now()}")
        logger.info("=" * 80)


if __name__ == "__main__":
    main()

