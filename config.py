import os
from dotenv import load_dotenv

# Charger les variables du fichier .env
load_dotenv()

# Configuration de la base de données
DATABASE_URL = os.getenv("DATABASE_URL")

# Configuration des emails
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

# Clé API OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

load_dotenv()

class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

