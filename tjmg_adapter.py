from datetime import date, timedelta
import random, hashlib

from adapter_base import CourtAdapter

PROCEDURES = [
    "Cirurgia oncológica", "Radioterapia IMRT", "Cateterismo", "Prótese de quadril",
    "Hemodiálise", "Medicação de alto custo", "Quimioterapia"
]
CITIES_MG = [
    "Belo Horizonte","Uberlândia","Contagem","Juiz de Fora","Betim","Montes Claros","Uberaba",
    "Governador Valadares","Ipatinga","Sete Lagoas","Divinópolis","Ibirité","Poços de Caldas",
    "Patos de Minas","Teófilo Otoni","Sabará"
]

class TJMGAdapterMock(CourtAdapter):
    """Adapter MOCK para desenvolvimento.

    Em produção: substituir por integração autorizada (API/convênio/consulta) com TJMG/Diários.
    """
    def __init__(self, n: int = 10):
        self.n = n

    def fetch_cases(self):
        out = []
        base_today = date.today()
        for i in range(self.n):
            proc = random.choice(PROCEDURES)
            city = random.choice(CITIES_MG)
            case_number = f"500{base_today.year}{i:04d}-{random.randint(10,99)}.2025.8.13.0000"
            patient_hash = hashlib.sha256(f"paciente_{i}".encode()).hexdigest()[:16]
            due = base_today + timedelta(days=random.randint(10, 90))
            value = round(random.uniform(5000, 80000), 2)
            out.append({
                "court": "TJMG",
                "jurisdiction": "Saúde",
                "case_number": case_number,
                "patient_hash": patient_hash,
                "procedure": proc,
                "municipality": city,
                "value_estimate": value,
                "status": "open",
                "due_date": due,
                "meta": {"stage": "transitado_em_julgado", "source": "mock_tjmg"}
            })
        return out
