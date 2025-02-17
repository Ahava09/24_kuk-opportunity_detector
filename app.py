from flask import Flask, jsonify
import os
from email_client import EmailClient

app = Flask(__name__)

# Informations de connexion
username = os.getenv("EMAIL_USER")
password = os.getenv("EMAIL_PASS")

@app.route("/", methods=["GET"])
def get_emails():
    email_client = EmailClient(username, password)

    # Connexion au serveur
    email_client.connect()

    # Récupérer les emails non lus depuis une date donnée
    date_since = "15-Feb-2025"  # Exemple, tu peux adapter la date
    emails = email_client.get_unread_emails_since(date_since)

    # Déconnexion du serveur
    email_client.disconnect()

    # Convertir la liste d'objets Email en un format JSON
    emails_json = [
        {"subject": email.subject, "from": email.sender, "body": email.body,
            "attachments": email.attachments  }
        for email in emails
    ]

    return jsonify(emails_json)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
