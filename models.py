from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, JSON, UniqueConstraint, Boolean, Index, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from db import Base

class Case(Base):
    __tablename__ = "cases"
    id = Column(Integer, primary_key=True, index=True)
    court = Column(String, index=True)
    jurisdiction = Column(String, index=True)
    case_number = Column(String, unique=True, index=True)
    patient_hash = Column(String, index=True)
    procedure = Column(String, index=True)
    procedure_normalized = Column(String, index=True)  # NOVO
    municipality = Column(String, index=True)
    municipality_normalized = Column(String, index=True)  # NOVO
    value_estimate = Column(Float, nullable=True)
    status = Column(String, index=True, default="open")
    due_date = Column(Date, nullable=True)
    meta = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    bids = relationship("Bid", back_populates="case", cascade="all, delete-orphan")
    award = relationship("Award", back_populates="case", uselist=False, cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('ix_case_status_municipality', 'status', 'municipality_normalized'),
        Index('ix_case_status_procedure', 'status', 'procedure_normalized'),
        Index('ix_case_due_date_status', 'due_date', 'status'),
    )

class Hospital(Base):
    __tablename__ = "hospitals"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    city = Column(String, index=True)
    email = Column(String, unique=True, index=True, nullable=True)  # NOVO
    password_hash = Column(String, nullable=True)  # NOVO
    is_active = Column(Boolean, default=True)  # NOVO
    specialties = Column(JSON, default=list)
    credentials = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)

    bids = relationship("Bid", back_populates="hospital", cascade="all, delete-orphan")

class Bid(Base):
    __tablename__ = "bids"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), index=True)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), index=True)
    amount = Column(Float)
    notes = Column(String, nullable=True)
    status = Column(String, index=True, default="submitted")
    created_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("Case", back_populates="bids")
    hospital = relationship("Hospital", back_populates="bids")

    __table_args__ = (
        UniqueConstraint("case_id", "hospital_id", name="uq_bid_case_hospital"),
        Index('ix_bid_hospital_status', 'hospital_id', 'status'),
        Index('ix_bid_case_created', 'case_id', 'created_at'),
    )

class Award(Base):
    __tablename__ = "awards"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), unique=True, index=True)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), index=True)
    amount = Column(Float)
    payer_entity = Column(String)
    award_notes = Column(String, nullable=True)
    awarded_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("Case", back_populates="award")

class IngestionLog(Base):
    """Registro de execuções do robô de ingestão"""
    __tablename__ = "ingestion_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Timestamp
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Float, nullable=True)
    
    # Configuração
    mode = Column(String, nullable=False, index=True)  # "mock" ou "real"
    requested_count = Column(Integer, nullable=False)
    
    # Resultado
    success = Column(Boolean, nullable=False, default=False, index=True)
    cases_found = Column(Integer, nullable=False, default=0)
    cases_created = Column(Integer, nullable=False, default=0)
    
    # Retry
    attempt_number = Column(Integer, nullable=False, default=1)
    max_attempts = Column(Integer, nullable=False, default=3)
    
    # Erro (se houver)
    error_message = Column(Text, nullable=True)
    error_traceback = Column(Text, nullable=True)
    
    # Metadados
    meta = Column(JSON, nullable=True)
    
    # Tipo de execução
    execution_type = Column(String, nullable=False, default="manual", index=True)  # "manual", "cron", "api"
    
    __table_args__ = (
        Index('ix_ingestion_log_started_success', 'started_at', 'success'),
        Index('ix_ingestion_log_execution_type', 'execution_type', 'started_at'),
    )

