"""
Tasks com Sistema de Retry Automático
======================================

Sistema robusto de ingestão com retry automático até conseguir executar com sucesso.
"""

from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from schemas import CaseCreate
from tjmg_adapter import TJMGAdapterMock
from tjmg_adapter_real import TJMGAdapterReal
from nlp import normalize_case_fields
import crud
import models
from logger import logger
import os
import time
import traceback


def create_ingestion_log(
    db: Session,
    mode: str,
    requested_count: int,
    execution_type: str = "manual",
    max_attempts: int = 3
) -> models.IngestionLog:
    """
    Cria registro inicial de log de ingestão.
    """
    log = models.IngestionLog(
        mode=mode,
        requested_count=requested_count,
        execution_type=execution_type,
        attempt_number=1,
        max_attempts=max_attempts,
        success=False
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def update_ingestion_log(
    db: Session,
    log: models.IngestionLog,
    success: bool,
    cases_found: int = 0,
    cases_created: int = 0,
    error_message: str = None,
    error_traceback: str = None,
    meta: dict = None
):
    """
    Atualiza registro de log com resultado da execução.
    """
    log.finished_at = datetime.now()
    log.duration_seconds = (log.finished_at - log.started_at).total_seconds()
    log.success = success
    log.cases_found = cases_found
    log.cases_created = cases_created
    log.error_message = error_message
    log.error_traceback = error_traceback
    
    if meta:
        log.meta = meta
    
    db.commit()
    db.refresh(log)


def run_tjmg_ingestion_with_retry(
    db: Session,
    n: int = 10,
    use_real: bool = False,
    execution_type: str = "manual",
    max_attempts: int = 3
) -> dict:
    """
    Executa ingestão com sistema de retry automático.
    
    Tenta executar até conseguir sucesso ou atingir número máximo de tentativas.
    
    Args:
        db: Sessão do banco de dados
        n: Número de processos a capturar
        use_real: Se True, usa adapter real (Selenium)
        execution_type: Tipo de execução ("manual", "cron", "api")
        max_attempts: Número máximo de tentativas
    
    Returns:
        Dicionário com resultado final
    """
    mode = "real" if use_real else "mock"
    
    logger.info("=" * 80)
    logger.info(f"INGESTÃO INICIADA: mode={mode}, n={n}, max_attempts={max_attempts}")
    logger.info("=" * 80)
    
    # Criar log inicial
    log = create_ingestion_log(db, mode, n, execution_type, max_attempts)
    
    for attempt in range(1, max_attempts + 1):
        log.attempt_number = attempt
        db.commit()
        
        logger.info(f"Tentativa {attempt}/{max_attempts}")
        
        try:
            # Executar ingestão
            result = _execute_ingestion(db, n, use_real)
            
            # Verificar se teve sucesso
            if result["success"]:
                logger.info(f"✅ SUCESSO na tentativa {attempt}!")
                
                # Atualizar log com sucesso
                update_ingestion_log(
                    db, log,
                    success=True,
                    cases_found=result["cases_found"],
                    cases_created=result["cases_created"],
                    meta=result.get("meta")
                )
                
                return {
                    "success": True,
                    "log_id": log.id,
                    "attempt": attempt,
                    "cases_created": result["cases_created"],
                    "cases_found": result["cases_found"],
                    "duration_seconds": log.duration_seconds
                }
            else:
                # Falha mas sem exceção
                raise Exception(result.get("error", "Falha desconhecida"))
                
        except Exception as e:
            error_msg = str(e)
            error_trace = traceback.format_exc()
            
            logger.error(f"❌ ERRO na tentativa {attempt}: {error_msg}")
            
            # Se não é a última tentativa, aguardar antes de tentar novamente
            if attempt < max_attempts:
                # Backoff exponencial: 10s, 30s, 60s
                wait_time = min(10 * (2 ** (attempt - 1)), 60)
                logger.info(f"Aguardando {wait_time}s antes da próxima tentativa...")
                time.sleep(wait_time)
            else:
                # Última tentativa falhou
                logger.error(f"❌ FALHA FINAL após {max_attempts} tentativas")
                
                # Atualizar log com falha
                update_ingestion_log(
                    db, log,
                    success=False,
                    error_message=error_msg,
                    error_traceback=error_trace
                )
                
                return {
                    "success": False,
                    "log_id": log.id,
                    "attempt": attempt,
                    "error": error_msg,
                    "max_attempts_reached": True
                }
    
    # Não deveria chegar aqui
    return {
        "success": False,
        "error": "Erro inesperado no sistema de retry"
    }


def _execute_ingestion(db: Session, n: int, use_real: bool) -> dict:
    """
    Executa ingestão (função interna).
    
    Returns:
        Dicionário com resultado
    """
    try:
        if use_real:
            logger.info("Usando TJMGAdapterReal (scraping real)")
            adapter = TJMGAdapterReal(headless=True, max_processos=n)
        else:
            logger.info("Usando TJMGAdapterMock (dados fictícios)")
            adapter = TJMGAdapterMock(n=n)
        
        # Buscar casos
        cases = adapter.fetch_cases()
        cases_found = len(cases)
        logger.info(f"Capturados {cases_found} processos")
        
        # Salvar no banco
        count = 0
        for c in cases:
            try:
                c_norm = normalize_case_fields(c)
                obj = crud.get_or_create_case(db, CaseCreate(**c_norm))
                if obj:
                    count += 1
                    logger.info(f"Caso criado: {c_norm.get('case_number')}")
            except Exception as e:
                logger.error(f"Erro ao criar caso: {e}")
                continue
        
        logger.info(f"Ingestão concluída: {count} casos criados de {cases_found} encontrados")
        
        return {
            "success": True,
            "cases_found": cases_found,
            "cases_created": count,
            "meta": {
                "adapter": "real" if use_real else "mock",
                "requested": n
            }
        }
        
    except Exception as e:
        logger.error(f"Erro na ingestão: {e}")
        return {
            "success": False,
            "error": str(e),
            "cases_found": 0,
            "cases_created": 0
        }


def run_daily_ingestion(db: Session) -> dict:
    """
    Executa ingestão diária automática com retry.
    
    Esta função é chamada pelo cron job.
    """
    logger.info("=" * 80)
    logger.info("INGESTÃO DIÁRIA AUTOMÁTICA INICIADA")
    logger.info("=" * 80)
    
    # Configuração
    use_real = os.getenv("USE_REAL_ADAPTER", "false").lower() == "true"
    max_processos = int(os.getenv("MAX_PROCESSOS_DIARIOS", "50"))
    max_attempts = int(os.getenv("MAX_RETRY_ATTEMPTS", "5"))  # 5 tentativas para cron
    
    logger.info(f"Configuração: use_real={use_real}, max_processos={max_processos}, max_attempts={max_attempts}")
    
    # Executar com retry
    result = run_tjmg_ingestion_with_retry(
        db,
        n=max_processos,
        use_real=use_real,
        execution_type="cron",
        max_attempts=max_attempts
    )
    
    if result["success"]:
        logger.info(f"✅ Ingestão diária concluída: {result['cases_created']} casos criados")
    else:
        logger.error(f"❌ Ingestão diária falhou: {result.get('error')}")
    
    return result


def get_last_ingestion_status(db: Session) -> dict:
    """
    Retorna status da última execução do robô.
    
    Returns:
        Dicionário com informações da última execução
    """
    last_log = db.query(models.IngestionLog).order_by(
        models.IngestionLog.started_at.desc()
    ).first()
    
    if not last_log:
        return {
            "status": "never_executed",
            "message": "Robô nunca foi executado"
        }
    
    return {
        "status": "success" if last_log.success else "failed",
        "log_id": last_log.id,
        "started_at": last_log.started_at.isoformat(),
        "finished_at": last_log.finished_at.isoformat() if last_log.finished_at else None,
        "duration_seconds": last_log.duration_seconds,
        "mode": last_log.mode,
        "execution_type": last_log.execution_type,
        "cases_found": last_log.cases_found,
        "cases_created": last_log.cases_created,
        "attempt_number": last_log.attempt_number,
        "max_attempts": last_log.max_attempts,
        "error_message": last_log.error_message,
        "meta": last_log.meta
    }


def get_ingestion_history(db: Session, limit: int = 10) -> list:
    """
    Retorna histórico de execuções.
    
    Args:
        limit: Número máximo de registros
    
    Returns:
        Lista de execuções
    """
    logs = db.query(models.IngestionLog).order_by(
        models.IngestionLog.started_at.desc()
    ).limit(limit).all()
    
    return [
        {
            "log_id": log.id,
            "started_at": log.started_at.isoformat(),
            "finished_at": log.finished_at.isoformat() if log.finished_at else None,
            "duration_seconds": log.duration_seconds,
            "mode": log.mode,
            "execution_type": log.execution_type,
            "success": log.success,
            "cases_found": log.cases_found,
            "cases_created": log.cases_created,
            "attempt_number": log.attempt_number,
            "error_message": log.error_message
        }
        for log in logs
    ]


def get_ingestion_stats(db: Session) -> dict:
    """
    Retorna estatísticas gerais de ingestão.
    
    Returns:
        Dicionário com estatísticas
    """
    total_executions = db.query(models.IngestionLog).count()
    successful_executions = db.query(models.IngestionLog).filter(
        models.IngestionLog.success == True
    ).count()
    
    total_cases_created = db.query(
        models.IngestionLog.cases_created
    ).filter(
        models.IngestionLog.success == True
    ).all()
    
    total_cases = sum([log.cases_created for log in total_cases_created])
    
    # Última execução bem-sucedida
    last_success = db.query(models.IngestionLog).filter(
        models.IngestionLog.success == True
    ).order_by(
        models.IngestionLog.started_at.desc()
    ).first()
    
    return {
        "total_executions": total_executions,
        "successful_executions": successful_executions,
        "failed_executions": total_executions - successful_executions,
        "success_rate": round((successful_executions / total_executions * 100), 2) if total_executions > 0 else 0,
        "total_cases_created": total_cases,
        "last_successful_execution": last_success.started_at.isoformat() if last_success else None
    }

