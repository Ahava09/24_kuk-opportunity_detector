from flask import Blueprint, current_app, jsonify, render_template, send_file, request, redirect, url_for, Response
from app.models.res_company import ResCompany
from app.models.res_partner import ResPartner
from app.models.emails_state import EmailsState
from app.models.emails import Emails
from app.models.email_analyze import EmailAnalyze, sanitize_data
from app.models.crm_odoo import structure_lead_payload_for_odoo
from app.models.partner_company import PartnerCompany
from app.models.state import State
from app.database import db
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from flask_socketio import emit
import io
from config import  MAKE_WEBHOOK_URL
import requests
import json

# Dossier où enregistrer les logos
UPLOAD_FOLDER = "app/static/uploads/company/logos"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

# Vérifier si l'extension du fichier est autorisée
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

api_emails_blueprint = Blueprint('api_emails', __name__)

# Route pour afficher la liste des clients
@api_emails_blueprint.route('/clients')
def clients():
    all_clients = ResPartner.query.all()
    # clt = [client.to_dict() for client in all_clients]
    # clean_data = sanitize_data(clt)
    # current_app.logger.info(f"Réponse Webhook: {clean_data}")
    # try:
    #     response = requests.get(MAKE_WEBHOOK_URL, json=clean_data)
    #     response.raise_for_status()
    #     current_app.logger.info(f"Réponse Webhook: {response.status_code}, {response.text}")
    # except requests.exceptions.RequestException as e:
    #     current_app.logger.error(f"Erreur d'envoi au webhook: {str(e)}")
    #     if response is not None:
    #         current_app.logger.error(f"Détails de l'erreur Webhook: {response.text}")
    return render_template('list.html', clients=all_clients, title="Gestion Client")

# Route pour afficher la liste des entreprises
@api_emails_blueprint.route('/companies')
def companies():
    all_companies = ResCompany.query.all()
    return render_template('list.html', companies=all_companies, title="Gestion Company")

# Route pour créer un client
@api_emails_blueprint.route('/client/create', methods=['GET', 'POST'])
def create_client():
    if request.method == 'POST':
        from app import socketio
        # Get form data
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        is_company = request.form.get('is_company') == 'True'  # Correct handling for is_company

        # Create new client object
        new_client = ResPartner(name=name, email=email, phone=phone, is_company=is_company)
        if new_client == None:
            db.session.add(new_client)
            db.session.commit()
            socketio.emit("new_partner", {
                "new_partner": new_client.to_dict()
            })

        # Redirect to client list page
        return redirect(url_for('api_emails.clients'))

    # Return the form page
    return render_template('list.html')

# Route pour créer une entreprise
@api_emails_blueprint.route("/create_company", methods=["POST"])
def create_company():
    try:
        from app import socketio
        name = request.form.get("name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        street = request.form.get("street")
        city = request.form.get("city")
        zip_code = request.form.get("zip")
        website = request.form.get("website")
        logo = request.files.get("logo")

        if not name:
            return jsonify({"error": "Le nom de l'entreprise est requis."}), 400

        # Vérifier si l'entreprise existe déjà
        existing_company = ResCompany.query.filter_by(name=name).first()
        if existing_company:
            return jsonify({"error": "Cette entreprise existe déjà."}), 400

        # 🔹 Création et sauvegarde de l'entreprise
        new_company = ResCompany(
            name=name,
            email=email,
            phone=phone,
            street=street,
            city=city,
            zip=zip_code,
            website=website
        )
        if logo:
            new_company.logo = logo.read()  # Stocke en binaire
        current_app.logger.info(new_company)
        db.session.add(new_company)
        db.session.commit()
        if new_company:
            socketio.emit("new_company", {
                "new_company": new_company.to_dict()
            })
            current_app.logger.info(f"✅ Entreprise enregistrée : {new_company.name}")

        return redirect(url_for('api_emails.companies'))

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# Route pour éditer un client
@api_emails_blueprint.route('/client/edit/<int:client_id>', methods=['POST'])
def edit_client(client_id):
    client = ResPartner.query.get_or_404(client_id)
    
    # Récupérer les données du formulaire
    client.name = request.form['name']
    client.email = request.form['email']
    client.phone = request.form['phone']
    client.is_company = request.form.get('is_company') == 'True'  # Convertir la valeur en booléen
    
    db.session.commit()  # Enregistrer les modifications dans la base de données
    return redirect(url_for('api_emails.clients'))

# Route pour éditer une entreprise
@api_emails_blueprint.route('/company/edit/<int:company_id>', methods=['GET', 'POST'])
def edit_company(company_id):
    company = ResCompany.query.get_or_404(company_id)
    try:
        if request.method == 'POST':
            company = ResCompany.query.get(company_id)

            if not company:
                return jsonify({"error": "Entreprise non trouvée"}), 404

            company.name = request.form.get("name")
            company.email = request.form.get("email")
            company.phone = request.form.get("phone")
            company.street = request.form.get("street")
            company.city = request.form.get("city")
            company.zip = request.form.get("zip")
            company.website = request.form.get("website")

            # Gestion du logo
            logo = request.files.get("logo")
            if logo:
                company.logo = logo.read()  # Stocke en binaire

            db.session.commit()
            return redirect(url_for('api_emails.companies'))
        return render_template('list.html', company=company)

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@api_emails_blueprint.route("/company_logo/<int:company_id>")
def get_company_logo(company_id):
    company = ResCompany.query.get(company_id)

    if company and company.logo:
        try:
            # Vérifie si les données sont valides
            if not company.logo:
                return Response("Image vide", status=404, mimetype="text/plain")

            return send_file(io.BytesIO(company.logo), mimetype="image/png")

        except Exception as e:
            return Response(f"Erreur lors de la récupération de l'image: {str(e)}", status=500)

    return Response("Logo non trouvé", status=404, mimetype="text/plain")

# Route pour supprimer un client
@api_emails_blueprint.route('/client/delete/<int:client_id>', methods=['POST'])
def delete_client(client_id):
    client = ResPartner.query.get_or_404(client_id)
    db.session.delete(client)
    db.session.commit()
    return redirect(url_for('api_emails.clients'))

# Route pour supprimer une entreprise
@api_emails_blueprint.route('/company/delete/<int:company_id>', methods=['POST'])
def delete_company(company_id):
    company = ResCompany.query.get_or_404(company_id)
    db.session.delete(company)
    db.session.commit()
    return redirect(url_for('api_emails.companies'))

@api_emails_blueprint.route('/refuse-client/<int:mailId>', methods=['GET'])
@jwt_required()
def refused_email(mailId):
    try:
        refuse = State.refuse()
        email = EmailsState.get_email_state_by_id(mailId)
        if not email:
            return jsonify({"message": "Email non trouvé"}), 404
        current_app.logger.info(f"{email.emails_id} Email {refuse} refusé")

        email = EmailsState.update_state_id(email.emails_id, refuse)

        # Ici, tu devrais enregistrer dans la base de données (SQLAlchemy ou autre ORM)
        current_app.logger.info(f"Email {email} refusé")

        return jsonify({"message": "Client refusé avec succès"}), 200

    except Exception as e:
        print(f"Erreur serveur : {str(e)}")
        return jsonify({"message": {str(e)}}), 500

@api_emails_blueprint.route("/send-refuse-client/<int:mailId>", methods=["POST"])
@jwt_required()
def send_refuse_client(mailId):
    try:
        current_user = get_jwt_identity()    # ✅ Récupérer email et mot de passe du token
        sender_email = current_user["email"]
        sender_password = current_user["password"]
        data = request.json
        # sender_email = data.get("to")
        recipient_email = "mr@phareindustries.com"
        subject = data.get("subject")
        body_text = data.get("message")

        if not recipient_email or not subject or not body_text:
            return jsonify({"message": "Tous les champs sont requis"}), 400

        current_app.logger.info(f"Envoi de mail à : {recipient_email}\nSujet : {subject}\nMessage : {body_text}")
        EmailAnalyze.send_email(sender_email, sender_password, recipient_email, subject, body_text, body_html=None)
        return jsonify({"message": "Email envoyé avec succès"}), 200

    except Exception as e:
        return jsonify({"message": str(e)}), 500
    
@api_emails_blueprint.route('/get_email_info/<int:email_id>', methods=['GET'])
def get_email_info(email_id):
    try:
        # Obtenir la réponse formatée
        flask_response = EmailAnalyze.prompt_info_client_company(email_id)
        payload = json.loads(flask_response.get_data(as_text=True))
        structured_payload = structure_lead_payload_for_odoo(payload, email_id)
        current_app.logger.info("-----------------------------------------")
        current_app.logger.info(structured_payload)
        # ✅ Envoyer au Webhook Make via POST
        # response = requests.post(MAKE_WEBHOOK_URL, json=structured_payload)
        response = requests.post("https://hook.eu2.make.com/p4yh89aav4e3w96863au87kkjqq6smyh", json=structured_payload)
        response.raise_for_status()

        current_app.logger.info(f"✅ Webhook envoyé: {response.status_code}, {response.text}")
        return flask_response

    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"❌ Erreur d'envoi au webhook: {str(e)}")
        return flask_response, 500

    except Exception as e:
        current_app.logger.error(f"❌ Erreur serveur: {str(e)}")
        return jsonify({"error": str(e)}), 500
    
@api_emails_blueprint.route('/get_email_info_devis/<int:email_id>', methods=['GET'])
def get_email_info_webhooks(email_id):
    try:
        # email = Emails.get_by_path(email_url)
        # if not email:
        #     return jsonify({"error": "Email non trouvé pour ce path"}), 404

        flask_response = EmailAnalyze.prompt_info_client_company(email_id)
        payload = json.loads(flask_response.get_data(as_text=True))
        structured_payload = structure_lead_payload_for_odoo(payload, email_id)

        return jsonify(structured_payload), 200

    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"❌ Erreur d'envoi au webhook: {str(e)}")
        return jsonify({"error": "Erreur webhook"}), 500

    except Exception as e:
        current_app.logger.error(f"❌ Erreur serveur: {str(e)}")
        return jsonify({"error": str(e)}), 500

@api_emails_blueprint.route("/save_client_company/<int:email_id>", methods=["GET"])
def save_client_company(email_id):
    try:
        from app import socketio
        current_app.logger.info(f"📩 Traitement de l'email ID : {email_id}")
        
        # 🏢 Récupérer les données de l'email
        res_partner = ResPartner.save_partner_from_json(email_id)
        res_company = ResCompany.save_company_from_json(email_id)

        # ✅ Envoyer les nouvelles données aux clients via WebSocket (si elles existent)
        if res_partner:
            socketio.emit("new_partner", {
                "new_partner": res_partner.to_dict()
            })
            current_app.logger.info(f"✅ Partenaire enregistré : {res_partner.name}")

        if res_company:
            socketio.emit("new_company", {
                "new_company": res_company.to_dict()
            })
            current_app.logger.info(f"✅ Entreprise enregistrée : {res_company.name}")

        # 🔄 Associer le partenaire et l'entreprise (s'ils existent tous les deux)
        if res_partner and res_company:
            pc = PartnerCompany(res_partner.id, res_company.id)
            pc.save()
            current_app.logger.info(f"🔗 Association Partenaire <-> Entreprise créée.")

        return jsonify({
            "message": "Client et entreprise enregistrés avec succès",
            "status": "success"
        }), 200

    except Exception as e:
        current_app.logger.error(f"❌ Erreur lors de la sauvegarde : {e}")
        return jsonify({"error": str(e), "status": "failed"}), 500

@api_emails_blueprint.route("/download_attachment/<filename>")
def download_attachment(filename):
    from app.models.email_attachment import EmailAttachment
    email_id = request.args.get("email")

    attachment = EmailAttachment.exists(email_id, filename)
    if not attachment:
        return Response("Pièce jointe non trouvée", status=404)
    current_app.logger.info(attachment)
    return send_file(
        io.BytesIO(attachment.data),
        mimetype=attachment.content_type,
        as_attachment=True,
        download_name=attachment.filename
    )