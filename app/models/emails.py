import os
from sqlalchemy import Column, Integer, String, Text, Float, Boolean
from datetime import datetime
from app.database import db
from app.models.mail_type import MailType

class Emails(db.Model):
    __tablename__ = "emails"

    id = Column(Integer, primary_key=True, autoincrement=True)
    subject = Column(String(255), nullable=False)
    sender = Column(String(255), nullable=False)
    mail =  Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    receive_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    path = db.Column(db.String)
    percentage = Column(Float, default=0)
    mail_type_id = db.Column(db.Integer, db.ForeignKey('mail_type.id'), nullable=True)
    type_name = db.String 
    already_answered = db.Column(db.Boolean, default=False)

    def __init__(self, subject, sender, mail, body,path , receive_at, percentage=0, mail_type_id=None, already_answered=False):
        self.subject = subject
        self.sender = sender
        self.mail = mail
        self.body = body
        self.percentage = percentage
        self.path = path
        self.receive_at = receive_at
        self.mail_type_id = mail_type_id
        self.already_answered = already_answered

    def get_type_name(self):
        self.type_name = MailType.select_by_id(self.mail_type_id).type_name

    def to_dict(self):
        """ Convertit un objet Emails en dictionnaire JSON """
        self.get_type_name()
        return {
            "id": self.id,
            "subject": self.subject,
            "sender": self.sender,
            "mail": self.mail,
            "body": self.body,
            "receive_at": self.receive_at.isoformat() if self.receive_at else None,
            "path": self.path,
            "percentage": self.percentage,
            "mail_type_id": self.mail_type_id,
            "type_name": self.type_name,
            "already_answered": self.already_answered
        }
    
    @classmethod
    def exists(cls, subject, sender, mail, receive_at):
        existing_email = cls.query.filter_by(subject=subject, sender=sender, receive_at=receive_at, mail = mail).first()
        return existing_email is not None  

    def save(self):
        try:
            db.session.add(self)
            db.session.commit()
            db.session.refresh(self)  # Recharge l'objet avec les nouvelles valeurs
            return self
        except Exception as e:
            db.session.rollback()
            raise e
    
    
    def verify(self):
        if not Emails.exists(self.subject, self.sender, self.mail, self.receive_at):
            return True
        return False
        
    @staticmethod 
    def get_all_json():
        emails = Emails.query.all()
        return [email.to_dict() for email in emails]
    
    def __repr__(self):
        return f"<Email id={self.id}, subject={self.subject}, sender={self.sender}>"

    @classmethod
    def get_by_id(cls, email_id):
        """ Récupérer un email par son ID """
        email = cls.query.get(email_id)
        if email:
            return email
        return None
    
    
    @staticmethod
    def get_by_path(path):
        email = Emails.query.filter_by(path=path).first()
        if email:
            return email
        return None

    @classmethod
    def is_already_answered (cls, emails):
        try:
            # Récupérer l'état de l'email
            email = cls.get_by_id(emails.id)
            
            if email:
                # Mettre à jour l'état
                email.already_answered = True
                db.session.commit()
                db.session.refresh(email)  # Recharge l'objet
                return email
            else:
                return None  # Si aucun email n'est trouvé
        except Exception as e:
            db.session.rollback()
            raise e
        