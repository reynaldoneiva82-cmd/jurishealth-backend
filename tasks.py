from sqlalchemy.orm import Session
from .schemas import CaseCreate
from .ingest.tjmg_adapter import TJMGAdapterMock
from .ingest.nlp import normalize_case_fields
from . import crud

def run_tjmg_ingestion(db: Session, n: int = 10) -> int:
    adapter = TJMGAdapterMock(n=n)
    cases = adapter.fetch_cases()
    count = 0
    for c in cases:
        c_norm = normalize_case_fields(c)
        obj = crud.get_or_create_case(db, CaseCreate(**c_norm))
        if obj:
            count += 1
    return count
