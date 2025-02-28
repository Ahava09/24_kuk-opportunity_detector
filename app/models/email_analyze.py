import imaplib
import email
import os
from app.models.emails import Emails
from app.models.mail_type import MailType
from email.header import decode_header
from datetime import datetime
from email.utils import parsedate_to_datetime, parseaddr
from app import create_app
import openai  
from config import OPENAI_API_KEY

openai.api_key = OPENAI_API_KEY
app = create_app()

class EmailAnalyze:
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
    

    def generate_gmail_link(self, email_uid):
        """Génère un lien direct vers l'email dans Gmail Web."""
        return f"https://mail.google.com/mail/u/0/#inbox/{email_uid}"

    def get_unread_emails_since(self, date_since="01-Jan-2025", mail_type_id=6):
        self.connect()
        
        status, messages = self.mail.search(None, f'(SINCE "{date_since}")')

        email_ids = messages[0].split()
        emails = []

        for email_id in email_ids:
            # Récupérer l'UID de l'email
            status, uid_data = self.mail.fetch(email_id, "(UID)")
            email_uid = uid_data[0].decode().split()[-1]  # Extraction de l'UID
            status, msg_data = self.mail.fetch(email_id, "(RFC822)")

            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])

                    # 📩 Extraire le sujet
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding if encoding else "utf-8")

                    # 📤 Extraire l'expéditeur
                    # sender = msg.get("From")
                    sender = parseaddr(msg.get("From"))[1]

                    # 📆 Extraire la date d'envoi
                    date_str = msg.get("Date")
                    receive_at = parsedate_to_datetime(date_str) if date_str else datetime.utcnow()

                    # 📝 Extraire le corps
                    body = self.extract_body(msg)

                    # 🛠️ Définir un chemin vers le mail (exemple : ID du mail)
                    # Générer le lien Gmail
                    path = self.generate_gmail_link(email_uid)

                    # ✅ Stocker en base de données
                    new_email = Emails(
                        subject=subject,
                        sender=sender,
                        body=body,
                        receive_at=receive_at,
                        path=path,
                        percentage=0, 
                        mail_type_id=mail_type_id
                    )
                    type = MailType.select_by_id(int(mail_type_id))
                    percentage = self.analyze_email_with_chatgpt(new_email, type.type_name)
                    new_email.percentage = percentage

                    emails.append(new_email)
                    
        self.disconnect()

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

    

    def analyze_email_with_chatgpt(self, email, message):

        prompt = f"""
        {Emails.message_chat(message)}
        
        --- Début de l'email ---
        Sujet : {email.subject}
        Contenu : {email.body}
        --- Fin de l'email ---
        """

        try:
            print("🤖 Envoi du prompt à ChatGPT...")

            # openai.api_key = os.getenv("OPENAI_API_KEY") 
            client = openai.Client(api_key=os.getenv("OPENAI_API_KEY") )  # Nouvelle façon d'initialiser le client

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                store=True,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            
            answer = response.choices[0].message.content.strip()
            print("🎯 Réponse analysée :", answer)

            email.percentage = answer 
            return email.percentage

        except Exception as e:
            app.logger.info(e)
            print("❌ Erreur lors de l'analyse :", e)


    