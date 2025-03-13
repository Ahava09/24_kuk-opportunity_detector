import os
import openai  
from config import OPENAI_API_KEY
from sqlalchemy import Column, Integer
from app.database import db
from flask import current_app

openai.api_key = OPENAI_API_KEY

class PartnerCompany(db.Model):
    __tablename__ = "partner_company"

    id = Column(Integer, primary_key=True, autoincrement=True)
    partner_id = db.Column(db.Integer, db.ForeignKey('res_partner.id'), nullable=True)
    company_id = db.Column(db.Integer, db.ForeignKey('res_company.id'), nullable=True)

    res_partner = db.relationship("ResPartner", backref="partner_company", uselist=False)  # Relation avec Email
    res_company = db.relationship("ResCompany", backref="partner_company", uselist=False)  # Relation avec State


    def __init__(self, partner_id, company_id):
        self.partner_id = partner_id
        self.company_id = company_id
    
    def save(self):
        try:
            db.session.add(self)
            db.session.commit()
            db.session.refresh(self)  # Recharge l'objet avec les nouvelles valeurs
            return self
        except Exception as e:
            db.session.rollback()
            raise e
        

    def to_dict(self):
        """ Convertit un objet EmailsState en dictionnaire JSON """
        
        return {
            "id": self.id,
            "partner_id": self.partner_id,
            "company_id": self.company_id,
            "res_partner": self.res_partner.to_dict() if self.res_partner else None,  
            "res_company": self.res_company.to_dict() if self.res_company else None   
        }

    @staticmethod
    def get_all_json():
        """ Récupère tous les EmailsState sous forme de JSON """
        partner_company = PartnerCompany.query.all()
        return [pc.to_dict() for pc in partner_company]

    @classmethod
    def get_by_partner_id(cls, partner_id):
        return cls.query.filter_by(partner_id=partner_id).first()
    
    @classmethod
    def get_company(cls, partner_id):
        current_app.logger.info(partner_id)
        pc = cls.query.filter_by(partner_id=partner_id).first()
        if pc:
            return pc.res_company
        else : 
            return None

    @classmethod
    def add_partner_company(cls, partner_id, company_id):
        new_partner_company = cls(partners_id=partner_id, company_id=company_id)
        db.session.add(new_partner_company)
        db.session.commit()
        return new_partner_company
    