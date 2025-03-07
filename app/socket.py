from app import socketio
from flask import request
from flask_jwt_extended import decode_token
from flask_socketio import emit
from app.models.email_analyze import EmailAnalyze
import threading
import time
from imapclient import IMAPClient
from flask_socketio import emit

# app = create_app()
@socketio.on("connect")
def handle_connect():
    print("Client connecté")

@socketio.on("disconnect")
def handle_disconnect():
    print("Client déconnecté")

def emit_new_email(email):
    print("ECOUTE")
    socketio.emit("new_email", email)
    
def emit_new_email_gmail(email):
    socketio.emit("new_email_gmail", email)

# @socketio.on("connect")
# def handle_connect():
#     """Gère la connexion au client WebSocket."""
#     print("✅ Client WebSocket connecté.")
#     token = request.args.get("token")
#     print(f"🔍 Token reçu: {token}")

#     if not token:
#         print("🚨 Connexion refusée : JWT manquant.")
#         return False

#     try:
#         token = token.replace("Bearer ", "")
#         user = decode_token(token)["sub"]
#         print(f"✅ Utilisateur authentifié : {user['email']}")

#         request.user = user
#         emit("listening_started", {"message": "Écoute des emails activée."})
#     except Exception as e:
#         print(f"🚨 JWT invalide : {e}")
#         return False

# @socketio.on("start_listening")
# def start_listening():
#     """Démarre l'écoute des emails."""
#     print("📡 start_listening reçu du client !")

#     user = getattr(request, "user", None)
#     if user:
#         print(f"🟢 Démarrage de l'écoute pour {user['email']}")
#         email_client = EmailAnalyze(user["email"], user["password"])

#         threading.Thread(target=listen_email, args=(email_client,), daemon=True).start()
#         emit("listening_started", {"message": "Notification activée"})
#     else:
#         print("🚨 Erreur: utilisateur non authentifié.")
#         emit("error", {"message": "Utilisateur non authentifié"})

# def listen_email(email_client):
#     """Écoute les nouveaux emails avec une combinaison de IMAP IDLE et vérification manuelle."""
#     try:
#         print(f"📩 Connexion à {email_client.server} avec {email_client.username}")

#         with IMAPClient(email_client.server) as client:
#             client.login(email_client.username, email_client.password)
#             print("✅ Connexion IMAP réussie !")

#             client.select_folder("INBOX")
#             while True:
#                 print("⌛ Activation de IDLE pour l'écoute des nouveaux emails...")
#                 client.idle()
#                 responses = client.idle_check(timeout=60)

#                 print(f"🔍 Réponse IMAP IDLE: {responses}")

#                 client.idle_done()

#                 # 🔥 Si pas de réponse IMAP, on force une recherche des nouveaux emails toutes les 10s
#                 if not responses:
#                     unseen = client.search("UNSEEN")
#                     print(f"🔍 Vérification manuelle : {len(unseen)} emails non lus")

#                 if unseen:
#                     emails_data = []
#                     for email_id in unseen:
#                         email_data = client.fetch(email_id, ["RFC822"])
#                         emails_data.append(email_data)

#                     print("📤 Envoi des nouveaux emails via WebSocket...")
#                     socketio.emit("new_email_gmail", {"emails": emails_data})

#                 time.sleep(10)  # Vérification toutes les 10 secondes

#     except Exception as e:
#         print(f"🚨 Erreur IMAP: {e}")
#         time.sleep(60)
