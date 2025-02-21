from app.database import db
from datetime import datetime

class Emails(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(100))
    receive_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
