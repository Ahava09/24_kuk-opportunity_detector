import imaplib
import email
import os
from email.header import decode_header
from datetime import datetime


class Email:
    def __init__(self, subject, sender, body, attachments=None):
        self.subject = subject
        self.sender = sender
        self.body = body
        self.attachments = attachments if attachments else []

    def __repr__(self):
        return f"Email(subject={self.subject}, sender={self.sender}, attachments={len(self.attachments)})"


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

                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding if encoding else "utf-8")

                    sender = msg.get("From")
                    body = self.extract_body(msg)
                    attachments = self.extract_attachments(msg)

                    emails.append(Email(subject, sender, body, attachments))

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
