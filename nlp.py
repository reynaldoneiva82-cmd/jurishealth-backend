# Regras simples para normalizar campos (sem deps pesadas).
from typing import Dict

def normalize_case_fields(data: Dict) -> Dict:
    data = dict(data)
    if 'municipality' in data and isinstance(data['municipality'], str):
        data['municipality'] = data['municipality'].strip().title()
    if 'procedure' in data and isinstance(data['procedure'], str):
        data['procedure'] = data['procedure'].strip().capitalize()
    return data
