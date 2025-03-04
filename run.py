from flask import jsonify, request, render_template
from sqlalchemy.exc import SQLAlchemyError
from app.models.email_analyze import EmailAnalyze
from app.models.emails_partner import EmailsPartner
from app.models.emails import Emails
from app.models.state import State
from app.models.emails_state import EmailsState
from app.models.mail_type import MailType
from app import create_app
from app.database import db
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from config import JWT_SECRET_KEY, JWT_ACCESS_TOKEN_EXPIRES
from flask_socketio import SocketIO
from datetime import datetime

app = create_app()
socketio = SocketIO(app, cors_allowed_origins="*")  # ✅ Permet la communication WebSocket

app.config["JWT_SECRET_KEY"] =   JWT_SECRET_KEY
app.config["JWT_ACCESS_TOKEN_EXPIRES"] =  JWT_ACCESS_TOKEN_EXPIRES
jwt = JWTManager(app)

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
        import traceback
        app.logger.error(f"Erreur de connexion: {str(e)}")
        traceback.print_exc()

        return jsonify({"error": "Échec de connexion, vérifiez vos identifiants "}), 401

@app.route('/email')
def dashboard():
    return render_template("email.html")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/save_emails", methods=["POST"])
@jwt_required()
def save_emails():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "Aucune donnée reçue"}), 400
        
        # Exemple de traitement
        emails = data.get("emails", [])
        for email_data in emails:
            percentage =  email_data["percentage"] if email_data["percentage"] is not None else 0
            mail_type = MailType.select_by_type_name(email_data["type"]) 
            new_email = Emails(
                subject=email_data["subject"],
                sender=email_data["sender"],
                body=email_data["body"],
                receive_at=email_data["receive_at"],
                path=email_data["path"],
                percentage=percentage,
                mail_type_id=mail_type.id
            )

            try:
                new_email = new_email.save()
            except Exception as e:
                app.logger.error(f"Erreur lors de la sauvegarde : {str(e)}")

            partner = new_email.verify_partner()
            if partner == None :
                app.logger.info(f" --------------------------- {partner}")
                
                try:
                    state_id = State.default()
                    if state_id is None:
                        app.logger.error("Erreur : État par défaut non inséré ou non trouvé.")
                        return jsonify({"message": "Erreur lors de la récupération de l'état par défaut."}), 500
                    emails_state = EmailsState(new_email.id, state_id)
                    emails_state.save()
                    app.logger.info(f"Email avec ID {new_email.id} et état ID {state_id} inséré avec succès.")
                except Exception as e:
                    app.logger.error(f"Erreur lors de la sauvegarde de l'état : {str(e)}")
                    return jsonify({"message": "Erreur lors de la sauvegarde de l'état."}), 500


                return jsonify({"message": f"L'expéditeur {new_email.sender} n'est pas un client existant."}), 500
            else :
                emailsPartner = EmailsPartner(partner.id, new_email.id)
                
                return jsonify({"message": f"Opportunité bien enregistrée {emailsPartner.partner_id}"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route("/get_emails", methods=["GET"])
@jwt_required()
def get_emails():
    current_user = get_jwt_identity()    # ✅ Récupérer email et mot de passe du token
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

    try:
        if date_since:
            date_since = datetime.strptime(date_since, "%Y-%m-%d")
        if date_before:
            date_before = datetime.strptime(date_before, "%Y-%m-%d")
        emails = email_client.get_unread_emails_since(date_since, date_before, mail_type_id)
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
        mails = EmailsState.get_all_json()
        types = MailType.get_all_json()
        state = State.get_all_json()
        app.logger.info(f"-********************* : {len(emails_json)}")

        return jsonify({"unread_count": len(emails_json), "emails": emails_json,"emails_count": len(mails), "emails_bdd":mails, "types": types, "state": state})

    except Exception as e:
        import traceback
        app.logger.error(f"Erreur serveur: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    with app.app_context():  
        db.create_all() 
        app.run(host='0.0.0.0', port=5000, debug=True)
