from flask import  request, jsonify
from app.database import db
from sqlalchemy import Column, Integer, String, Text, Boolean

class ResPartner(db.Model):
    __tablename__ = 'res_partner'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('res_company.id'), nullable=True)
    email = db.Column(db.String(255), unique=True)
    phone = db.Column(db.String(50))
    is_company = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "company_id": self.company_id,
            "email": self.email,
            "phone": self.phone,
            "is_company": self.is_company,
            "created_at": self.created_at
        }
