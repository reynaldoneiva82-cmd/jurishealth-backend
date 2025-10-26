"""
TJMG Adapter Real - Captura de Processos Judiciais de Saúde
=============================================================

Este módulo substitui o mock e faz scraping REAL do PJe do TJMG.

Estratégia validada:
- Buscar por "Secretaria de Saúde" (não "Estado de Minas Gerais")
- Filtrar processos com movimentações recentes
- Identificar sentenças favoráveis
- Extrair tipo de procedimento
- Classificar urgência
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import hashlib

from adapter_base import CourtAdapter
from logger import logger

# Configurações
PJE_URL = "https://pje-consulta-publica.tjmg.jus.br/"

# Termos para buscar (réus em processos de saúde)
TERMOS_BUSCA = [
    "Secretaria de Saúde",
    "Secretaria Municipal de Saúde",
    "Secretaria Estadual de Saúde",
]

# Palavras-chave que indicam sentença favorável
PALAVRAS_SENTENCA_FAVORAVEL = [
    "concedo", "defiro", "determino", "obrigação de fazer",
    "fornecimento", "procedente", "acolho", "julgo procedente",
    "condeno", "deverá fornecer", "deverá realizar"
]

# Tipos de procedimentos
TIPOS_PROCEDIMENTOS = {
    "cirurgia": ["cirurgia", "cirúrgico", "procedimento cirúrgico", "operação"],
    "medicamento": ["medicamento", "remédio", "fármaco", "fornecimento de medicamento"],
    "internacao": ["internação", "internacao", "leito", "vaga hospitalar"],
    "uti": ["uti", "unidade de terapia intensiva", "cti"],
    "quimioterapia": ["quimio", "quimioterapia", "oncologia", "câncer", "cancer"],
    "radioterapia": ["radio", "radioterapia"],
    "exame": ["exame", "diagnóstico", "ressonância", "tomografia"],
    "tratamento": ["tratamento", "terapia", "sessões"],
}

# Valores estimados por tipo (em R$)
VALORES_ESTIMADOS = {
    "cirurgia": (20000, 80000),
    "medicamento": (5000, 30000),
    "internacao": (10000, 50000),
    "uti": (30000, 100000),
    "quimioterapia": (15000, 60000),
    "radioterapia": (10000, 40000),
    "exame": (1000, 5000),
    "tratamento": (5000, 25000),
}


class TJMGAdapterReal(CourtAdapter):
    """
    Adapter REAL para captura de processos do TJMG.
    
    Usa Selenium para fazer scraping do PJe.
    """
    
    def __init__(self, headless: bool = True, max_processos: int = 30):
        """
        Args:
            headless: Executar navegador em modo headless
            max_processos: Número máximo de processos a capturar
        """
        self.headless = headless
        self.max_processos = max_processos
        self.driver = None
    
    def _init_driver(self):
        """Inicializa o navegador Chrome."""
        if self.driver:
            return
        
        logger.info("Inicializando navegador Chrome...")
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument("--headless")
        
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            logger.info("Navegador inicializado com sucesso")
        except Exception as e:
            logger.error(f"Erro ao inicializar navegador: {e}")
            raise
    
    def _close_driver(self):
        """Fecha o navegador."""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Navegador fechado")
            except:
                pass
            self.driver = None
    
    def _buscar_processos_pje(self, termo_busca: str) -> List[Dict]:
        """
        Busca processos no PJe por termo.
        
        Args:
            termo_busca: Termo para buscar (ex: "Secretaria de Saúde")
        
        Returns:
            Lista de processos encontrados
        """
        logger.info(f"Buscando processos: {termo_busca}")
        
        try:
            self.driver.get(PJE_URL)
            wait = WebDriverWait(self.driver, 10)
            
            # Preencher campo "Nome da Parte"
            campo_nome = wait.until(
                EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Nome da Parte' or contains(@id, 'nome')]"))
            )
            campo_nome.clear()
            campo_nome.send_keys(termo_busca)
            
            # Clicar em Pesquisar
            btn_pesquisar = self.driver.find_element(By.XPATH, "//button[contains(text(), 'PESQUISAR') or contains(@id, 'pesquisar')]")
            btn_pesquisar.click()
            
            time.sleep(5)  # Aguardar carregamento
            
            # Extrair processos
            processos = []
            links_processos = self.driver.find_elements(By.XPATH, "//a[contains(@href, 'DetalheProcessoConsultaPublica')]")
            
            logger.info(f"Encontrados {len(links_processos)} processos")
            
            for link in links_processos[:self.max_processos]:
                texto_processo = link.text
                url_processo = link.get_attribute("href")
                
                # Extrair número do processo
                match_numero = re.search(r'(\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})', texto_processo)
                numero_processo = match_numero.group(1) if match_numero else None
                
                if not numero_processo:
                    continue
                
                # Extrair assunto
                assunto = texto_processo.split(" - ")[-1] if " - " in texto_processo else "N/A"
                
                processo = {
                    "numero": numero_processo,
                    "assunto": assunto,
                    "texto_completo": texto_processo,
                    "url": url_processo,
                    "termo_busca": termo_busca
                }
                
                processos.append(processo)
            
            return processos
            
        except Exception as e:
            logger.error(f"Erro na busca: {e}")
            return []
    
    def _classificar_tipo_procedimento(self, texto: str) -> tuple:
        """
        Classifica o tipo de procedimento baseado no texto.
        
        Returns:
            (tipo, valor_estimado)
        """
        texto_lower = texto.lower()
        
        for tipo, palavras in TIPOS_PROCEDIMENTOS.items():
            for palavra in palavras:
                if palavra in texto_lower:
                    # Gerar valor estimado
                    min_val, max_val = VALORES_ESTIMADOS.get(tipo, (5000, 30000))
                    valor = (min_val + max_val) / 2
                    return tipo, valor
        
        # Padrão se não identificar
        return "tratamento", 15000.0
    
    def _identificar_sentenca_favoravel(self, texto: str) -> bool:
        """
        Identifica se há sentença favorável no texto.
        """
        texto_lower = texto.lower()
        return any(palavra in texto_lower for palavra in PALAVRAS_SENTENCA_FAVORAVEL)
    
    def _extrair_municipio(self, texto: str) -> str:
        """
        Extrai município do texto do processo.
        """
        # Tentar extrair da comarca
        match = re.search(r'Comarca[:\s]+([A-Za-zÀ-ÿ\s]+)', texto, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        # Padrão
        return "Belo Horizonte"
    
    def _gerar_patient_hash(self, numero_processo: str) -> str:
        """
        Gera hash anônimo do paciente baseado no número do processo.
        """
        return hashlib.sha256(numero_processo.encode()).hexdigest()[:16]
    
    def fetch_cases(self) -> List[Dict]:
        """
        Busca processos judiciais de saúde no TJMG.
        
        Returns:
            Lista de casos no formato esperado pelo sistema
        """
        logger.info("Iniciando captura de processos do TJMG...")
        
        try:
            self._init_driver()
            
            todos_processos = []
            
            # Buscar por cada termo
            for termo in TERMOS_BUSCA[:1]:  # Começar com 1 termo
                processos = self._buscar_processos_pje(termo)
                todos_processos.extend(processos)
                
                if len(todos_processos) >= self.max_processos:
                    break
            
            logger.info(f"Total de processos capturados: {len(todos_processos)}")
            
            # Converter para formato do sistema
            casos = []
            for proc in todos_processos:
                # Classificar tipo de procedimento
                tipo, valor = self._classificar_tipo_procedimento(
                    proc["assunto"] + " " + proc["texto_completo"]
                )
                
                # Verificar sentença favorável
                sentenca_favoravel = self._identificar_sentenca_favoravel(
                    proc["texto_completo"]
                )
                
                # Apenas processos com sentença favorável
                if not sentenca_favoravel:
                    continue
                
                # Extrair município
                municipio = self._extrair_municipio(proc["texto_completo"])
                
                # Gerar hash do paciente
                patient_hash = self._gerar_patient_hash(proc["numero"])
                
                # Calcular prazo (30 dias a partir de hoje)
                due_date = datetime.now().date() + timedelta(days=30)
                
                caso = {
                    "court": "TJMG",
                    "jurisdiction": "Saúde",
                    "case_number": proc["numero"],
                    "patient_hash": patient_hash,
                    "procedure": tipo.capitalize(),
                    "municipality": municipio,
                    "value_estimate": valor,
                    "status": "open",
                    "due_date": due_date,
                    "meta": {
                        "assunto": proc["assunto"],
                        "url": proc["url"],
                        "termo_busca": proc["termo_busca"],
                        "source": "pje_tjmg_real",
                        "captura_data": datetime.now().isoformat()
                    }
                }
                
                casos.append(caso)
            
            logger.info(f"Total de casos válidos (com sentença favorável): {len(casos)}")
            return casos
            
        except Exception as e:
            logger.error(f"Erro na captura de processos: {e}")
            import traceback
            traceback.print_exc()
            return []
        
        finally:
            self._close_driver()

