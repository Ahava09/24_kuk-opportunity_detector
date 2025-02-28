import os
from sqlalchemy import Column, Integer, String, Text, Float
from datetime import datetime
from app.database import db

class Emails(db.Model):
    __tablename__ = "emails"

    id = Column(Integer, primary_key=True, autoincrement=True)
    subject = Column(String(255), nullable=False)
    sender = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    receive_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    path = db.Column(db.String(100))
    percentage = Column(Float, default=0)
    mail_type_id = db.Column(db.Integer, db.ForeignKey('mail_type.id'), nullable=True)

    def __init__(self, subject, sender, body,path , receive_at, percentage=0, mail_type_id=None):
        self.subject = subject
        self.sender = sender
        self.body = body
        self.percentage = percentage
        self.path = path
        self.receive_at = receive_at
        self.mail_type_id = mail_type_id

    def to_dict(self):
        """ Convertit un objet Emails en dictionnaire JSON """
        return {
            "id": self.id,
            "subject": self.subject,
            "sender": self.sender,
            "body": self.body,
            "receive_at": self.receive_at.isoformat() if self.receive_at else None,
            "path": self.path,
            "percentage": self.percentage,
            "mail_type_id": self.mail_type_id
        }
    
    @classmethod
    def exists(cls, subject, sender, receive_at):
        existing_email = cls.query.filter_by(subject=subject, sender=sender, receive_at=receive_at).first()
        return existing_email is not None  

    def save(self):
        # Vérifier si l'email existe déjà avant de l'enregistrer
        if not Emails.exists(self.subject, self.sender, self.receive_at):
            # db.session.add(self)
            # db.session.commit()
            return True
        return False

    @staticmethod 
    def get_all_json():
        emails = Emails.query.all()
        return [email.to_dict() for email in emails]
    
    def __repr__(self):
        return f"<Email id={self.id}, subject={self.subject}, sender={self.sender}>"
    
    @staticmethod 
    def message_chat(message):
        print("Reformulation du message pour le critère")
        return f"""
        Analyse le contenu de cet email pour déterminer s'il concerne {message}.

        Ta réponse doit être uniquement entre 0 à 100, de quel pourcentage s'agit il de ce type si on a ce mail.
        """
