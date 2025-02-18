from flask import Flask, jsonify, request, send_from_directory
import os
from email_client import EmailClient

app = Flask(__name__)

# Informations de connexion
# username = os.getenv("EMAIL_USER")
# password = os.getenv("EMAIL_PASS")


@app.route("/")
def index():
    return send_from_directory(".", "index.html")  

@app.route("/get_emails", methods=["POST"])
def get_emails():
    data = request.get_json()
    username = data.get("email")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Email et mot de passe requis"}), 400

    email_client = EmailClient(username, password)

    try:
        email_client.connect()
        date_since = "15-Feb-2025"  # Modifier selon besoin
        emails = email_client.get_unread_emails_since(date_since)
        email_client.disconnect()

        emails_json = [
            {"subject": email.subject, "from": email.sender, "body": email.body, "attachments": len(email.attachments)}
            for email in emails
        ]
        return jsonify(emails_json)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
