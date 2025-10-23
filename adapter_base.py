from typing import Iterable, Dict, Any

class CourtAdapter:
    """Contrato base para adaptadores de consulta a tribunais/diários/etc."""
    def fetch_cases(self) -> Iterable[Dict[str, Any]]:
        """Retorna dicionários com campos mínimos: case_number, procedure, municipality, value_estimate, due_date, meta."""
        raise NotImplementedError
