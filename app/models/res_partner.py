from flask import request, jsonify
from app.database import db
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from app.models.emails import Emails

class ResPartner(db.Model):
    __tablename__ = 'res_partner'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True)
    phone = db.Column(db.String(50))
    is_company = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    def __init__(self, name, email=None, phone=None, is_company=False):
        self.name = name
        self.email = email
        self.phone = phone
        self.is_company = is_company

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "is_company": self.is_company,
            "created_at": str(self.created_at)
        }

    def save(self):
        try:
            db.session.add(self)
            db.session.commit()
            db.session.refresh(self)
            return self
        except Exception as e:
            db.session.rollback()
            raise e

    @staticmethod
    def get_all_json():
        """Récupère tous les partenaires au format JSON"""
        partners = ResPartner.query.all()
        return [partner.to_dict() for partner in partners]

    @classmethod
    def get_json(cls, partner_id):
        """Récupère un partenaire par son ID"""
        partner = cls.query.get(partner_id)
        if partner:
            return partner.to_dict()
        return None
    
    def save_partner_email(self, emails_state):
        emails = Emails.get_by_id(emails_state.emails_id)
        if emails:
            existing_partner = ResPartner.query.filter_by(email=emails.sender).first()
            if not existing_partner:
                partner = ResPartner(
                    name=emails.sender,
                    email=emails.sender,
                    phone=None,
                    is_company=False
                )
                partner.save()
                print(f"Partenaire {partner.name} créé avec succès.")
            else:
                print(f"Partenaire {existing_partner.name} existe déjà.")
        else:
            print("Email introuvable")

    @classmethod
    def verify_state(cls, emails_state):
        """Vérifier si l'email est accepté"""
        state = emails_state.is_accepted()
        if state:
            emails = Emails.get_by_id(emails_state.emails_id)
            if emails:
                partner = cls.query.filter_by(email=emails.sender).first()
                if not partner:
                    partner = cls(
                        name=emails.sender,
                        email=emails.sender,
                        is_company=False
                    )
                    partner.save()
                    print(f"Partenaire {partner.name} créé avec succès.")
                else:
                    print(f"Partenaire {partner.name} existe déjà.")
                return partner
        else:
            print("L'email n'est pas accepté.")
            return None
        
    @staticmethod
    def verify_partner (emails):
        # Chercher le partenaire existant en fonction de l'email actuel
        existing_partner = ResPartner.query.filter_by(email=emails.sender).first()
        
        if existing_partner:
            return existing_partner
        else:
            # Si l'expéditeur n'est pas un client
            print(f"L'expéditeur {emails.sender} n'est pas un client existant.")
            return None 