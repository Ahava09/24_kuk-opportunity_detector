import imaplib
import email
import os
from email.header import decode_header
import openai  
from config import OPENAI_API_KEY
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from email.utils import parsedate_to_datetime
from app.database import db

openai.api_key = OPENAI_API_KEY

class Email(db.Model):
    __tablename__ = "emails"

    id = Column(Integer, primary_key=True, autoincrement=True)
    subject = Column(String(255), nullable=False)
    sender = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    receive_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    path = db.Column(db.String(100))
    is_negoce = Column(Boolean, default=False)

    def __init__(self, subject, sender, body,path , receive_at, is_negoce=False):
        self.subject = subject
        self.sender = sender
        self.body = body
        self.is_negoce = is_negoce
        self.path = path
        self.receive_at = receive_at

    @classmethod
    def exists(cls, subject, sender, receive_at):
        # Vérifier si un email avec les mêmes attributs existe déjà dans la base
        existing_email = cls.query.filter_by(subject=subject, sender=sender, receive_at=receive_at).first()
        return existing_email is not None  # Retourne True si l'email existe, sinon False

    def save(self):
        # Vérifier si l'email existe déjà avant de l'enregistrer
        if not Email.exists(self.subject, self.sender, self.receive_at):
            db.session.add(self)
            db.session.commit()
            return True
        return False

    def __repr__(self):
        return f"<Email id={self.id}, subject={self.subject}, sender={self.sender}>"
    
    @staticmethod 
    def message_chat(message):
        print("Reformulation du message pour le critère")
        return f"""
        Analyse le contenu de cet email pour déterminer s'il concerne {message}.

        Ta réponse doit être uniquement "OUI" ou "NON".
        """


    def analyze_email_with_chatgpt(self, message):
        print("🔍 Début de l'analyse de l'email")

        prompt = f"""
        {Email.message_chat(message)}
        
        --- Début de l'email ---
        Sujet : {self.subject}
        Expéditeur : {self.sender}
        Contenu : {self.body}
        --- Fin de l'email ---
        """

        try:
            print("🤖 Envoi du prompt à ChatGPT...")

            openai.api_key = os.getenv("OPENAI_API_KEY")  # Clé API stockée dans .env
            response = openai.completions.create(
                model="gpt-3.5-turbo",  # Spécifiez le modèle GPT-4
                prompt=prompt,  # Le prompt à envoyer au modèle
                max_tokens=50,  # Limite de la réponse
                temperature=0    # Température à 0 pour une réponse déterministe
            )

            answer = response['choices'][0]['message']['content'].strip()
            print("🎯 Réponse analysée :", answer)

            self.is_negoce = answer == "OUI"
            return self.is_negoce

        except Exception as e:
            print("❌ Erreur lors de l'analyse :", e)
            return False


class EmailClient:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.server = "imap.gmail.com"
        self.mail = None

    def connect(self):
        self.mail = imaplib.IMAP4_SSL(self.server)
        self.mail.login(self.username, self.password)
        self.mail.select("inbox")

    def disconnect(self):
        if self.mail:
            self.mail.close()
            self.mail.logout()

    def get_unread_emails_since(self, date_since="01-Jan-2025"):
        status, messages = self.mail.search(None, f'(SINCE "{date_since}")')

        email_ids = messages[0].split()
        emails = []

        # Lire les emails non lus
        for email_id in email_ids:
            status, msg_data = self.mail.fetch(email_id, "(RFC822)")

            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])

                    # 📩 Extraire le sujet
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding if encoding else "utf-8")

                    # 📤 Extraire l'expéditeur
                    sender = msg.get("From")

                    # 📆 Extraire la date d'envoi
                    date_str = msg.get("Date")
                    receive_at = parsedate_to_datetime(date_str) if date_str else datetime.utcnow()

                    # 📝 Extraire le corps
                    body = self.extract_body(msg)

                    # 🛠️ Définir un chemin vers le mail (exemple : ID du mail)
                    path = f"/emails/{email_id}"

                    # ✅ Stocker en base de données
                    new_email = Email(
                        subject=subject,
                        sender=sender,
                        body=body,
                        receive_at=receive_at,
                        path=path,
                        is_negoce=False
                    )
                    emails.append(new_email)


            # for response_part in msg_data:
            #     if isinstance(response_part, tuple):
            #         msg = email.message_from_bytes(response_part[1])

            #         subject, encoding = decode_header(msg["Subject"])[0]
            #         if isinstance(subject, bytes):
            #             subject = subject.decode(encoding if encoding else "utf-8")

            #         sender = msg.get("From")
            #         body = self.extract_body(msg)
            #         # attachments = self.extract_attachments(msg)
            #         # objt_email = Email(subject, sender, body, attachments)
            #         objt_email = Email(subject, sender, body)
            #         # is_negoce = objt_email.analyze_email_with_chatgpt()
            #         # if is_negoce:
            #         #     objt_email.is_negoce = True
            #         emails.append(objt_email)

        return emails

    def extract_body(self, msg):
        # Si l'email a plusieurs parties (texte, HTML, etc.)
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                if content_type == "text/plain" and "attachment" not in content_disposition:
                    body = part.get_payload(decode=True).decode()
                    break
        else:
            body = msg.get_payload(decode=True).decode()
        return body

    def extract_attachments(self, msg):
        attachments = []
        for part in msg.walk():
            content_disposition = str(part.get("Content-Disposition"))
            if "attachment" in content_disposition:
                filename = part.get_filename()
                if filename:
                    if not os.path.exists("attachments"):
                        os.makedirs("attachments")
                    filepath = os.path.join("attachments", filename)
                    with open(filepath, "wb") as f:
                        f.write(part.get_payload(decode=True))
                    attachments.append(filepath)
        return attachments

    