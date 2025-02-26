from app.database import db
from datetime import datetime

class Emails(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(100))
    receive_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    path = db.Column(db.String(100))
    res_partner_id = db.Column(db.String(20))
