from flask import current_app
from app.database import db
from sqlalchemy.exc import SQLAlchemyError

class ResCompany(db.Model):
    __tablename__ = 'res_company'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)
    street = db.Column(db.String(255))
    city = db.Column(db.String(100))
    zip = db.Column(db.String(20))
    phone = db.Column(db.String(50))
    email = db.Column(db.String(255), unique=True)
    website = db.Column(db.String(255))
    logo = db.Column(db.String)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    def __init__(self, name, street=None, city=None, zip=None, phone=None, email=None, website=None, logo=None):
        """
        Initialise un nouvel objet ResCompany.
        """
        self.name = name
        self.street = street
        self.city = city
        self.zip = zip
        self.phone = phone
        self.email = email
        self.website = website
        self.logo = logo

    def to_dict(self):
        """
        Convertit l'objet en dictionnaire JSON.
        """
        return {
            "id": self.id,
            "name": self.name,
            "street": self.street,
            "city": self.city,
            "zip": self.zip,
            "phone": self.phone,
            "email": self.email,
            "website": self.website,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None
        }

    def save(self):
        """
        Enregistre l'objet dans la base de données.
        """
        try:
            db.session.add(self)
            db.session.commit()
            db.session.refresh(self)
            return self
        except SQLAlchemyError as e:
            db.session.rollback()
            raise e

    @classmethod
    def get_by_id(cls, company_id):
        """
        Récupère une entreprise par son ID.
        """
        return cls.query.get(company_id)

    @classmethod
    def exists(cls, name=None, email=None):
        """
        Vérifie si une entreprise existe déjà avec le même nom ou email.
        """
        query = cls.query
        if name:
            query = query.filter(cls.name == name)
        if email:
            query = query.filter(cls.email == email)
        
        return query.first() is not None

    @classmethod
    def save_company_from_json(cls, email_id):
        """
        🔄 Charge les informations d'un email depuis le fichier JSON et enregistre le partenaire.
        """
        try:
            from app.models.email_analyze import EmailAnalyze
            company_data = EmailAnalyze.load_email_data(email_id)
            company_name = company_data.get("company_name")
            if not company_name:
                current_app.logger.warning("⚠️ Aucune entreprise à enregistrer (Nom manquant)")
                return None

            # ✅ Vérifier si l'entreprise existe déjà
            existing_company = cls.exists(name = company_name, email = None)
            if existing_company:
                current_app.logger.info(f"✅ Entreprise '{company_name}' existe déjà.")
                return existing_company

            # 🆕 Créer et enregistrer la nouvelle entreprise
            new_company = cls(
                name=company_name,
                street=company_data.get("company_street"),
                phone=company_data.get("company_phone"),
                email=company_data.get("company_email"),
                website=company_data.get("company_website")
            )
            new_company = new_company.save()
            current_app.logger.info(f"✅ Nouvelle entreprise '{company_name}' enregistrée avec succès.")
            return new_company

        except Exception as e:
            current_app.logger.error(f"❌ Erreur lors de l'enregistrement de l'entreprise : {e}")
            return None
        