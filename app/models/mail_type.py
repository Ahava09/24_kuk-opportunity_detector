from sqlalchemy import Column, Integer, String
from app.database import db

class MailType(db.Model):
    __tablename__ = "mail_type"

    id = Column(Integer, primary_key=True, autoincrement=True)
    type_name = Column(String(100), unique=True, nullable=False)

    def __init__(self, type_name):
        self.type_name = type_name

    def save(self):
        db.session.add(self)
        db.session.commit()

    def to_dict(self):
        """ Convertit un objet MailType en dictionnaire JSON """
        return {
            "id": self.id,
            "type_name": self.type_name
        }

    @staticmethod
    def get_all_json():
        """ Récupère tous les MailType sous forme de JSON """
        types = MailType.query.all()
        return [type.to_dict() for type in types]

    @staticmethod
    def select_by_id(mail_type_id):
        """ Récupère un enregistrement MailType par son ID """
        mail_type = MailType.query.get(mail_type_id)
        if mail_type:
            return mail_type
        return None

    @staticmethod
    def select_by_type_name(type_name):
        """ Récupère un enregistrement MailType par son type_name """
        mail_type = MailType.query.filter_by(type_name=type_name).first()
        if mail_type:
            return mail_type
        return None
