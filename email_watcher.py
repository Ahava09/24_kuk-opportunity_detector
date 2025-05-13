from imapclient import IMAPClient
import email
from email.header import decode_header
from flask import current_app
from datetime import datetime
from app.models.emails import Emails
from app.database import db
from app.models.email_analyze import EmailAnalyze
from app.models.emails_state import EmailsState
from app.models.email_attachment import EmailAttachment
from app import socketio
from app.models.mail_type import MailType
import time

def idle_watch(username, password):
    HOST = "imap.gmail.com"
    analyzer = EmailAnalyze(username, password)

    with IMAPClient(HOST) as client:
        client.login(username, password)
        client.select_folder("INBOX")
        current_app.logger.info(f"📡 Watcher IMAP IDLE actif pour {username}")

        while True:
            try:
                # 1. Entrer en mode IDLE
                client.idle()
                current_app.logger.info("⏳ Waiting... (IDLE mode)")
                responses = client.idle_check(timeout=60)
                client.idle_done()

                # 2. Si Gmail notifie : on agit
                if responses:
                    current_app.logger.info("📬 Signal reçu via IDLE")
                    process_unseen_emails(client, analyzer)

                # 3. Fallback : recheck au cas où IDLE a raté
                else:
                    current_app.logger.info("🔍 Aucun signal IDLE → vérification manuelle")
                    process_unseen_emails(client, analyzer)

            except Exception as e:
                current_app.logger.error(f"❌ Erreur dans le watcher : {e}")
                time.sleep(10)

def process_unseen_emails(client, analyzer):
    unseen_uids = client.search(["UNSEEN"])
    if not unseen_uids:
        current_app.logger.info("📭 Aucun mail non lu")
        return

    for uid in unseen_uids:
        raw_msg = client.fetch([uid], ["RFC822"])[uid][b"RFC822"]
        msg = email.message_from_bytes(raw_msg)

        # Sujet
        subject, encoding = decode_header(msg["Subject"])[0]
        if isinstance(subject, bytes):
            subject = subject.decode(encoding or "utf-8")

        # Expéditeur
        sender = email.utils.parseaddr(msg.get("From"))[1]

        # Date
        date_str = msg.get("Date")
        receive_at = email.utils.parsedate_to_datetime(date_str)

        # Corps
        body = analyzer.extract_body(msg)
        path = analyzer.generate_gmail_link(msg.get("Message-ID"))
        attachments = analyzer.extract_attachments(msg)

        mail_type_id = 1
        percentage = 0

        mail_type = MailType.select_by_id(mail_type_id) if mail_type_id else None

        # Création d’un dictionnaire au départ
        new_email_dict = {
            "subject": subject,
            "sender": sender,
            "mail": sender,
            "body": body,
            "receive_at": receive_at,
            "path": path,
            "percentage": 0,
            "mail_type_id": mail_type_id,
            "attachments": attachments
        }

        # Analyse GPT
        if mail_type:
            percentage = analyzer.analyze_email_with_chatgpt(new_email_dict, mail_type.type_name)
            new_email_dict["percentage"] = int(percentage)

        # Si pertinent, créer un objet Emails
        if new_email_dict["percentage"] >= 50:
            new_email = Emails(
                subject=new_email_dict["subject"],
                sender=new_email_dict["sender"],
                mail=new_email_dict["mail"],
                body=new_email_dict["body"],
                receive_at=new_email_dict["receive_at"],
                path=new_email_dict["path"],
                percentage=new_email_dict["percentage"],
                mail_type_id=new_email_dict["mail_type_id"]
            )

            db.session.add(new_email)
            db.session.flush()
            
            # Ajout des pièces jointes
            for attachment in new_email_dict["attachments"]:
                if not EmailAttachment.exists(new_email.id, attachment["filename"]):
                    db.session.add(EmailAttachment(
                        email_id=new_email.id,
                        filename=attachment["filename"],
                        content_type=attachment["content_type"],
                        data=attachment["data"]
                    ))

            db.session.add(EmailsState(new_email.id, 1))
            db.session.commit()

            socketio.emit("new_email", {
                "total": Emails.query.count(),
                "new_count": 1,
                "new_emails": [new_email.to_dict()]
            })

            current_app.logger.info(f"📧 Email enregistré et émis : {new_email.subject}")
