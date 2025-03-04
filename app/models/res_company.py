from flask import  request, jsonify
from app.database import db
from sqlalchemy import Column, Integer, String, Text, Boolean

class ResCompany(db.Model):
    __tablename__ = 'res_company'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    street = db.Column(db.String(255))
    city = db.Column(db.String(100))
    zip = db.Column(db.String(20))
    # country_id = db.Column(db.Integer, db.ForeignKey('res_country.id'), nullable=True)
    phone = db.Column(db.String(50))
    email = db.Column(db.String(255), unique=True)
    website = db.Column(db.String(255))
    logo = db.Column(db.LargeBinary)
    # currency_id = db.Column(db.Integer, db.ForeignKey('res_currency.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "street": self.street,
            "city": self.city,
            "zip": self.zip,
            # "country_id": self.country_id,
            "phone": self.phone,
            "email": self.email,
            "website": self.website,
            # "currency_id": self.currency_id,
            "created_at": self.created_at
        }
