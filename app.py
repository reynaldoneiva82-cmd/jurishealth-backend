from fastapi import FastAPI, Depends, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from db import Base, engine, SessionLocal
import schemas
import crud
import models
from tasks import (
    run_tjmg_ingestion_with_retry,
    get_last_ingestion_status,
    get_ingestion_history,
    get_ingestion_stats
)
from config import settings
from auth import create_access_token, get_current_hospital, get_password_hash, verify_password

# Criar tabelas
Base.metadata.create_all(bind=engine)

# Inicializar app
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description="""
    ## Plataforma G4med - API de Oportunidades Judiciais de Saúde
    
    A G4med conecta hospitais privados a processos judiciais de saúde ganhos contra entes públicos.
    
    ### Fluxo Principal:
    1. **Autenticação**: Registre-se ou faça login para obter um token JWT
    2. **Oportunidades**: Liste processos judiciais disponíveis
    3. **Orçamentos**: Envie orçamentos competitivos
    4. **Adjudicação**: Aguarde decisão e execute procedimentos
    
    ### Autenticação:
    Use o token JWT obtido no login em todas as requisições protegidas.
    
    **Header:** `Authorization: Bearer {seu_token_aqui}`
    """
)

# Rate Limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==================== ENDPOINTS PÚBLICOS ====================

@app.get("/health", tags=["Sistema"])
def health():
    """Verifica se a API está funcionando"""
    return {"status": "ok", "version": settings.API_VERSION}

@app.get("/stats/platform", tags=["Estatísticas"])
def get_platform_stats(db: Session = Depends(get_db)):
    """Estatísticas gerais da plataforma (público)"""
    total_cases = db.query(models.Case).count()
    open_cases = db.query(models.Case).filter(models.Case.status == "open").count()
    awarded_cases = db.query(models.Case).filter(models.Case.status == "awarded").count()
    total_hospitals = db.query(models.Hospital).filter(models.Hospital.is_active == True).count()
    total_bids = db.query(models.Bid).count()
    total_value = db.query(func.sum(models.Award.amount)).scalar() or 0
    
    return {
        "total_cases": total_cases,
        "open_cases": open_cases,
        "awarded_cases": awarded_cases,
        "total_hospitals": total_hospitals,
        "total_bids": total_bids,
        "total_awarded_value": float(total_value)
    }

# ==================== AUTENTICAÇÃO ====================

@app.post("/auth/register", response_model=schemas.TokenResponse, tags=["Autenticação"])
@limiter.limit("3/minute")
def register_hospital(request: Request, data: schemas.HospitalRegister, db: Session = Depends(get_db)):
    """Registrar novo hospital na plataforma"""
    # Verificar se email já existe
    existing = db.query(models.Hospital).filter(models.Hospital.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email já cadastrado")
    
    # Verificar se nome já existe
    existing_name = db.query(models.Hospital).filter(models.Hospital.name == data.name).first()
    if existing_name:
        raise HTTPException(status_code=400, detail="Nome do hospital já cadastrado")
    
    # Criar hospital
    hospital = models.Hospital(
        name=data.name,
        city=data.city,
        email=data.email,
        password_hash=get_password_hash(data.password),
        specialties=data.specialties,
        credentials=data.credentials,
        is_active=True
    )
    db.add(hospital)
    db.commit()
    db.refresh(hospital)
    
    # Gerar token
    access_token = create_access_token(data={"hospital_id": hospital.id})
    return schemas.TokenResponse(
        access_token=access_token,
        hospital_id=hospital.id,
        hospital_name=hospital.name
    )

@app.post("/auth/login", response_model=schemas.TokenResponse, tags=["Autenticação"])
@limiter.limit("5/minute")
def login_hospital(request: Request, data: schemas.HospitalLogin, db: Session = Depends(get_db)):
    """Login de hospital existente"""
    hospital = db.query(models.Hospital).filter(models.Hospital.email == data.email).first()
    if not hospital or not verify_password(data.password, hospital.password_hash):
        raise HTTPException(status_code=401, detail="Email ou senha inválidos")
    
    if not hospital.is_active:
        raise HTTPException(status_code=403, detail="Hospital inativo. Contate o suporte.")
    
    access_token = create_access_token(data={"hospital_id": hospital.id})
    return schemas.TokenResponse(
        access_token=access_token,
        hospital_id=hospital.id,
        hospital_name=hospital.name
    )

# ==================== OPORTUNIDADES ====================

@app.get("/opportunities", tags=["Oportunidades"])
def list_opportunities(
    city: Optional[str] = None,
    procedure: Optional[str] = None,
    status: Optional[str] = "open",
    page: int = Query(1, ge=1, description="Número da página"),
    page_size: int = Query(20, ge=1, le=100, description="Itens por página"),
    db: Session = Depends(get_db)
):
    """
    Lista oportunidades (processos judiciais) disponíveis.
    
    Filtros disponíveis:
    - city: Filtrar por município
    - procedure: Filtrar por tipo de procedimento
    - status: Filtrar por status (open, in_bid, awarded)
    - page: Número da página
    - page_size: Itens por página (máximo 100)
    """
    result = crud.list_opportunities(
        db,
        city=city,
        procedure=procedure,
        status=status,
        page=page,
        page_size=page_size
    )
    return result

@app.get("/cases/{case_id}", response_model=schemas.CaseOut, tags=["Oportunidades"])
def get_case(case_id: int, db: Session = Depends(get_db)):
    """Obter detalhes de um caso específico"""
    obj = crud.get_case(db, case_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Caso não encontrado")
    return obj

@app.get("/cases/{case_id}/bids", response_model=List[schemas.BidOut], tags=["Admin"])
def list_case_bids(case_id: int, db: Session = Depends(get_db)):
    """Lista todos os orçamentos de um caso (apenas para equipe G4med)"""
    case = db.get(models.Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Caso não encontrado")
    
    return crud.get_case_bids(db, case_id)

# ==================== HOSPITAIS ====================

@app.post("/hospitals", response_model=schemas.HospitalOut, tags=["Admin"])
def create_hospital(data: schemas.HospitalCreate, db: Session = Depends(get_db)):
    """Criar hospital (método legado, use /auth/register)"""
    return crud.create_hospital(db, data)

@app.get("/hospitals/me", response_model=schemas.HospitalOut, tags=["Hospitais"])
def get_current_hospital_info(current_hospital: models.Hospital = Depends(get_current_hospital)):
    """Obter informações do hospital autenticado"""
    return current_hospital

@app.get("/hospitals/{hospital_id}/stats", tags=["Hospitais"])
def get_hospital_stats(
    hospital_id: int,
    current_hospital: models.Hospital = Depends(get_current_hospital),
    db: Session = Depends(get_db)
):
    """Estatísticas do hospital (apenas próprio hospital)"""
    if hospital_id != current_hospital.id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    total_bids = db.query(models.Bid).filter(models.Bid.hospital_id == hospital_id).count()
    won_bids = db.query(models.Bid).filter(
        models.Bid.hospital_id == hospital_id,
        models.Bid.status == "won"
    ).count()
    
    total_awarded = db.query(models.Award).filter(
        models.Award.hospital_id == hospital_id
    ).count()
    
    total_revenue = db.query(func.sum(models.Award.amount)).filter(
        models.Award.hospital_id == hospital_id
    ).scalar() or 0
    
    return {
        "hospital_id": hospital_id,
        "hospital_name": current_hospital.name,
        "total_bids": total_bids,
        "won_bids": won_bids,
        "total_awarded": total_awarded,
        "total_revenue": float(total_revenue),
        "win_rate": round((won_bids / total_bids * 100), 2) if total_bids > 0 else 0
    }

# ==================== ORÇAMENTOS ====================

@app.post("/bids", response_model=schemas.BidOut, tags=["Orçamentos"])
@limiter.limit("10/minute")
def create_bid(
    request: Request,
    data: schemas.BidCreate,
    current_hospital: models.Hospital = Depends(get_current_hospital),
    db: Session = Depends(get_db)
):
    """
    Enviar orçamento para um caso.
    
    Requer autenticação. O hospital só pode criar orçamentos em seu próprio nome.
    """
    # Garantir que o hospital só pode criar bids em seu próprio nome
    if data.hospital_id != current_hospital.id:
        raise HTTPException(
            status_code=403,
            detail="Você só pode criar orçamentos em seu próprio nome"
        )
    
    return crud.create_bid(db, data)

@app.get("/hospitals/{hospital_id}/bids", response_model=List[schemas.BidOut], tags=["Orçamentos"])
def list_hospital_bids(
    hospital_id: int,
    status: Optional[str] = None,
    current_hospital: models.Hospital = Depends(get_current_hospital),
    db: Session = Depends(get_db)
):
    """Lista todos os orçamentos de um hospital (apenas próprio hospital)"""
    if hospital_id != current_hospital.id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    return crud.get_hospital_bids(db, hospital_id, status)

# ==================== ADJUDICAÇÃO ====================

@app.post("/cases/{case_id}/award", response_model=schemas.AwardOut, tags=["Admin"])
def award_case(case_id: int, data: schemas.AwardCreate, db: Session = Depends(get_db)):
    """Adjudicar caso ao hospital vencedor (apenas equipe G4med)"""
    return crud.award_case(db, case_id, data.winning_bid_id, data.payer_entity, data.award_notes)

# ==================== INGESTÃO (ADMIN) ====================

@app.post("/ingest/tjmg/run", tags=["Admin"])
def ingest_tjmg(
    n: int = 10,
    use_real: bool = False,
    max_attempts: int = 3,
    db: Session = Depends(get_db)
):
    """
    Executar ingestão de processos do TJMG com retry automático.
    
    Args:
        n: Número de processos a capturar (padrão: 10)
        use_real: Se True, usa scraping real do PJe. Se False, usa dados mock (padrão: False)
        max_attempts: Número máximo de tentativas em caso de erro (padrão: 3)
    
    Returns:
        Resultado da ingestão com estatísticas
    
    Exemplo:
        POST /ingest/tjmg/run?n=30&use_real=true&max_attempts=5
    
    O robô tentará executar até conseguir sucesso ou atingir o número máximo de tentativas.
    Em caso de erro, aguarda com backoff exponencial antes de tentar novamente.
    """
    result = run_tjmg_ingestion_with_retry(
        db,
        n=n,
        use_real=use_real,
        execution_type="api",
        max_attempts=max_attempts
    )
    return result

@app.get("/ingest/status", tags=["Admin"])
def get_ingestion_status(db: Session = Depends(get_db)):
    """
    Consultar status da última execução do robô.
    
    Retorna informações detalhadas sobre a última execução:
    - Status (sucesso/falha)
    - Horário de início e fim
    - Duração
    - Número de casos encontrados e criados
    - Número de tentativas
    - Mensagem de erro (se houver)
    
    Exemplo:
        GET /ingest/status
    """
    return get_last_ingestion_status(db)

@app.get("/ingest/history", tags=["Admin"])
def get_ingestion_history_endpoint(
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    Consultar histórico de execuções do robô.
    
    Args:
        limit: Número máximo de registros a retornar (padrão: 10)
    
    Returns:
        Lista com as últimas execuções do robô
    
    Exemplo:
        GET /ingest/history?limit=20
    """
    return {
        "history": get_ingestion_history(db, limit=limit),
        "total_returned": min(limit, len(get_ingestion_history(db, limit=limit)))
    }

@app.get("/ingest/stats", tags=["Admin"])
def get_ingestion_stats_endpoint(db: Session = Depends(get_db)):
    """
    Consultar estatísticas gerais de ingestão.
    
    Retorna:
    - Total de execuções
    - Execuções bem-sucedidas
    - Execuções com falha
    - Taxa de sucesso
    - Total de casos criados
    - Data da última execução bem-sucedida
    
    Exemplo:
        GET /ingest/stats
    """
    return get_ingestion_stats(db)

