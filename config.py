import os
from dotenv import load_dotenv
from datetime import timedelta
# Charger les variables du fichier .env
load_dotenv()

# Configuration de la base de données
DATABASE_URL = os.getenv("DATABASE_URL")

# Configuration des emails
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

# Clé API OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("assistant_id")
assistant_id_email = os.getenv("assistant_id_email")

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24) 

DATA_STORAGE_PATH =  os.getenv("DATA_STORAGE_PATH")
DIRECTORY_LOGO_COMPANY = os.getenv("DIRECTORY_LOGO_COMPANY")

GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL")
MAKE_WEBHOOK_URL = os.getenv("MAKE_WEBHOOK_URL")
load_dotenv()

class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

