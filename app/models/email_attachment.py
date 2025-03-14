from app.database import db
from datetime import datetime

class EmailAttachment(db.Model):
    __tablename__ = "email_attachments"
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email_id = db.Column(db.Integer, db.ForeignKey("emails.id"), nullable=False)  # Association avec Emails
    filename = db.Column(db.String(255), nullable=False)  # Nom du fichier
    content_type = db.Column(db.String(100), nullable=False)  # Type MIME (image/png, application/pdf, etc.)
    data = db.Column(db.LargeBinary, nullable=False)  # Stockage en binaire
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # Date d'ajout

    # Relation avec Emails
    email = db.relationship("Emails", backref=db.backref("attachments", lazy=True))

    def __init__(self, email_id, filename, content_type, data):
        self.email_id = email_id
        self.filename = filename
        self.content_type = content_type
        self.data = data

    def to_dict(self):
        """ Convertit un objet EmailAttachment en dictionnaire JSON """
        return {
            "id": self.id,
            "email_id": self.email_id,
            "filename": self.filename,
            "content_type": self.content_type,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
