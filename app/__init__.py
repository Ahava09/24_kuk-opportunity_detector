from flask import Flask
import os
from app.routes import api_emails_blueprint  # Importation du blueprint
from app.database import db  # Si tu utilises une base de données

def create_app():
    app = Flask(__name__)
    # Configuration de la base de données ou autres configurations
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///emails.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    
    # Enregistrement du blueprint une seule fois
    app.register_blueprint(api_emails_blueprint, url_prefix='/api')
    
    return app
