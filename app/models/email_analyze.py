import imaplib
import email
import os
import re
import json
from app.models.emails import Emails
from app.models.mail_type import MailType
from app.models.res_partner import ResPartner
from app.models.res_company import ResCompany
from app.models.partner_company import PartnerCompany
from app.models.email_attachment import EmailAttachment
from email.header import decode_header
from datetime import datetime
from email.utils import parsedate_to_datetime, parseaddr
import openai  
from config import OPENAI_API_KEY
from datetime import timedelta
from flask import current_app , Response
import ssl
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import json
import re
import io
import openai
import re
import time

openai.api_key = OPENAI_API_KEY
client = openai.Client(api_key=os.getenv("OPENAI_API_KEY") )  

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
                    percentage = 0
                    if mail_type_id != 0 or not type.type_name or type.type_name.strip() != "None":
                        p = self.analyze_email_with_chatgpt(new_email, type.type_name)
                        percentage = p
                    
                    attachments = self.extract_attachments(msg) 
                    new_email = {
                        "subject" : subject,
                        "sender" : sender_name,
                        "mail" : sender_email,
                        "body" : body,
                        "receive_at" : receive_at,
                        "path" : path,
                        "percentage" : percentage,
                        "mail_type_id" : type.id,
                        "attachments": attachments
                    }

                    emails.append(new_email)
                    
        self.disconnect()

        return emails

    def extract_body(self, msg):
                
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
        """
        Extrait les pièces jointes d'un email et les retourne sous forme d'objets en mémoire.
        """
        attachments = []
        for part in msg.walk():
            content_disposition = str(part.get("Content-Disposition"))
            if "attachment" in content_disposition:
                filename = part.get_filename()
                if filename:
                    file_data = part.get_payload(decode=True)
                    content_type = part.get_content_type()
                    attachments.append({
                        "filename": filename,
                        "content_type": content_type,
                        "data": file_data  # Binaire du fichier
                    })
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
        Analyse le contenu de cet email pour déterminer c'est une opportunité de {message}.
        Répond uniquement par un nombre entre 0 et 100.
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

    def upload_files_to_openai(attachments):
        """
        Envoie plusieurs fichiers à OpenAI et retourne une liste d'IDs de fichiers.

        :param attachments: Liste d'objets EmailAttachment.
        :return: Liste des IDs des fichiers téléchargés.
        """
        file_ids = []
        
        for attachment in attachments:
            try:
                file_data = io.BytesIO(attachment.data)  # Convertir en fichier binaire
                
                response = openai.files.create(
                    file=("attachment.pdf", file_data, attachment.content_type),  # 🔹 Correction ici
                    purpose="assistants"
                )
                file_ids.append(response.id)  # ✅ Correction ici
                
                current_app.logger.error(f"✅ Fichier {attachment.filename} envoyé avec succès, ID: {response.id}")

            except Exception as e:
                current_app.logger.error(f"❌ Erreur lors de l'envoi du fichier {attachment.filename} : {e}")

        return file_ids

    def extract_info_with_openai(email_body, file_ids): 
        """
        Envoie un email et ses fichiers joints à OpenAI Assistant pour extraire les DET et DAE.
        """
        prompt = f"""
            📩 **Email reçu :**  
            {email_body}

            🚀 Analyse ce message et les fichiers joints pour extraire :
            - **DET (Détails Éléments et Techniques)** → spécifications techniques, équipements demandés, contraintes.
            - **DAE (Détails Initiaux de la Demande)** → nature de la demande, date limite, critères de sélection.

            Répond STRICTEMENT en JSON :
            ```json
            {{
                "DET": {{
                    "description_projet": "",
                    "elements_techniques": "",
                    "specifications": "",
                    "materiaux_equipements": "",
                    "normes_reglementations": "",
                    "contraintes_techniques": "",
                    "quantite_estimee": "",
                    "lieu_execution": ""
                }},
                "DAE": {{
                    "demande_initiale": "",
                    "demandeur": "",
                    "entreprise_demandeuse": "",
                    "contact_demandeur": {{
                        "telephone": "",
                        "email": ""
                    }},
                    "date_limite_reponse": "",
                    "contexte": "",
                    "criteres_selection": "",
                    "budget_estime": "",
                    "delai_execution": "",
                    "modalites_paiement": ""
                }}
            }}
            ```
        """
        try:
            assistant_id = "asst_Tlud1UfX5yxgoAbHbG75L71P"  
            thread = openai.beta.threads.create()
            thread_id = thread.id

            # 📎 Étape 1 : Ajouter les fichiers AU THREAD
            for file_id in file_ids:
                openai.beta.threads.messages.create(
                    thread_id=thread_id,
                    role="user",
                    content=f"Fichier joint pour analyse : {file_id}",
                    attachments=[{"file_id": file_id,
                    "tools": [{"type": "file_search"}]}]
                )
                current_app.logger.info(f"📎 Fichier ajouté au thread : {file_id}")

            # 📩 Étape 2 : Ajouter l'email au thread (sans fichier)
            openai.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=prompt
            )

            # 🚀 Étape 3 : Lancer l'Assistant (SANS file_ids ici)
            run = openai.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=assistant_id
            )

            # 🔄 Étape 4 : Attendre la réponse (Timeout = 60s)
            timeout = 60
            start_time = time.time()
            while time.time() - start_time < timeout:
                run_status = openai.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
                if run_status.status == "completed":
                    break
                time.sleep(2)

            # 📥 Étape 5 : Récupérer la réponse
            messages = openai.beta.threads.messages.list(thread_id=thread_id)
            assistant_response = messages.data[0].content[0].text.value

            # 📌 Vérifier la réponse avant parsing
            current_app.logger.info(f"🔍 Réponse brute OpenAI : {assistant_response}")

            # 🔹 Étape 1 : Nettoyer le formatage ` ```json ... ``` `
            cleaned_response = re.sub(r"```json|```", "", assistant_response).strip()

            # 🔹 Étape 2 : Convertir en JSON
            extracted_info = json.loads(cleaned_response)

            # 🔹 Étape 3 : Vérifier les clés
            det_data = extracted_info.get("DET", {})
            dae_data = extracted_info.get("DAE", {})

            return {"DET": det_data, "DAE": dae_data}

        except json.JSONDecodeError as e:
            current_app.logger.error(f"❌ Erreur parsing JSON OpenAI : {str(e)}")
            return {"error": "Erreur JSON"}
        except Exception as e:
            current_app.logger.error(f"❌ Erreur OpenAI : {str(e)}")
            return {"error": str(e)}

    def prompt_info_client_company(email_id):
        """
        Récupère les informations d'un email et complète les données avec OpenAI si nécessaire.

        :param email_id: ID de l'email dans la base de données
        :return: Un JSON structuré avec toutes les informations du client et de l'email.
        """

        # 📩 Récupération de l'email
        email = Emails.query.get(email_id)
        if not email:
            return {"error": "Email non trouvé"}
        sender_email = email.mail.strip().lower()

        # 🔎 Recherche du client (`ResPartner`) et de son entreprise (`ResCompany`)
        partner = ResPartner.query.filter_by(email=sender_email).first()
        company = PartnerCompany.get_company(partner.id) if partner else None

    # 📎 Récupération des pièces jointes
        attachments = EmailAttachment.query.filter_by(email_id=email.id).all()

        # 🚀 Envoi de toutes les pièces jointes à OpenAI
        file_ids = EmailAnalyze.upload_files_to_openai(attachments)

        # 🛠️ Extraction des DET et DAE via OpenAI
        extracted_data = EmailAnalyze.extract_info_with_openai(email.body, file_ids)
        current_app.logger.info("🔍 Infos OpenAI récupérées :", extracted_data)

        # 🔹 Construction du dictionnaire structuré
        try:
            info = {
                "email_id": email.id,
                "email_date": email.receive_at.strftime("%Y-%m-%d %H:%M:%S"),
                "email_subject": email.subject,
                "email_sender": email.sender,
                "email_address": sender_email,
                "email_body": email.body,
                "already_answered": email.already_answered,
                "type_name": email.type_name,

                # 🔹 Informations du client (`ResPartner`)
                "client_id": partner.id if partner else None,
                "client_name": partner.name if partner else None,
                "client_phone": partner.phone if partner else None,
                "is_company": partner.is_company if partner else None,

                # 🔹 Informations de l'entreprise (`ResCompany`)
                "company_id": company.id if company else None,
                "company_name": company.name if company else None,
                "company_phone": company.phone if company else None,
                "company_email": company.email if company else None,
                "company_street": company.street if company else None,
                "company_website": company.website if company else None,

                # 🛠️ DET & DAE récupérés depuis OpenAI
                "DET": extracted_data["DET"],
                "DAE": extracted_data["DAE"]
            }

            return Response(json.dumps(info, default=str), mimetype="application/json")

        except Exception as e:
            current_app.logger.error("❌ Erreur dans la récupération des données :", e)
            return jsonify({"error": str(e)})


    # def extract_info_company_with_openai(email_body):
    #     """
    #     Utilise OpenAI pour extraire les informations d'un email.
        
    #     :param email_body: Le texte brut du mail à analyser.
    #     :return: Dictionnaire des informations extraites.
    #     """
    #     prompt = f"""
    #     Analyse ce mail et extrait les informations suivantes sous forme de JSON :
    #     - Nom et prénom du contact
    #     - Adresse email
    #     - Numéro de téléphone
    #     - Nom de l'entreprise (si disponible)
    #     - Adresse de l'entreprise (si disponible)
    #     - Site web de l'entreprise (si mentionné)

    #     Mail :
    #     {email_body}

    #     Répond STRICTEMENT en JSON, sans texte supplémentaire :
    #     ```json
    #     {{
    #     "nom": "",
    #     "prenom": "",
    #     "email": "",
    #     "telephone": "",
    #     "entreprise": "",
    #     "adresse": "",
    #     "site_web": ""
    #     }}
    #     ```
    #     """
    #     response = openai.chat.completions.create(
    #         model="gpt-3.5-turbo", # gpt-4o
    #         messages=[{"role": "system", "content": "Tu es un assistant qui extrait des informations d'email."},
    #                 {"role": "user", "content": prompt}]
    #     )
    #     try:
            
    #         raw_content = response.choices[0].message.content

    #         # 🛠 Nettoyer le JSON (supprimer les ```json et ``` autour)
    #         cleaned_json = re.sub(r'```json|```', '', raw_content).strip()

    #         # 📌 Convertir la chaîne JSON en dictionnaire
    #         extracted_info = json.loads(cleaned_json)  

    #         return extracted_info
        
    #     except json.JSONDecodeError as e:
    #         current_app.logger.error(e)
    #         return {"error": f"Erreur JSON : {str(e)}"}
    #     except Exception as e:
    #         current_app.logger.error(e)
    #         return {"error": f"Erreur d'extraction : {str(e)}"}

    # def prompt_info_client_company(email_id):
    #     """
    #     Récupère les informations d'un email et complète les données avec OpenAI si nécessaire.

    #     :param email_id: ID de l'email dans la base de données
    #     :return: Un JSON structuré avec toutes les informations du client et de l'email.
    #     """

    #     # Récupération de l'email
    #     email = Emails.query.get(email_id)
    #     if not email:
    #         return {"error": "Email non trouvé"}
    #     sender_email = email.mail.strip().lower()

    #     # Recherche du client (`ResPartner`) et de son entreprise (`ResCompany`)
    #     partner = ResPartner.query.filter_by(email=sender_email).first()
    #     company = PartnerCompany.get_company(partner.id) if partner else None
    #     current_app.logger.info(company)
    #     if partner:
    #         extracted_data = {}  # ✅ Aucune récupération via OpenAI si toutes les infos existent
    #     else:
    #         extracted_data = EmailAnalyze.extract_info_with_openai(email.body)  # 🔹 Appel OpenAI uniquement si nécessaire

    #     current_app.logger.info("🔍 Infos OpenAI récupérées :", extracted_data)

    #     # 🔹 Construction du dictionnaire structuré
    #     try:
    #         info = {
    #             "email_id": email.id,
    #             "email_date": email.receive_at.strftime("%Y-%m-%d %H:%M:%S"),
    #             "email_subject": email.subject,
    #             "email_sender": email.sender,
    #             "email_address": sender_email,
    #             "email_body": email.body,
    #             "already_answered": email.already_answered,
    #             "type_name": email.type_name,

    #             # 🔹 Informations du client (`ResPartner`)
    #             "client_id": partner.id if partner else None,
    #             "client_name": partner.name if partner else extracted_data.get("nom"),
    #             "client_phone": partner.phone if partner else extracted_data.get("telephone"),
    #             "is_company": partner.is_company if partner else None,

    #             # 🔹 Informations de l'entreprise (`ResCompany`)
    #             "company_id": company.id if company else None,
    #             "company_name": company.name if company else extracted_data.get("entreprise"),
    #             "company_phone": company.phone if company else None,
    #             "company_email": company.email if company else None,
    #             "company_street": company.street if company else extracted_data.get("adresse"),
    #             "company_city": company.city if company else None,
    #             "company_zip": company.zip if company else None,
    #             "company_website": company.website if company else extracted_data.get("site_web"),
    #         }

    #         # ✅ Retourne un JSON propre
    #         return Response(json.dumps(info, default=str), mimetype="application/json")

    #     except Exception as e:
    #         current_app.logger.error("❌ Erreur dans la récupération des données :", e)
    #         return jsonify({"error": str(e)})
