from flask import jsonify, request, render_template, Response, send_file, render_template_string
from sqlalchemy.exc import SQLAlchemyError
from app.models.email_analyze import EmailAnalyze
from app.models.emails_partner import EmailsPartner
from app.models.email_attachment import EmailAttachment
from app.models.emails import Emails
from app.models.state import State
from app.models.emails_state import EmailsState
from app.models.mail_type import MailType
from app.models.res_partner import ResPartner
from app import create_app, socketio
from app.database import db
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from config import JWT_SECRET_KEY, JWT_ACCESS_TOKEN_EXPIRES, MAKE_WEBHOOK_URL, GMAIL_USER, GMAIL_PASSWORD, PUBLIC_BASE_URL
from datetime import datetime
import traceback
from flask_migrate import Migrate
import requests
import io
import os
import threading
import openai  
from config import OPENAI_API_KEY

openai.api_key = OPENAI_API_KEY

app = create_app()
migrate = Migrate(app, db)

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

def auto_save_email(e, attachments_cache):
    try:
        percentage = float(e.get("percentage", 0))
        if percentage < 50:
            return False

        new_email = Emails(
            subject=e["subject"],
            sender=e["sender"],
            mail=e["mail"],
            body=e["body"],
            receive_at=e["receive_at"],
            path=e["path"],
            percentage=percentage,
            mail_type_id=e["mail_type_id"]
        )
        db.session.add(new_email)
        db.session.flush()

        # 📎 Enregistrement des pièces jointes
        for attachment in e.get("attachments", []):
            clean_filename = attachment["filename"].split("?")[0]
            file_id = f"{e['mail']}_{clean_filename}"
            att = attachments_cache.get(file_id)
            if att:
                db.session.add(EmailAttachment(
                    email_id=new_email.id,
                    filename=att["filename"],
                    content_type=att["content_type"],
                    data=att["data"]
                ))

        # 🔗 Vérification partenaire
        partner = ResPartner.verify_partner(new_email)
        if partner:
            state_id = State.is_partner()
            db.session.add(EmailsPartner(partner.id, new_email.id))
        else:
            state_id = State.default()

        emails_state = EmailsState(new_email.id, state_id)
        db.session.add(emails_state)
        db.session.commit()

        # 🟢 Événement Socket
        socketio.emit("new_email", {
            "total": Emails.query.count(),
            "new_count": 1,
            "new_emails": [emails_state.to_dict()]
        })
        return True

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"❌ Erreur auto_save_email : {e}")
        return False


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
                    app.logger.info(email_data["type"])
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
                    db.session.flush()
            
                    for attachment in email_data.get("attachments", []):
                        clean_filename = attachment["filename"].split("?")[0]  # 🔹 Retirer "?email=..."
                        file_id = f"{email_data['mail']}_{clean_filename}"  # ✅ Utiliser le bon format

                        app.logger.info("🔎 Recherche dans cache avec clé : %s", file_id)

                        attachment_data = attachments_cache.get(file_id)  # 🔹 Récupérer depuis le cache

                        if attachment_data:
                            app.logger.info("✅ Pièce jointe trouvée dans cache :", attachment_data)
                            new_attachment = EmailAttachment(
                                email_id=new_email.id,
                                filename=attachment_data["filename"],
                                content_type=attachment_data["content_type"],
                                data=attachment_data["data"]
                            )
                            db.session.add(new_attachment)
                        else:
                            app.logger.warning("❌ Pièce jointe non trouvée dans cache : %s", file_id)


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
        try:
            for email in new_mail:
                email_data = {
                    "subject": email.subject,
                    "sender": email.sender,
                    "mail": email.mail,
                    "body": email.body,
                    "receive_at": email.receive_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "percentage": email.percentage,
                    "path": email.path
                }
                response = requests.post(MAKE_WEBHOOK_URL, json=email_data)
                app.logger.info(f"Envoyé à Make : {response.status_code} - {response.text}")

        except Exception as e:
            app.logger.error(f"Erreur lors de l'envoi des données à Make : {str(e)}")
        
        return jsonify({"message": f"{new_count} emails traités avec succès."}), 200

    except Exception as e:
        app.logger.error(f"Erreur générale : {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/download_attachment/<filename>")
def download_attachment(filename):
    """
    Permet de télécharger une pièce jointe depuis la mémoire, sans rappeler get_unread_emails_since.
    """
    global attachments_cache

    email_sender = request.args.get("email")
    file_id = f"{email_sender}_{filename}"  # On recrée la clé unique

    attachment = attachments_cache.get(file_id)  # 🔹 Récupération depuis la mémoire
    if not attachment:
        return Response("Pièce jointe non trouvée", status=404)

    return send_file(
        io.BytesIO(attachment["data"]),
        mimetype=attachment["content_type"],
        as_attachment=True,
        download_name=attachment["filename"]
    )

# Stockage temporaire des pièces jointes en mémoire (clé = nom du fichier)
attachments_cache = {}

@app.route("/get_emails", methods=["GET"])
@jwt_required()
def get_emails():
    global attachments_cache  # Utilisation de la mémoire partagée
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
        new_emails = []  # Liste pour stocker les objets à insérer
        attachments_cache.clear()

        for e in emails:
            try:
                email = Emails (
                    subject = e["subject"], 
                    sender = e["sender"], 
                    mail = e["mail"],
                    body = e["body"],
                    receive_at = e["receive_at"],
                    path = e["path"],
                    percentage = e["percentage"],
                    mail_type_id = e["mail_type_id"]
                )
                existing_email = email.verify()
                

                if existing_email:
                    app.logger.info(email.percentage)
                    email_obj = {
                        "subject": e["subject"],
                        "sender": e["sender"],
                        "mail": e["mail"],
                        "body": e["body"],
                        "receive_at": e["receive_at"].isoformat() if isinstance(e["receive_at"], datetime) else e["receive_at"],
                        "path": e["path"],
                        "percentage": e["percentage"],
                        "mail_type_id": e["mail_type_id"],
                        "attachments": []
                    }

                    # 📎 Stocker les pièces jointes en mémoire
                    for attachment in e["attachments"]:
                        clean_filename = attachment["filename"].split("?")[0]  # 🔹 Retirer "?email=..."
                        file_id = f"{e['mail']}_{clean_filename}"  # Clé propre

                        attachments_cache[file_id] = {
                            "filename": clean_filename,
                            "content_type": attachment["content_type"],
                            "data": attachment["data"]
                        }

                        email_obj["attachments"].append({
                            "filename": clean_filename 
                        })
                    
                    
                    percentage = float(e.get("percentage", 0))

                    # Enregistrement automatique
                    if percentage >= 50:
                        success = auto_save_email(email_obj, attachments_cache)
                    new_emails.append(email_obj)

                    continue

            except SQLAlchemyError as e:
                db.session.rollback()
                app.logger.error(f"Erreur SQLAlchemy: {str(e)}")
                return jsonify({"error": "Erreur lors de l'insertion en base"}), 500
            
        types = MailType.get_all_json()

        return jsonify({"emails": new_emails, "types": types})


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

        # Ajouter les pièces jointes pour chaque email
        for mail in mails:
            email_id = mail["emails_id"]
            attachments = EmailAttachment.query.filter_by(email_id=email_id).all()
            mail["attachments"] = [attachment.to_dict() for attachment in attachments]

        return jsonify({"emails_bdd": mails, "state": state})

    except Exception as e:
        app.logger.error(f"Erreur serveur: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

import base64

@app.route("/email/<int:email_id>/attachments", methods=["GET"])
def get_email_attachments(email_id):
    try:
        email = Emails.query.get_or_404(email_id)

        # Ajout des pièces jointes encodées en base64
        attachments = EmailAttachment.query.filter_by(email_id=email_id).all()
        attachments_data = [
            {
                "id": att.id,
                "filename": att.filename,
                "content_type": att.content_type,
                "created_at": att.created_at.isoformat() if att.created_at else None,
                "base64": base64.b64encode(att.data).decode("utf-8")
            }
            for att in attachments
        ]

        return jsonify({
            "email_id": email_id,
            "subject": email.subject,
            "attachments": attachments_data
        })

    except Exception as e:
        app.logger.error(f"Erreur lors de la récupération des pièces jointes : {str(e)}")
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

client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.route("/verifier_designation", methods=["POST"])
def verifier_designation():
    data = request.json
    designation = data.get("designation", "")
    categorie = data.get("categorie", "")
    attributs = data.get("attributs", [])

    if not designation or not categorie or not attributs:
        return jsonify({"error": "Champs manquants"}), 400

    prompt = f"""
        Tu es un assistant expert en technique industrielle.
        Voici une désignation client : "{designation}"
        Catégorie : {categorie}
        Voici les attributs à extraire :
        {attributs}

        Analyse la désignation et remplis les attributs ci-dessous.
        Si une valeur est introuvable, laisse-la vide.

        Réponds uniquement en JSON :
        {{
        {', '.join([f'"{attr}": ""' for attr in attributs])}
        }}
        """

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=150
        )
        content = response.choices[0].message.content

        result = eval(content) if content.strip().startswith("{") else {"raw": content}
        status = "complet" if all(result.get(attr, "").strip() for attr in attributs) else "incomplet"
        result["status"] = status

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def start_idle_watcher(app):
    from email_watcher import idle_watch
    with app.app_context():
        idle_watch(GMAIL_USER, GMAIL_PASSWORD)


forms_db = {} 

@app.route('/generate-form', methods=['POST'])
def generate_form():
    import uuid
    data = request.get_json()
    form_id = str(uuid.uuid4())
    forms_db[form_id] = data  # stocke la structure à afficher
    public_url = f"{PUBLIC_BASE_URL}/formulaire?id={form_id}"
    return public_url

@app.route('/formulaire', methods=['GET', 'POST'])
def formulaire():
    form_id = request.args.get("id")
    form_data = forms_db.get(form_id)

    if not form_data:
        return "Formulaire introuvable.", 404

    if request.method == 'POST':
        reponses = []

        for designation in form_data:
            designation_id = designation.get("designation_id")
            ligne = {
                "designation_id": designation_id,
                "designation": designation["x_designation_originale"],
                "reponses": []
            }

            for attr in designation.get("x_attributs", []):
                attr_id = attr["attributs"]["id"]
                attr_label = attr["attributs"]["value"]
                champ = f"{designation_id}_{attr_id}"
                valeur = request.form.get(champ, "").strip()

                if valeur:
                    ligne["reponses"].append({
                        "designation_id": designation_id,
                        "attribut_id": attr_id,
                        "attribut_label": attr_label,
                        "value": valeur
                    })

            reponses.append(ligne)

        app.logger.info("✔️ Réponses client :", reponses)
        requests.post('https://hook.eu2.make.com/yppt782socbyl6wokwfo3carjcsjamrt', json={"reponses": reponses})
        return "Merci pour votre réponse !"

    # Affichage HTML
    html = "<h2>Merci de compléter les informations techniques</h2><form method='post'>"
    for designation in form_data:
        html += f"<h3>{designation['x_designation_originale']}</h3>"
        designation_id = designation['designation_id']

        for attr in designation.get("x_attributs", []):
            attr_id = attr["attributs"]["id"]
            attr_label = attr["attributs"]["value"]
            champ = f"{designation_id}_{attr_id}"
            options = attr["values"]
            selected = attr.get("value_selected")

            html += f"<label>{attr_label}</label><br><select name='{champ}' required>"
            html += "<option value=''>-- Choisir --</option>"
            for option in options:
                selected_attr = "selected" if selected and option["id"] == selected["id"] else ""
                html += f"<option value='{option['id']}' {selected_attr}>{option['label']}</option>"
            html += "</select><br><br>"

    html += "<button type='submit'>Envoyer</button></form>"
    return render_template_string(html)

# @app.route('/formulaire', methods=['GET', 'POST'])
# def formulaire():
#     designations = request.args.get('data')  # JSON encodé en string
#     import json
#     designations = json.loads(designations)
#     return render_template('formulaire.html', designations=designations)

if __name__ == "__main__":
    
    watcher_thread = threading.Thread(target=start_idle_watcher, args=(app,))
    watcher_thread.daemon = True
    watcher_thread.start()

    with app.app_context():
        db.create_all()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_reloader=False, allow_unsafe_werkzeug=True)

