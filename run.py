from flask import jsonify, request, render_template
from sqlalchemy.exc import SQLAlchemyError
from app.models.email_analyze import EmailAnalyze
from app.models.emails import Emails
from app.models.mail_type import MailType
from app import create_app
from app.database import db
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from config import JWT_SECRET_KEY, JWT_ACCESS_TOKEN_EXPIRES
from flask_socketio import SocketIO
import time

app = create_app()
socketio = SocketIO(app, cors_allowed_origins="*")  # ✅ Permet la communication WebSocket

app.config["JWT_SECRET_KEY"] =   JWT_SECRET_KEY
app.config["JWT_ACCESS_TOKEN_EXPIRES"] =  JWT_ACCESS_TOKEN_EXPIRES
jwt = JWTManager(app)

# ✅ Simulation de la récupération des emails en boucle (à remplacer par ta logique)
# def check_new_emails():
#     while True:
#         time.sleep(10)  # ✅ Vérifier les nouveaux emails toutes les 10 secondes
#         emails = get_new_emails()  # 🔄 Fonction qui récupère les nouveaux emails

#         if emails:
#             print("🟢 Nouveaux emails détectés, envoi via WebSocket...")
#             socketio.emit("new_email", {"emails": emails})  # ✅ Envoi en temps réel au client

# ✅ Lancer la fonction en tâche de fond
# import threading
# email_thread = threading.Thread(target=check_new_emails)
# email_thread.daemon = True
# email_thread.start()



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
            new_email = Emails(
                subject=email_data["subject"],
                sender=email_data["sender"],
                body="Contenu non disponible", 
                receive_at=email_data["receive_at"],
                path=email_data["path"],
                percentage=email_data["percentage"],
                mail_type_id=email_data["type"]
            )
            app.logger.info(f"Emails existant : ---------------------------------------------------------------------")
            db.session.add(new_email)

        db.session.commit()
        return jsonify({"message": "Emails enregistrés avec succès !"}), 200

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
    if not mail_type_id:
        return jsonify({"error": "mail_type_id is required"}), 400
    try:
        mail_type_id = int(mail_type_id)
    except ValueError:
        return jsonify({"error": "mail_type_id must be an integer"}), 400

    email_client = EmailAnalyze(username, password)

    try:
        date_since = "28-Feb-2025"  # Modifier selon besoin
        app.logger.info(email_client)

        emails = email_client.get_unread_emails_since(date_since, mail_type_id)
        new_emails = []  # Liste pour stocker les objets à insérer

        for email in emails:
            try:
                existing_email = email.save()

                if existing_email:
                    # app.logger.info(str(existing_email))
                    new_emails.append(email)
                    continue

            except SQLAlchemyError as e:
                db.session.rollback()
                app.logger.error(f"Erreur SQLAlchemy: {str(e)}")
                return jsonify({"error": "Erreur lors de l'insertion en base"}), 500
            
        emails_json = [e.to_dict() for e in new_emails]
        mails = Emails.get_all_json()
        types = MailType.get_all_json()
        return jsonify({"unread_count": len(emails_json), "emails": emails_json,"emails_count": len(mails), "emails_bdd":mails, "types": types})

    except Exception as e:
        import traceback
        app.logger.error(f"Erreur serveur: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    with app.app_context():  
        db.create_all() 
        app.run(host='0.0.0.0', port=5000, debug=True)
