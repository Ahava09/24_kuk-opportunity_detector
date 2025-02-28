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

# Routes API CRUD
# @app.route('/companies', methods=['POST'])
# def create_company():
#     data = request.json
#     company = ResCompany(
#         name=data['name'],
#         street=data.get('street'),
#         city=data.get('city'),
#         zip=data.get('zip'),
#         country_id=data.get('country_id'),
#         phone=data.get('phone'),
#         email=data.get('email'),
#         website=data.get('website'),
#         currency_id=data.get('currency_id')
#     )
#     db.session.add(company)
#     db.session.commit()
#     return jsonify(company.to_dict()), 201

# @app.route('/companies', methods=['GET'])
# def get_companies():
#     companies = ResCompany.query.all()
#     return jsonify([company.to_dict() for company in companies])

# @app.route('/companies/<int:company_id>', methods=['GET'])
# def get_company(company_id):
#     company = ResCompany.query.get_or_404(company_id)
#     return jsonify(company.to_dict())

# @app.route('/companies/<int:company_id>', methods=['PUT'])
# def update_company(company_id):
#     company = ResCompany.query.get_or_404(company_id)
#     data = request.json
#     for key, value in data.items():
#         setattr(company, key, value)
#     db.session.commit()
#     return jsonify(company.to_dict())

# @app.route('/companies/<int:company_id>', methods=['DELETE'])
# def delete_company(company_id):
#     company = ResCompany.query.get_or_404(company_id)
#     db.session.delete(company)
#     db.session.commit()
#     return jsonify({"message": "Company deleted"}), 200
