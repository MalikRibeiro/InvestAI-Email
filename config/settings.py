import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

class Settings:
    # E-mail (Credenciais carregadas do .env)
    EMAIL_SENDER = os.getenv("EMAIL_SENDER")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
    EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")

import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

class Settings:
    # E-mail (Credenciais carregadas do .env)
    EMAIL_SENDER = os.getenv("EMAIL_SENDER")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
    EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")

    # IA (Gemini)
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

    # App
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # Google Sheets CSV Link
    SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQsiq3RTqfKGES0ntzkV_crn8BN43DleBxbpUr-UX32zD28ppyURXLaLnYIGaGmXt1Nvu3jUNsdjmiK/pub?gid=0&single=true&output=csv"
    
    # Alocação Ideal Atualizada
    TARGET_ALLOCATION = {
        "Renda Fixa": 0.35,  
        "Ações BR": 0.20,    
        "ETFs": 0.15,        
        "FIIs": 0.10,        
        "REITs": 0.07,       
        "Ações EUA": 0.07,   
        "Cripto": 0.06,
        "ETFs EUA": 0.03
    }