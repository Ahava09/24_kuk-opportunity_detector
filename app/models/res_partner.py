from flask import current_app
from app.database import db
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
            existing_partner = ResPartner.query.filter_by(email=emails.mail, name = emails.sender).first()
            if not existing_partner:
                partner = ResPartner(
                    name=emails.sender,
                    email=emails.mail,
                    phone=None,
                    is_company=False
                )
                partner.save()
                print(f"Partenaire {partner.name} créé avec succès.")
            else:
                print(f"Partenaire {existing_partner.name} existe déjà.")
        else:
            print("Email introuvable")
            
    @staticmethod    
    def get_partner(emails):
        partner = ResPartner(
                        name=emails.sender,
                        email=emails.mail,
                        is_company=False
                    )
        return partner

    @staticmethod
    def verify_state(emails_state):
        """Vérifier si l'email est accepté"""
        state = emails_state.is_accepted()
        if state:
            emails = Emails.get_by_id(emails_state.emails_id)
            if emails:
                partner = ResPartner.query.filter_by(email=emails.mail, name = emails.sender).first()
                if not partner:
                    partner = ResPartner.get_partner(emails)
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
        existing_partner = ResPartner.query.filter_by(email=emails.mail, name = emails.sender).first()
        
        if existing_partner:
            return existing_partner
        else:
            # Si l'expéditeur n'est pas un client
            print(f"L'expéditeur {emails.sender} n'est pas un client existant.")
            return None 
    
    def exist (partner):
        # Chercher le partenaire existant en fonction de l'email actuel
        existing_partner = ResPartner.query.filter_by(email=partner.email, name = partner.sender).first()
        
        if existing_partner:
            return existing_partner
        else:
            print(f"L'expéditeur {partner.sender} n'est pas un client existant.")
            return None 
    
    @staticmethod
    def save_partner_from_json(email_id):
        """
        🔄 Charge les informations d'un email depuis le fichier JSON et enregistre le partenaire.
        """
        try:
            from app.models.email_analyze import EmailAnalyze
            data_json = EmailAnalyze.load_email_data(email_id)

            if not data_json:
                current_app.logger.error(f"❌ Aucune donnée trouvée pour l'email ID {email_id}")
                return {"error": "Données non trouvées"}

            current_app.logger.info(f"📂 Données chargées pour l'email ID {email_id}")

            # ✅ Récupérer les infos du client depuis JSON
            client_name = data_json.get("client_name")
            client_email = data_json.get("client_email")
            client_phone = data_json.get("client_phone")
            is_company = data_json.get("is_company", False)

            # 🔎 Vérifier si le partenaire existe déjà
            existing_partner = ResPartner.query.filter_by(email=client_email, name=client_name).first()

            if existing_partner:
                current_app.logger.info(f"✅ Partenaire {client_name} existe déjà.")
                return existing_partner.to_dict()
            
            # 🆕 Si le partenaire n'existe pas, on le crée
            new_partner = ResPartner(
                name=client_name,
                email=client_email,
                phone=client_phone,
                is_company=is_company
            )

            # 💾 Sauvegarde en base de données
            new_partner.save()
            current_app.logger.info(f"✅ Nouveau partenaire {new_partner.name} enregistré avec succès.")
            return new_partner

        except Exception as e:
            current_app.logger.error(f"❌ Erreur lors de l'enregistrement du partenaire : {e}")
            return {"error": str(e)}