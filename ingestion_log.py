"""
Modelo de Log de Ingestão
==========================

Armazena histórico de execuções do robô de scraping.
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, JSON
from sqlalchemy.sql import func
from db import Base

class IngestionLog(Base):
    """
    Registro de cada execução do robô de ingestão.
    """
    __tablename__ = "ingestion_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Timestamp
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    
    # Configuração
    mode = Column(String, nullable=False)  # "mock" ou "real"
    requested_count = Column(Integer, nullable=False)  # Número solicitado
    
    # Resultado
    success = Column(Boolean, nullable=False, default=False)
    cases_created = Column(Integer, nullable=False, default=0)
    cases_found = Column(Integer, nullable=False, default=0)
    
    # Erro (se houver)
    error_message = Column(String, nullable=True)
    
    # Metadados
    meta = Column(JSON, nullable=True)  # Informações adicionais
    
    # Tipo de execução
    execution_type = Column(String, nullable=False, default="manual")  # "manual", "cron", "api"
    
    def __repr__(self):
        return f"<IngestionLog(id={self.id}, mode={self.mode}, success={self.success}, cases={self.cases_created})>"

