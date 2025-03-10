import os
import openai  
from config import OPENAI_API_KEY
from sqlalchemy import Column, Integer, String, Text, Boolean
from datetime import datetime
from app.database import db

openai.api_key = OPENAI_API_KEY

class EmailsPartner(db.Model):
    __tablename__ = "emails_partner"

    id = Column(Integer, primary_key=True, autoincrement=True)
    partner_id = db.Column(db.Integer, db.ForeignKey('res_partner.id'), nullable=True)
    emails_id = db.Column(db.Integer, db.ForeignKey('emails.id'), nullable=True)

    def __init__(self, partner_id, emails_id):
        self.partner_id = partner_id
        self.emails_id = emails_id

    
    def save(self):
        try:
            db.session.add(self)
            db.session.commit()
            db.session.refresh(self)  # Recharge l'objet avec les nouvelles valeurs
            return self
        except Exception as e:
            db.session.rollback()
            raise e