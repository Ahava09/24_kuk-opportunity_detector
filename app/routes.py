from flask import Blueprint, jsonify
from .models.emails import Emails
from .database import db

# Utilisation d'un nom unique pour le blueprint
api_emails_blueprint = Blueprint("api_emails", __name__)

@api_emails_blueprint.route("/emails", methods=["GET"])
def get_users():
    emails = Emails.query.all()
    return jsonify([{"id": email.id, "email": email.subject} for email in emails])
