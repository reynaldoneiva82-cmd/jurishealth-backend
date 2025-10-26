import logging
import json
from datetime import datetime
from typing import Any, Dict

class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Adicionar campos extras
        if hasattr(record, 'extra_data'):
            log_data.update(record.extra_data)
        
        return json.dumps(log_data, ensure_ascii=False)

def setup_logging():
    logger = logging.getLogger("g4med")
    logger.setLevel(logging.INFO)
    
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)
    
    return logger

logger = setup_logging()

def log_bid_created(case_id: int, hospital_id: int, amount: float):
    extra = logging.LogRecord(
        name="g4med", level=logging.INFO, pathname="", lineno=0,
        msg="Orçamento criado", args=(), exc_info=None
    )
    extra.extra_data = {
        "event": "bid_created",
        "case_id": case_id,
        "hospital_id": hospital_id,
        "amount": amount
    }
    logger.handle(extra)

def log_case_awarded(case_id: int, hospital_id: int, amount: float):
    extra = logging.LogRecord(
        name="g4med", level=logging.INFO, pathname="", lineno=0,
        msg="Caso adjudicado", args=(), exc_info=None
    )
    extra.extra_data = {
        "event": "case_awarded",
        "case_id": case_id,
        "hospital_id": hospital_id,
        "amount": amount
    }
    logger.handle(extra)

def log_error(error: Exception, context: Dict[str, Any] = None):
    logger.error(
        f"Erro: {str(error)}",
        extra={
            "event": "error",
            "error_type": type(error).__name__,
            "context": context or {}
        },
        exc_info=True
    )

