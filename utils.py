import unicodedata
from typing import Optional

def normalize_string(text: Optional[str]) -> Optional[str]:
    """
    Normaliza string removendo acentos e convertendo para minúsculas.
    Útil para buscas case-insensitive e accent-insensitive.
    """
    if not text:
        return text
    
    # Normalizar unicode (NFD = decomposição canônica)
    nfd = unicodedata.normalize('NFD', text)
    
    # Remover acentos (categoria Mn = Nonspacing Mark)
    without_accents = ''.join(char for char in nfd if unicodedata.category(char) != 'Mn')
    
    # Converter para minúsculas e remover espaços extras
    return without_accents.lower().strip()

