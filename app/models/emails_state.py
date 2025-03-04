from app.database import db

class EmailsState(db.Model):
    __tablename__ = "emails_state"
    
    id = db.Column(db.Integer, primary_key=True)
    emails_id = db.Column(db.Integer, db.ForeignKey("emails.id"), nullable=True)
    state_id = db.Column(db.Integer, db.ForeignKey("state.id", ondelete="SET NULL"))

    # Définir les relations avec les objets Email et State
    email = db.relationship("Emails", backref="emails_state", uselist=False)  # Relation avec Email
    state = db.relationship("State", backref="emails_state", uselist=False)  # Relation avec State

    def __repr__(self):
        return f"<EmailsState email_id={self.emails_id}, state_id={self.state_id}>"

    def __init__(self, emails_id, state_id):
        self.emails_id = emails_id
        self.state_id = state_id

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
            "emails_id": self.emails_id,
            "state_id": self.state_id,
            "email": self.email.to_dict() if self.email else None,  
            "state": self.state.to_dict() if self.state else None   
        }

    @staticmethod
    def get_all_json():
        """ Récupère tous les EmailsState sous forme de JSON """
        emails_state = EmailsState.query.all()
        return [state.to_dict() for state in emails_state]

    @classmethod
    def get_all_email_states(cls):
        return cls.query.all()

    @classmethod
    def get_email_state_by_email(cls, email_id):
        """Récupérer l'état d'un email spécifique"""
        return cls.query.filter_by(emails_id=email_id).first()

    @classmethod
    def add_email_state(cls, email_id, state_id):
        """Associer un email à un état"""
        new_email_state = cls(emails_id=email_id, state_id=state_id)
        db.session.add(new_email_state)
        db.session.commit()
        return new_email_state
    
    def save (self):
        try:
            db.session.add(self)
            db.session.commit()
            db.session.refresh(self)  # Recharge l'objet avec les nouvelles valeurs
            return self
        except Exception as e:
            db.session.rollback()
            raise e
