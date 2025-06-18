import imaplib
import email
import os
import re
import json
from app.models.emails import Emails
from app.models.mail_type import MailType
from app.models.res_partner import ResPartner
from app.models.partner_company import PartnerCompany
from app.models.email_attachment import EmailAttachment
from email.header import decode_header
from datetime import datetime
from email.utils import parsedate_to_datetime, parseaddr
import openai  
from config import OPENAI_API_KEY, ASSISTANT_ID, DATA_STORAGE_PATH, DIRECTORY_LOGO_COMPANY, assistant_id_email
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
import base64

openai.api_key = OPENAI_API_KEY
client = openai.Client(api_key=os.getenv("OPENAI_API_KEY") )  
assistant_id = ASSISTANT_ID
assistant_id_email = assistant_id_email

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
        if isinstance(date_since, str):
            date_since = datetime.strptime(date_since, "%d-%b-%Y")  # Format : DD-MMM-YYYY
        
        if isinstance(date_before, str):
            date_before = datetime.strptime(date_before, "%d-%b-%Y")

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
                    if mail_type_id != 0 or not type.type_name or type.type_name.strip() != "None":
                        p = self.analyze_email_with_chatgpt(new_email, type.type_name)
                        new_email["percentage"] = p

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

    
    def safe_json(value, default=""):
        return value if value is not None else default

    def generate_message_mail(recipient,subject,message):
        # current_app.logger.info(message)
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

    # def analyze_email_with_chatgpt(self, email, message):

    #     prompt = f"""
    #     {EmailAnalyze.message_chat(message)}
        
    #     --- Début de l'email ---
    #     {email["subject"]}
    #     {email["body"]}
    #     --- Fin de l'email ---
    #     """

    #     try:
    #         print("🤖 Envoi du prompt à ChatGPT...")
    #         response = client.chat.completions.create(
    #             model="gpt-3.5-turbo",
    #             temperature=0,
    #             messages=[
    #                 {"role": "user", "content": prompt}
    #             ]
    #         )
            
    #         answer = response.choices[0].message.content.strip()
    #         current_app.logger.info(f"🎯 Pourcentage détecté : {answer}")

    #         return answer

    #     except Exception as e:
    #         current_app.logger.error(e)
    #         print("❌ Erreur lors de l'analyse :", e)

    def analyze_email_with_chatgpt(self, email_dict, message):

        prompt = f"""
    {EmailAnalyze.message_chat(message)}

    --- Début de l'email ---
    Objet : {email_dict['subject']}
    Corps :
    {email_dict['body']}
    --- Fin de l'email ---

    Analyse également les documents joints pour déterminer si c’est une opportunité de type {message}.
    Répond uniquement par un nombre entre 0 et 100.
    """

        try:
            # 1. Créer un thread
            thread = client.beta.threads.create()
            thread_id = thread.id

            # 2. Uploader les fichiers
            file_ids = []
            for att in email_dict.get("attachments", []):
                file_data = io.BytesIO(att["data"])
                res = client.files.create(
                    file=(att["filename"], file_data, att["content_type"]),
                    purpose="assistants"
                )
                file_ids.append(res.id)

                # 3. Ajouter le fichier au thread
                client.beta.threads.messages.create(
                    thread_id=thread_id,
                    role="user",
                    content=f"Fichier joint : {att['filename']}",
                    attachments=[{"file_id": res.id, "tools": [{"type": "file_search"}]}]
                )

            # 4. Ajouter le corps de mail
            client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=prompt
            )

            # 5. Lancer le thread
            run = client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=assistant_id_email
            )

            # 6. Attente de complétion
            for _ in range(30):
                status = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
                if status.status == "completed":
                    break
                time.sleep(2)

            # 7. Récupérer la réponse
            messages = client.beta.threads.messages.list(thread_id=thread_id)
            answer = messages.data[0].content[0].text.value.strip()

            # 8. Extraire le pourcentage
            percentage_match = re.search(r"\b(\d{1,3})\b", answer)
            if percentage_match:
                return int(percentage_match.group(1))
            return 0

        except Exception as e:
            current_app.logger.error(f"❌ Erreur OpenAI : {e}")
            return 0

    
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
                file_ids.append(response.id)  
                
                current_app.logger.error(f"✅ Fichier {attachment.filename} envoyé avec succès, ID: {response.id}")

            except Exception as e:
                current_app.logger.error(f"❌ Erreur lors de l'envoi du fichier {attachment.filename} : {e}")

        return file_ids

    def ensure_storage_exists():
        """Vérifie et crée le dossier et le fichier JSON si nécessaire."""
        directory = os.path.dirname(DATA_STORAGE_PATH)
        
        # 📂 Création du dossier s'il n'existe pas
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            current_app.logger.info(f"📁 Dossier {directory} créé.")

        # 📄 Création du fichier JSON vide `{}` s'il n'existe pas ou est corrompu
        if not os.path.exists(DATA_STORAGE_PATH) or os.stat(DATA_STORAGE_PATH).st_size == 0:
            with open(DATA_STORAGE_PATH, "w", encoding="utf-8") as file:
                json.dump({}, file, indent=4, ensure_ascii=False)  # Initialiser avec `{}` vide
            current_app.logger.info(f"📄 Fichier {DATA_STORAGE_PATH} créé avec contenu vide.")

    def save_email_data(email_id, data):
        """📁 Sauvegarde les données d'un email traité dans un fichier JSON."""
        try:
            EmailAnalyze.ensure_storage_exists()  # ✅ Vérifier que le stockage est prêt

            with open(DATA_STORAGE_PATH, "r", encoding="utf-8") as file:
                email_data = json.load(file)

            email_data[email_id] = data  # Mise à jour des données
            
            with open(DATA_STORAGE_PATH, "w", encoding="utf-8") as file:
                json.dump(email_data, file, indent=4, ensure_ascii=False)

            current_app.logger.info(f"✅ Données sauvegardées pour l'email ID {email_id}")

        except Exception as e:
            current_app.logger.error(f"❌ Erreur lors de la sauvegarde des données : {e}")

    def load_email_data(email_id):
        """📁 Charge les données d'un email s'il a déjà été traité."""
        try:
            EmailAnalyze.ensure_storage_exists()  # ✅ Vérifier que le stockage est prêt
            with open(DATA_STORAGE_PATH, "r", encoding="utf-8") as file:
                email_data = json.load(file)
                email_id_str = str(email_id)  # ✅ Convertir en str
                # current_app.logger.info(f"📂 Vérification de l'email ID {email_id_str}")
                # current_app.logger.info(email_data.get(email_id_str))  # 🔍 Vérification des logs
                return email_data.get(email_id_str)  # ✅ Chercher avec `str`
        except Exception as e:
            current_app.logger.error(f"❌ Erreur lors du chargement des données : {e}")
        return None  # Retourne None si l'email n'a pas été trouvé
    
    def prompt_info_client_company(email_id):
        try:
            # 🚀 Vérifier si les données existent déjà dans le fichier JSON
            current_app.logger.info(f"📂 Vérification des données en cache pour l'email ID {email_id}")
            cached_data = EmailAnalyze.load_email_data(email_id)
            if cached_data:
                current_app.logger.info(f"📂 Données chargées depuis le cache pour l'email ID {email_id}")
                current_app.logger.info(json.dumps(cached_data, default=str))
                return Response(json.dumps(cached_data, default=str, indent=4, ensure_ascii=False), mimetype="application/json")

            # 📩 Récupération de l'email
            email = Emails.query.get(email_id)
            if not email:
                return Response(json.dumps({"error": "Email non trouvé"}, default=str), mimetype="application/json"), 404

            sender_email = email.mail.strip().lower()

            # 🔎 Recherche du client (`ResPartner`) et de son entreprise (`ResCompany`)
            partner = ResPartner.query.filter_by(email=sender_email).first()
            company = PartnerCompany.get_company(partner.id) if partner else None

            # 📎 Récupération des pièces jointes
            attachments = EmailAttachment.query.filter_by(email_id=email.id).all()

            # 🚀 Envoi de toutes les pièces jointes à OpenAI
            file_ids = EmailAnalyze.upload_files_to_openai(attachments)
            extracted_data = EmailAnalyze.extract_info_with_openai(email.subject,email.body, file_ids)

            # 🛠 Vérification et correction des données extraites
            if isinstance(extracted_data, str):
                try:
                    extracted_data = json.loads(extracted_data)
                except json.JSONDecodeError:
                    current_app.logger.error("❌ Erreur JSON : Impossible de parser la réponse OpenAI")
                    extracted_data = {"DEA": {}, "DET": {}}

            demandeur = extracted_data.get("DEA", {}).get("demandeur", {})
            if isinstance(demandeur, str):
                current_app.logger.error(f"⚠️ Erreur : 'demandeur' est une chaîne au lieu d'un dictionnaire : {demandeur}")
                demandeur = {}

            # ✅ Vérification des informations du partenaire
            partner_data = {
                "id": getattr(partner, "id", None),
                "name": getattr(partner, "name", None),
                "email": getattr(partner, "email", None),
                "phone": getattr(partner, "phone", None),
                "is_company": getattr(partner, "is_company", False),
            } if partner else {}

            # ✅ Vérification des informations de l'entreprise
            company_data = {
                "id": getattr(company, "id", None),
                "name": getattr(company, "name", None),
                "phone": getattr(company, "phone", None),
                "email": getattr(company, "email", None),
                "street": getattr(company, "street", None),
                "website": getattr(company, "website", None),
            } if company else {}

            # 📌 Sauvegarde du logo d’entreprise (si disponible)
            logo_base64 = extracted_data["DEA"].get("logo_entreprise_base64", "")
            company_name = extracted_data["DEA"].get("entreprise_demandeuse", "")
            logo_path = EmailAnalyze.save_logo(logo_base64, company_name) if logo_base64 else None
            client_nom = demandeur.get("nom", "")
            client_prenom = demandeur.get("prenom", "")
            client_full_name = f"{client_nom} {client_prenom}".strip() if client_nom or client_prenom else ""
            # 🔹 Construction du dictionnaire structuré
            info = {
                "email_id": email.id,
                "email_date": email.receive_at.strftime("%Y-%m-%d %H:%M:%S"),
                "email_subject": email.subject,
                "email_sender": email.sender,
                "email_address": sender_email,
                "email_body": email.body,
                "already_answered": email.already_answered,

                # ✅ Client (`ResPartner`)
                "client_id": partner_data.get("id", ""),
                "client_name": partner_data.get("name", client_full_name),
                "client_email": partner_data.get("email", demandeur.get("email_address", "")),
                "client_phone": partner_data.get("phone", demandeur.get("telephone", "")),
                "is_company": partner_data.get("is_company", False),

                # ✅ Entreprise (`ResCompany`)
                "company_id": company_data.get("id", ""),
                "company_name": company_data.get("name", extracted_data.get("DEA", {}).get("entreprise_demandeuse", "")),
                "company_phone": company_data.get("phone", extracted_data["DEA"].get("coordonnees_entreprise", {}).get("telephone", "")),
                "company_email": company_data.get("email", extracted_data["DEA"].get("coordonnees_entreprise", {}).get("email", "")),
                "company_street": company_data.get("street", extracted_data["DEA"].get("adresse_entreprise", "")),
                "company_website": company_data.get("website", extracted_data["DEA"].get("coordonnees_entreprise", {}).get("site_web", "")),
                "company_logo": logo_path if logo_path else "",
                
                "path_mail" : email.path if email.path else "",
                "probability" : email.percentage,
                # ✅ DEA & DET
                "DET": extracted_data.get("DET", {}),
                "DEA": extracted_data.get("DEA", {})
            }

            # ✅ Sauvegarde des données dans le fichier JSON
            EmailAnalyze.save_email_data(email_id, info)

            # ✅ Vérification des données avant affichage
            log_safe_info = json.dumps(info, default=str, indent=4, ensure_ascii=False)
            current_app.logger.info(log_safe_info)

            return Response(log_safe_info, mimetype="application/json")

        except Exception as e:
            current_app.logger.error(f"❌ Erreur générale : {e}")
            return Response(json.dumps({"error": str(e)}, default=str), mimetype="application/json"), 500

    def save_logo(logo_base64, company_name):
        """
        Sauvegarde le logo extrait sous forme de fichier image et retourne son chemin d'accès.
        """
        if not logo_base64:
            return None

        try:
            # 🔹 Décode l'image en base64
            image_data = base64.b64decode(logo_base64)
            
            # ✅ Crée le dossier s'il n'existe pas
            os.makedirs(DIRECTORY_LOGO_COMPANY, exist_ok=True)  

            # 🔹 Générer un nom de fichier basé sur le nom de l'entreprise
            safe_company_name = company_name.replace(" ", "_").replace("/", "_")
            logo_path = f"{DIRECTORY_LOGO_COMPANY}/{safe_company_name}.png"

            # 🔹 Écrire l'image décodée en fichier PNG
            with open(logo_path, "wb") as img_file:
                img_file.write(image_data)

            # ✅ Retourner le chemin accessible depuis le frontend
            return f"/{logo_path}"  

        except Exception as e:
            current_app.logger.error(f"❌ Erreur lors de la sauvegarde du logo : {e}")
            return None
       
    def extract_info_with_openai(email_subject, email_body, file_ids):
        """
        Envoie un email et ses fichiers joints à OpenAI Assistant pour extraire les informations détaillées de l'opportunité commerciale.
        """
        prompt = f"""
            Tu es un assistant expert dans l’analyse d’opportunités commerciales industrielles.  
            Tu vas analyser un email et ses **pièces jointes (PDF)** contenant une demande client pour établir un devis.
            --- Début de l'email ---
            {email_subject}
            {email_body}
            --- Fin de l'email ---
            🎯 Ton objectif :  
            1. Extraire **les informations générales (DEA)** relatives au client et à sa demande.  
            2. Extraire **chaque ligne de produit (DET)** demandée, **exactement comme elle est mentionnée** dans le mail ou le fichier PDF, même si elles se ressemblent.

            🟩 **PARTIE 1 – DEA : Données Générales**  
            Extrais les données suivantes si elles sont présentes :
            - Objet de la demande
            - Nom et prénom du demandeur
            - Entreprise demandeuse
            - Adresse entreprise
            - Coordonnées (email, téléphone, site web)
            - Référence de la demande
            - Marée associée
            - Dates limites (réponse, livraison)
            - Contexte
            - Critères de sélection
            - Budget estimé
            - Modalités de paiement
            - Exonération TVA
            - Adresse de livraison

            🟦 **PARTIE 2 – DET : Désignations techniques**  
            🔎 Recherche dans le PDF **toutes les lignes contenant les produits à chiffrer**, sous forme de tableau ou de liste.

            Pour chaque produit, extrait dans une liste `produits` :
            - `designation_client` : texte **exactement** tel que mentionné (pas de reformulation)
            - `reference_fournisseur` : si disponible
            - `specifications_techniques` : dimensions, matériaux, normes
            - `quantite_estimee` : valeur numérique extraite, ou 1 par défaut
            - `contraintes_techniques` : pression/température/compatibilité
            - `certification_requise` : (CE, ISO, etc.)

            📤 **Format STRICTEMENT JSON suivant :**
            ```json
            {{
            "DEA": {{
                "objet_demande": "",
                "demandeur": {{
                "nom": "",
                "prenom": "",
                "email": "",
                "telephone": ""
                }},
                "entreprise_demandeuse": "",
                "adresse_entreprise": "",
                "reference_demande": "",
                "maree_associee": "",
                "date_limite_reponse": "",
                "date_limite_livraison": "",
                "contexte": "",
                "criteres_selection": "",
                "budget_estime": "",
                "delai_execution": "",
                "modalites_paiement": "",
                "exoneration_tva": "",
                "adresse_livraison": "",
                "coordonnees_entreprise": {{
                "email": "",
                "telephone": "",
                "site_web": ""
                }}
            }},
            "DET": {{
                "description_projet": "",
                "lieu_execution": "",
                "fournisseur": "",
                "produits": [
                {{
                    "designation_client": "",
                    "reference_fournisseur": "",
                    "specifications_techniques": "",
                    "quantite_estimee": ""
                }}
                ]
            }}
            }}
        ```
        ❗ Tu ne dois JAMAIS résumer la liste de produits. Aucune coupe, aucun commentaire comme “the same structure applies”, ni “etc.”. Tu dois lister **chaque ligne de produit une par une**, dans son intégralité, sans exception.
        Tu dois générer un JSON **complet**, même s’il est long. Ta sortie doit être 100% conforme à la structure, **sans aucun ajout hors JSON**.

        """
        
        try:  
            thread = openai.beta.threads.create()
            thread_id = thread.id

            # 📎 Ajout des fichiers au thread
            for file_id in file_ids:
                openai.beta.threads.messages.create(
                    thread_id=thread_id,
                    role="user",
                    content="Fichier joint pour analyse.",
                    attachments=[{
                        "file_id": file_id,
                        "tools": [{"type": "file_search"}]
                    }]
                )
                current_app.logger.info(f"📎 Fichier ajouté au thread : {file_id}")

            # 📩 Ajouter le texte de l'email au thread
            openai.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=prompt
            )

            # 🚀 Lancer l'Assistant
            run = openai.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=assistant_id,
                tool_choice="auto"
            )

            # 🔄 Attendre la réponse (Timeout = 60s)
            timeout = 60
            start_time = time.time()
            while time.time() - start_time < timeout:
                run_status = openai.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
                
                if run_status.status == "completed":
                    break
                time.sleep(2)

            # 📥 Récupérer la réponse
            messages = openai.beta.threads.messages.list(thread_id=thread_id)
            assistant_response = messages.data[0].content[0].text.value

            # 🔹 Nettoyer la réponse JSON
            cleaned_response = assistant_response.strip()
            current_app.logger.info(cleaned_response)
            json_match = re.search(r"```json(.*?)```", cleaned_response, re.DOTALL)

            if json_match:
                cleaned_response = json_match.group(1).strip()
            else:
                current_app.logger.warning("⚠️ Aucun bloc JSON détecté dans la réponse OpenAI")
                return {"error": "Réponse non structurée, format JSON absent"}


            # 🔹 Convertir en JSON
            extracted_info = json.loads(cleaned_response)
            
            # current_app.logger.info(f"🔍 Réponse brute OpenAI : {extracted_info}")
            return extracted_info

        except json.JSONDecodeError as e:
            current_app.logger.error(f"❌ Erreur parsing JSON OpenAI : {str(e)}")
            return {"error": "Erreur JSON, impossible de convertir la réponse"}
        except Exception as e:
            current_app.logger.error(f"❌ Erreur OpenAI : {str(e)}")
            return {"error": str(e)}
        
def sanitize_data(data):
    """ Nettoie le JSON pour éviter les erreurs de sérialisation """
    if isinstance(data, list):
        return [sanitize_data(item) for item in data]
    elif isinstance(data, dict):
        return {key: sanitize_data(value) for key, value in data.items()}
    elif isinstance(data, bytes):
        return "<binary data removed>"  # Remplace les données binaires
    elif isinstance(data, str):
        return data.replace("\n", " ").replace("#", "").strip()  # Nettoie les sauts de ligne et #
    return data