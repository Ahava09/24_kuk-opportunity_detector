from flask import Blueprint, current_app, jsonify, render_template, send_file, request, redirect, url_for, Response
from app.models.res_company import ResCompany
from app.models.res_partner import ResPartner
from app.models.emails_state import EmailsState
from app.models.email_analyze import EmailAnalyze
from app.models.partner_company import PartnerCompany
from app.models.state import State
from app.database import db
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
import os
import io
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
        # Get form data
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        is_company = request.form.get('is_company') == 'True'  # Correct handling for is_company

        # Create new client object
        new_client = ResPartner(name=name, email=email, phone=phone, is_company=is_company)
        
        # Add to session and commit to database
        db.session.add(new_client)
        db.session.commit()

        # Redirect to client list page
        return redirect(url_for('api_emails.clients'))

    # Return the form page
    return render_template('list.html')

# Route pour créer une entreprise
@api_emails_blueprint.route("/create_company", methods=["POST"])
def create_company():
    try:
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

        # 📁 Vérifier et créer le dossier si nécessaire
        # if not os.path.exists(UPLOAD_FOLDER):
        #     os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        # 📸 Sauvegarde du fichier et stockage du nom
        # logo_filename = None
        # if logo and allowed_file(logo.filename):
        #     filename = secure_filename(logo.filename)
        #     logo_path = os.path.join(UPLOAD_FOLDER, filename)
        #     logo.save(logo_path)  # Sauvegarde du fichier
        #     logo_filename = filename  # Stocke seulement le nom du fichier

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
    json = EmailAnalyze.prompt_info_client_company(email_id)
    current_app.logger.info(json)
    return json

@api_emails_blueprint.route("/save_client_company", methods=["POST"])
def save_client_company():
    data = request.json

    try:
        email_id = data.get("email_id")
        client_name = data.get("client_name")
        client_email = data.get("client_email")
        client_phone = data.get("client_phone")
        company_name = data.get("company_name")
        company_street = data.get("company_street")
        company_website = data.get("company_website")

        # Vérifier si le client existe déjà
        partner = ResPartner.query.filter_by(email=client_email).first()
        if not partner:
            partner = ResPartner(
                name=client_name,
                email=client_email,
                phone=client_phone,
                is_company=False
            )
            partner.save()

        # Vérifier si l'entreprise existe déjà
        company = ResCompany.query.filter_by(name=company_name).first()
        if not company and company_name:
            company = ResCompany(
                name=company_name,
                street=company_street,
                website=company_website
            )
            company.save()
            pc = PartnerCompany(partner.id, company.id)
            pc.save
        if email_id:
            accept = State.is_partner()
            email = EmailsState.update_state_id(email_id, accept)
        return jsonify({"message": "Client et entreprise enregistrés avec succès", "status": "success"}), 200

    except Exception as e:
        return jsonify({"error": str(e), "status": "failed"}), 500


# @api_emails_blueprint.route("/emails", methods=["GET"])
# def get_emails():
#     try:

#         with db.session.begin():
#             emails = Emails.query.all()
            
#             if not emails:
#                 return jsonify({"message": "No emails found"}), 404
            
#             return jsonify([{
#                 "id": email.id,
#                 "subject": email.subject,
#                 "receive_date": email.receive_at.strftime("%Y-%m-%d %H:%M:%S"),
#                 "path": email.path,
#                 "is_negoce": email.is_negoce
#             } for email in emails])
        
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

# @api_emails_blueprint.route("/searchCriteria", methods=["GET"])
# def search_emails():
    # search_term = request.args.get("criterion", "").strip()

    # if not search_term:
    #     render_template("email.html")

    # matching_emails = Email.query.filter(
    #     (Emails.subject.ilike(f"%{search_term}%")) |
    #     (Emails.body.ilike(f"%{search_term}%"))|
    #     (Emails.sender.ilike(f"%{search_term}%"))|
    #     (cast(Emails.receive_at, String).ilike(f"%{search_term}%"))
    # ).all()
    # print(search_term)

    # if not matching_emails:
    #     return jsonify({"error": "Aucun email trouvé"}), 404

    # emails_json = [{
    #     "id": email.id,
    #     "subject": email.subject,
    #     "from": email.sender,
    #     "body": email.body,
    #     "receive_at": email.receive_at.strftime("%Y-%m-%d %H:%M:%S"),
    #     "is_negoce": email.is_negoce
    # } for email in matching_emails]

    # return jsonify({"emails": emails_json, "count": len(emails_json)})