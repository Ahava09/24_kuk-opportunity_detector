import imaplib
import email
import os
import re
from app.models.emails import Emails
from app.models.mail_type import MailType
from email.header import decode_header
from datetime import datetime
from email.utils import parsedate_to_datetime, parseaddr
import openai  
from config import OPENAI_API_KEY
from datetime import timedelta
from flask import current_app
import ssl
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

openai.api_key = OPENAI_API_KEY

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
    
    # Fonction pour nettoyer le texte
    @staticmethod
    def clean_text(body):

        # Supprimer tous les liens HTTP/HTTPS
        body = re.sub(r'https?://\S+', '', body)
        # body = '\n'.join([line for line in body.splitlines() if len(line) < 200])

        # Supprimer les espaces multiples
        body = re.sub(r'\s+', ' ', body).strip()
        if body:
            return body.strip().replace("\n", " ").replace("\r", " ")
        return ""

    def generate_gmail_link(self, message_id):
        message_id = message_id.strip("<>")
        return f"https://mail.google.com/mail/u/0/#search/rfc822msgid:{message_id}"
    
    def get_unread_emails_since(self, date_since, date_before, mail_type_id=0):
        self.connect()
        # Vérifier si la date est déjà un objet datetime
        if isinstance(date_since, str):
            date_since = datetime.strptime(date_since, "%d-%b-%Y")  # Format : DD-MMM-YYYY
        
        if isinstance(date_before, str):
            date_before = datetime.strptime(date_before, "%d-%b-%Y")

        # Gérer le cas où date_since est null (On prend date_before - 3 jours)
        if not date_since and date_before:
            date_before = date_before - timedelta(days=3)  # Recherche avant 3 jours de date_before
            date_since = date_before - timedelta(days=365)  # Choisir une date lointaine avant `date_before - 3 jours`
        
        # Gérer le cas où date_before est null (On prend date_since + 3 jours)
        elif date_since and not date_before:
            date_before = date_since + timedelta(days=3)  # Recherche après 3 jours de date_since

        # Convertir les dates au format IMA
        date_since = date_since.strftime("%d-%b-%Y")
        date_before = date_before.strftime("%d-%b-%Y")
    
        
        # app.logger.info(date_since)
        # Recherche des emails entre deux dates
        search_criteria = f'(SINCE "{date_since}" BEFORE "{date_before}")'
        
        status, messages = self.mail.search(None, search_criteria)

        email_ids = messages[0].split()
        emails = []

        for email_id in email_ids:
            # Récupérer l'UID de l'email
            status, msg_data = self.mail.fetch(email_id, "(RFC822)")

            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])

                    # 📩 Extraire le sujet
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding if encoding else "utf-8")
                    # Récupération du champ "From"
                    raw_sender = msg.get("From")

                    # Extraction du nom et de l'adresse email
                    sender_name, sender_email = parseaddr(raw_sender)

                    # Vérifier si le nom est vide et le remplacer par l'email si nécessaire
                    if not sender_name:
                        sender_name = sender_email

                    # 📆 Extraire la date d'envoi
                    date_str = msg.get("Date")
                    receive_at = parsedate_to_datetime(date_str) if date_str else datetime.utcnow()

                    # 📝 Extraire le corps
                    body = self.extract_body(msg)

                    # 🛠️ Définir un chemin vers le mail (exemple : ID du mail)
                    # Générer le lien Gmail
                    
                    message_id = msg["Message-ID"]
                    path = self.generate_gmail_link(message_id)
                    if mail_type_id != 0:
                        type = MailType.select_by_id(int(mail_type_id))
                    else:
                        type = MailType.select_by_type_name("None")
                        if type is None:
                            type = MailType("None")
                            type.save()  # Enregistrer dans la base

                    # ✅ Stocker en base de données
                    new_email = Emails(
                        subject=subject,
                        sender=sender_name,
                        mail=sender_email,
                        body=body,
                        receive_at=receive_at,
                        path=path,
                        percentage=0,
                        mail_type_id=type.id
                    )
                    if mail_type_id == 0 or not type.type_name or type.type_name.strip() == "None":
                        new_email.percentage = 0
                    else:
                        percentage = self.analyze_email_with_chatgpt(new_email, type.type_name)
                        new_email.percentage = percentage

                    emails.append(new_email)
                    
        self.disconnect()

        return emails

    def extract_body(self, msg):
        # Si l'email a plusieurs parties (texte, HTML, etc.)
        # body = ""
        # if msg.is_multipart():
        #     for part in msg.walk():
        #         content_type = part.get_content_type()
        #         content_disposition = str(part.get("Content-Disposition"))
        #         if content_type == "text/plain" and "attachment" not in content_disposition:
        #             body = part.get_payload(decode=True).decode()
        #             break
        # else:
        #     body = msg.get_payload(decode=True).decode()
        # return body

                
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    try:
                        body = part.get_payload(decode=True).decode("utf-8")
                    except (UnicodeDecodeError, AttributeError):
                        body = part.get_payload(decode=True).decode("iso-8859-1")
                    break
        else:
            body = msg.get_payload(decode=True).decode("utf-8")
        body = EmailAnalyze.clean_text(body)
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
        {EmailAnalyze.message_chat(message)}
        
        --- Début de l'email ---
        {email.subject}
        {email.body}
        --- Fin de l'email ---
        """
        # app.logger.info(prompt)

        try:
            print("🤖 Envoi du prompt à ChatGPT...")
            client = openai.Client(api_key=os.getenv("OPENAI_API_KEY") )  
            response = client.chat.completions.create(
                model="gpt-3.5-turbo", # gpt-4o
                temperature=0,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )


            
            answer = response.choices[0].message.content.strip()
            # app.logger.info("🎯 Réponse analysée :", answer)

            email.percentage = answer 
            return email.percentage

        except Exception as e:
            current_app.logger.error(e)
            print("❌ Erreur lors de l'analyse :", e)

    def generate_message_mail(recipient,subject,message):
        current_app.logger.info(message)
        prompt = f"Rédige un email professionnel à {recipient} sur '{subject}'.\n"
        if message:
            prompt += f"Voici une ébauche fournie par l'utilisateur :\n{message}\nAméliore-la et rends-la plus professionnelle."
        
        try:
            print("🤖 Envoi du prompt à ChatGPT...")

            # openai.api_key = os.getenv("OPENAI_API_KEY") 
            client = openai.Client(api_key=os.getenv("OPENAI_API_KEY") )  
            response = client.chat.completions.create(
                model="gpt-3.5-turbo", # gpt-4o
                temperature=0.7,
                messages=[
                    {"role": "system", "content": "Tu es un assistant expert en rédaction d'emails professionnels."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            generated_message = response.choices[0].message.content
            return generated_message
        
        except Exception as e:
            current_app.logger.info(e)
            print("❌ Erreur lors de l'analyse :", e)

    @staticmethod 
    def message_chat(message):
        print("Reformulation du message pour le critère")
        return f"""
        Analyse le contenu de cet email pour déterminer si l'opportunité décrite est une opportunité de {message} pour l'entreprise dans son secteur d'activité.
        Répond uniquement par un nombre entre 0 et 100, représentant le pourcentage d'adéquation avec un type d'opportunité de {message}, que ce soit dans le secteur industriel, maritime ou logistique.
        """

    def send_email(sender_email, sender_password, recipient_email, subject, body_text, body_html=None):
        """
        Envoie un email via le serveur SMTP de Gmail.
        
        :param sender_email: Adresse email de l'expéditeur
        :param sender_password: Mot de passe ou App Password de Gmail
        :param recipient_email: Adresse email du destinataire
        :param subject: Sujet de l'email
        :param body_text: Contenu en texte brut
        :param body_html: Contenu en HTML (optionnel)
        """
        try:
            # 📩 Création du message
            msg = MIMEMultipart("alternative")
            msg["From"] = sender_email
            msg["To"] = recipient_email
            msg["Subject"] = subject

            # Ajouter la version texte
            part1 = MIMEText(body_text, "plain")
            msg.attach(part1)

            # Ajouter la version HTML si disponible
            if body_html:
                part2 = MIMEText(body_html, "html")
                msg.attach(part2)

            # Connexion au serveur SMTP Gmail
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, recipient_email, msg.as_string())

            current_app.logger.info("✅ Email envoyé avec succès à", recipient_email)

        except Exception as e:
            current_app.logger.error("❌ Erreur lors de l'envoi de l'email :", e)

