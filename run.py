from flask import jsonify, request, render_template
from sqlalchemy.exc import SQLAlchemyError
from app.models.email_analyze import EmailAnalyze
from app.models.emails_partner import EmailsPartner
from app.models.emails import Emails
from app.models.state import State
from app.models.emails_state import EmailsState
from app.models.mail_type import MailType
from app.models.res_partner import ResPartner
from app import create_app, socketio
from app.database import db
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, decode_token
from config import JWT_SECRET_KEY, JWT_ACCESS_TOKEN_EXPIRES
from datetime import datetime
import traceback
import time
import threading
from imapclient import IMAPClient
from flask_socketio import emit

app = create_app()

app.config["JWT_SECRET_KEY"] =   JWT_SECRET_KEY
app.config["JWT_ACCESS_TOKEN_EXPIRES"] =  JWT_ACCESS_TOKEN_EXPIRES
jwt = JWTManager(app)

import imaplib
imaplib.Debug = 4

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email et mot de passe requis"}), 400

    email_client = EmailAnalyze(email, password)

    try:
        email_client.connect()  # Connexion à la boîte mail
        # 🔐 Stocker email et password dans le token
        user_identity = {"email": email, "password": password}
        access_token = create_access_token(identity=user_identity) 

        return jsonify({
            "token": access_token,
            "message": "Connexion réussie"
        }), 200

    except Exception as e:
        app.logger.error(f"Erreur de connexion: {str(e)}")
        traceback.print_exc()

        return jsonify({"error": "Échec de connexion, vérifiez vos identifiants"}), 401

@app.route('/email')
def email():
    return render_template("email.html", title="Gestion mail")

@app.route("/")
def index():
    return render_template("index.html", title="Connexion - Emails")

@app.route("/save_emails", methods=["POST"])
@jwt_required()
def save_emails():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "Aucune donnée reçue"}), 400

        emails = data.get("emails", [])
        if not emails:
            return jsonify({"message": "Aucun email à traiter"}), 400

        old_total = Emails.query.count()
        new_count = 0
        new_mail = []
        try:
            for email_data in emails:
                try:
                    percentage = email_data.get("percentage", 0)
                    mail_type = MailType.select_by_type_name(email_data["type"])

                    if not mail_type:
                        app.logger.error(f"Type de mail inconnu : {email_data['type']}")
                        continue

                    new_email = Emails(
                        subject=email_data["subject"],
                        sender=email_data["sender"],
                        mail=email_data["mail"],
                        body=email_data["body"],
                        receive_at=email_data["receive_at"],
                        path=email_data["path"],
                        percentage=percentage,
                        mail_type_id=mail_type.id
                    )
                    db.session.add(new_email)

                    partner = ResPartner.verify_partner(new_email)
                    if partner is None:
                        state_id = State.default()
                        if state_id is None:
                            raise Exception("État par défaut introuvable.")
                        emails_state = EmailsState(new_email.id, state_id)
                        db.session.add(emails_state)
                        new_mail.append(emails_state)
                        # --------------------------------- Rehefa is client
                    else:
                        state_id = State.is_partner()
                        if state_id is None:
                            raise Exception("État par défaut introuvable.")
                        emails_state = EmailsState(new_email.id, state_id)
                        db.session.add(emails_state)
                        new_mail.append(emails_state)
                        emailsPartner = EmailsPartner(partner.id, new_email.id)
                        db.session.add(emailsPartner)

                    new_count += 1

                except Exception as e:
                    app.logger.error(f"Erreur lors du traitement de l'email : {str(e)}")
                    db.session.rollback()  # Annuler uniquement cette opération
                    continue
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Erreur lors de la transaction globale : {str(e)}")
            return jsonify({"error": "Erreur interne lors du traitement des emails."}), 500

        new_total = old_total + new_count
        db.session.commit()  
        # app.logger.info("Emails envoyés via socket:", new_mail)
        socketio.emit("new_email", {
            "total": new_total,
            "new_count": new_count, 
            "new_emails": [email.to_dict() for email in new_mail]
        })
        
        return jsonify({"message": f"{new_count} emails traités avec succès."}), 200

    except Exception as e:
        app.logger.error(f"Erreur générale : {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/get_emails", methods=["GET"])
@jwt_required()
def get_emails():
    current_user = get_jwt_identity()    # ✅ Récupérer email et mot de passe du token
    app.logger.info(current_user)
    username = current_user["email"]
    password = current_user["password"]
    mail_type_id = request.args.get('mail_type_id')
    date_since = request.args.get('date_since')
    date_before = request.args.get('date_before')
    if not mail_type_id:
        return jsonify({"error": "mail_type_id is required"}), 400
    try:
        mail_type_id = int(mail_type_id)
    except ValueError:
        return jsonify({"error": "mail_type_id must be an integer"}), 400

    email_client = EmailAnalyze(username, password)
    app.logger.info(email_client)

    try:
        if date_since:
            date_since = datetime.strptime(date_since, "%Y-%m-%d")
        if date_before:
            date_before = datetime.strptime(date_before, "%Y-%m-%d")
        emails = email_client.get_unread_emails_since(date_since, date_before, mail_type_id)
        app.logger.info(emails)
        new_emails = []  # Liste pour stocker les objets à insérer

        for email in emails:
            try:
                existing_email = email.verify()

                if existing_email:
                    app.logger.info(email.percentage)
                    new_emails.append(email)
                    continue

            except SQLAlchemyError as e:
                db.session.rollback()
                app.logger.error(f"Erreur SQLAlchemy: {str(e)}")
                return jsonify({"error": "Erreur lors de l'insertion en base"}), 500
            
        emails_json = [e.to_dict() for e in new_emails]
        types = MailType.get_all_json()
        return jsonify({"emails": emails_json, "types": types})


    except Exception as e:
        app.logger.error(f"Erreur serveur: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    
@app.route("/get_emails_bdd", methods=["GET"])
@jwt_required()
def get_emails_bdd():
    try:

        mails = EmailsState.get_all_json()
        state = State.get_all_json()
        return jsonify({ "emails_bdd":mails, "state": state})


    except Exception as e:
        app.logger.error(f"Erreur serveur: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
   

@app.route("/update_email_state", methods=["POST"])
@jwt_required()
def update_email_state():
    data = request.json
    email_id = data.get("emailId")
    new_state_id = data.get("newStateId")

    if not email_id or not new_state_id:
        return jsonify({"success": False, "message": "Données manquantes"}), 400

    try:
        # app.logger.info(f"{new_state_id}---------------- {email_id}")
        email_state = EmailsState.update_state_id(email_id, new_state_id)
        if email_state:
            partner = ResPartner.verify_state(email_state)
            
            if partner:
                return jsonify({
                    "success": True,
                    "message": "Email mis à jour & Partenaire créé ou existant",
                    "data": partner.to_dict()
                }), 200
            else:
                return jsonify({
                    "success": True,
                    "message": "Email mis à jour, mais aucun partenaire n'a été créé"
                }), 200
        else:
            return jsonify({"success": False, "message": "Email introuvable"}), 404

    except Exception as e:
        app.logger.error(f"Erreur serveur: {str(e)}")
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/generate_ai_message", methods=["POST"])
@jwt_required()
def generate_ai_message():
    try:
        data = request.json
        subject = data.get("subject", "Demande d'information")
        recipient = data.get("recipient", "")
        existing_text = data.get("existingText", "").strip()
        app.logger.info(existing_text)

        mail_generer = EmailAnalyze.generate_message_mail(recipient, subject, existing_text)
        return jsonify({"message": mail_generer})

    except Exception as e:
        app.logger.error(e)
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    socketio.run(app, host='0.0.0.0', port=5001, debug=True, allow_unsafe_werkzeug=True)
