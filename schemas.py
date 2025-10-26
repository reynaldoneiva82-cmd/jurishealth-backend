from pydantic import BaseModel, Field, field_validator, EmailStr
from typing import Optional, List, Any, Generic, TypeVar
from datetime import date, datetime

# Schemas de Case
class CaseCreate(BaseModel):
    court: str = "TJMG"
    jurisdiction: Optional[str] = None
    case_number: str
    patient_hash: str
    procedure: str
    municipality: str
    value_estimate: Optional[float] = None
    status: str = "open"
    due_date: Optional[date] = None
    meta: Optional[dict] = None
    
    @field_validator('due_date')
    def validate_due_date(cls, v):
        if v and v < date.today():
            raise ValueError('Prazo judicial não pode ser no passado')
        return v

class CaseOut(BaseModel):
    id: int
    court: str
    jurisdiction: Optional[str]
    case_number: str
    patient_hash: str
    procedure: str
    municipality: str
    value_estimate: Optional[float]
    status: str
    due_date: Optional[date]
    meta: Optional[dict]
    created_at: datetime
    
    class Config:
        from_attributes = True

# Schemas de Hospital
class HospitalCreate(BaseModel):
    name: str
    city: str
    specialties: List[str] = Field(default_factory=list)
    credentials: List[str] = Field(default_factory=list)

class HospitalRegister(BaseModel):
    name: str
    city: str
    email: EmailStr
    password: str = Field(min_length=6)
    specialties: List[str] = Field(default_factory=list)
    credentials: List[str] = Field(default_factory=list)

class HospitalLogin(BaseModel):
    email: EmailStr
    password: str

class HospitalOut(BaseModel):
    id: int
    name: str
    city: str
    email: Optional[str]
    is_active: bool
    specialties: List[str]
    credentials: List[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    hospital_id: int
    hospital_name: str

# Schemas de Bid
class BidCreate(BaseModel):
    case_id: int
    hospital_id: int
    amount: float = Field(gt=0, description="Valor deve ser maior que zero")
    notes: Optional[str] = Field(None, max_length=1000)
    
    @field_validator('amount')
    def validate_amount(cls, v):
        if v > 1_000_000:
            raise ValueError('Valor do orçamento muito alto. Contate o suporte.')
        if v < 100:
            raise ValueError('Valor do orçamento muito baixo.')
        return v

class BidOut(BaseModel):
    id: int
    case_id: int
    hospital_id: int
    amount: float
    notes: Optional[str]
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True

# Schemas de Award
class AwardCreate(BaseModel):
    winning_bid_id: int
    payer_entity: str
    award_notes: Optional[str] = None

class AwardOut(BaseModel):
    id: int
    case_id: int
    hospital_id: int
    amount: float
    payer_entity: str
    award_notes: Optional[str]
    awarded_at: datetime
    
    class Config:
        from_attributes = True

# Schema de Paginação
T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int

