from flask import Flask, jsonify, request, render_template
import os
from sqlalchemy.exc import SQLAlchemyError
from app.models.email_client import EmailClient, Email
from app import create_app
from app.database import db

app = create_app()

@app.cli.command("create-db")
def create_db():
    """Commande pour créer la base de données."""
    with app.app_context():
        db.create_all()
        print("✅ Base de données créée avec succès !")


@app.route('/email')
def dashboard():
    return render_template("email.html")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/test_db")
def test_db():
    try:
        db.session.execute("SELECT 1")
        return "Connexion à PostgreSQL réussie !"
    except SQLAlchemyError as e:
        app.logger.error(f"Erreur SQLAlchemy: {str(e)}")
        return f"Erreur SQLAlchemy: {str(e)}"
    except Exception as e:
        app.logger.error(f"Erreur inconnue: {str(e)}")
        return f"Erreur inconnue: {str(e)}"

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
        date_since = "23-Feb-2025"  # Modifier selon besoin
        emails = email_client.get_unread_emails_since(date_since)
        email_client.disconnect()

        emails_json = []
        new_emails = []  # Liste pour stocker les objets à insérer

        for email in emails:
            try:
                existing_email = email.save()
            
                if existing_email:
                    app.logger.info(f"Email déjà existant : {email.subject} - {email.receive_at}")
                    continue  # Ne pas insérer ce mail
                new_emails.append(email)  # Ajouter à la liste des emails uniques

                emails_json.append({
                    "subject": email.subject,
                    "from": email.sender,
                    "body": email.body,
                    "is_negoce": email.is_negoce
                })
            except SQLAlchemyError as e:
                db.session.rollback()
                app.logger.error(f"Erreur SQLAlchemy: {str(e)}")
                return jsonify({"error": "Erreur lors de l'insertion en base"}), 500

        return jsonify({"unread_count": len(emails_json), "emails": emails_json})

    except Exception as e:
        import traceback
        app.logger.error(f"Erreur serveur: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    with app.app_context():  
        db.create_all() 
        app.run(host='0.0.0.0', port=5000, debug=True)
