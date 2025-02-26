from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os
from app.routes import api_emails_blueprint 
from config import DATABASE_URL
from app.database import init_db

def create_app():
    app = Flask(__name__)

    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", DATABASE_URL)
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Initialiser db avec l'application Flask
    init_db(app)

    # Enregistrement du blueprint une seule fois
    app.register_blueprint(api_emails_blueprint, url_prefix='/api')

    return app
