from sqlalchemy.orm import Session
from sqlalchemy import select, func
from typing import List, Optional, Dict
from datetime import date
from fastapi import HTTPException
import models
import schemas
from utils import normalize_string
from logger import log_bid_created, log_case_awarded, log_error

def get_or_create_case(db: Session, data: schemas.CaseCreate) -> models.Case:
    stmt = select(models.Case).where(models.Case.case_number == data.case_number)
    existing = db.execute(stmt).scalar_one_or_none()
    if existing:
        return existing
    
    case_data = data.model_dump()
    # Adicionar campos normalizados
    case_data['municipality_normalized'] = normalize_string(data.municipality)
    case_data['procedure_normalized'] = normalize_string(data.procedure)
    
    obj = models.Case(**case_data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

def list_opportunities(
    db: Session,
    city: Optional[str] = None,
    procedure: Optional[str] = None,
    status: Optional[str] = "open",
    page: int = 1,
    page_size: int = 20
) -> Dict:
    stmt = select(models.Case)
    
    if status:
        stmt = stmt.where(models.Case.status == status)
    if city:
        city_norm = normalize_string(city)
        stmt = stmt.where(models.Case.municipality_normalized.like(f"%{city_norm}%"))
    if procedure:
        proc_norm = normalize_string(procedure)
        stmt = stmt.where(models.Case.procedure_normalized.like(f"%{proc_norm}%"))
    
    # Contar total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.execute(count_stmt).scalar()
    
    # Aplicar paginação
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size).order_by(models.Case.created_at.desc())
    
    items = db.execute(stmt).scalars().all()
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if total > 0 else 0
    }

def create_hospital(db: Session, data: schemas.HospitalCreate) -> models.Hospital:
    obj = models.Hospital(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

def create_bid(db: Session, data: schemas.BidCreate) -> models.Bid:
    try:
        # Verificar se o caso existe
        case = db.get(models.Case, data.case_id)
        if not case:
            raise HTTPException(status_code=404, detail="Caso não encontrado")
        
        # Verificar status do caso
        if case.status not in ["open", "in_bid"]:
            raise HTTPException(
                status_code=400,
                detail=f"Caso não está disponível para orçamentos (status: {case.status})"
            )
        
        # Verificar prazo judicial
        if case.due_date and case.due_date < date.today():
            raise HTTPException(
                status_code=400,
                detail="Prazo judicial já expirado. Não é possível enviar orçamento."
            )
        
        # Verificar se hospital já enviou orçamento
        existing_bid = db.query(models.Bid).filter(
            models.Bid.case_id == data.case_id,
            models.Bid.hospital_id == data.hospital_id
        ).first()
        
        if existing_bid:
            raise HTTPException(
                status_code=400,
                detail="Hospital já enviou orçamento para este caso"
            )
        
        # Verificar se hospital existe
        hospital = db.get(models.Hospital, data.hospital_id)
        if not hospital:
            raise HTTPException(status_code=404, detail="Hospital não encontrado")
        
        # Criar bid
        obj = models.Bid(**data.model_dump())
        db.add(obj)
        
        # Atualizar status do caso
        if case.status == "open":
            case.status = "in_bid"
        
        db.commit()
        db.refresh(obj)
        
        # Log
        log_bid_created(obj.case_id, obj.hospital_id, obj.amount)
        
        return obj
    except HTTPException:
        raise
    except Exception as e:
        log_error(e, {"case_id": data.case_id, "hospital_id": data.hospital_id})
        raise

def award_case(db: Session, case_id: int, winning_bid_id: int, payer_entity: str, award_notes: str = None) -> models.Award:
    try:
        bid = db.get(models.Bid, winning_bid_id)
        case = db.get(models.Case, case_id)
        
        if not bid:
            raise HTTPException(status_code=404, detail="Orçamento não encontrado")
        if not case:
            raise HTTPException(status_code=404, detail="Caso não encontrado")
        if bid.case_id != case_id:
            raise HTTPException(status_code=400, detail="Orçamento não pertence a este caso")
        
        # Atualizar status de todos os bids
        for b in case.bids:
            b.status = "lost"
        bid.status = "won"
        
        # Criar award
        award = models.Award(
            case_id=case_id,
            hospital_id=bid.hospital_id,
            amount=bid.amount,
            payer_entity=payer_entity,
            award_notes=award_notes
        )
        case.status = "awarded"
        
        db.add(award)
        db.commit()
        db.refresh(award)
        
        # Log
        log_case_awarded(case_id, award.hospital_id, award.amount)
        
        return award
    except HTTPException:
        raise
    except Exception as e:
        log_error(e, {"case_id": case_id, "winning_bid_id": winning_bid_id})
        raise

def get_case(db: Session, case_id: int) -> models.Case:
    return db.get(models.Case, case_id)

def get_hospital_bids(db: Session, hospital_id: int, status: Optional[str] = None) -> List[models.Bid]:
    query = db.query(models.Bid).filter(models.Bid.hospital_id == hospital_id)
    if status:
        query = query.filter(models.Bid.status == status)
    return query.order_by(models.Bid.created_at.desc()).all()

def get_case_bids(db: Session, case_id: int) -> List[models.Bid]:
    return db.query(models.Bid).filter(models.Bid.case_id == case_id).order_by(models.Bid.amount).all()

