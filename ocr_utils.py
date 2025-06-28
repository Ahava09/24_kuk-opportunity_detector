# import os
# import base64
# import requests
# import fitz  # PyMuPDF
# import json
# from flask import current_app
# from google.oauth2 import service_account
# from google.auth.transport.requests import Request

# # Charger le fichier JSON OAuth
# SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")  # Ex: "vision-service-account.json"
# SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]

# def get_access_token() -> str:
#     """Génère un access token à partir du compte de service"""
#     credentials = service_account.Credentials.from_service_account_file(
#         SERVICE_ACCOUNT_FILE, scopes=SCOPES
#     )
#     credentials.refresh(Request())
#     return credentials.token

# def extract_text_from_image_bytes(image_bytes: bytes) -> str:
#     """Effectue l'OCR via Google Vision API avec OAuth2"""

#     access_token = get_access_token()

#     # Encodage base64
#     content = base64.b64encode(image_bytes).decode("utf-8")
#     current_app.logger.info(f"📤 Image encodée : {len(content)} caractères base64")

#     url = "https://vision.googleapis.com/v1/images:annotate"

#     headers = {
#         "Authorization": f"Bearer {access_token}",
#         "Content-Type": "application/json",
#     }

#     payload = {
#         "requests": [
#             {
#                 "image": {"content": content},
#                 "features": [{"type": "TEXT_DETECTION"}]
#             }
#         ]
#     }

#     try:
#         response = requests.post(url, headers=headers, json=payload)
#         response.raise_for_status()
#     except requests.RequestException as e:
#         current_app.logger.error(f"❌ Erreur HTTP Vision API : {e}")
#         return ""

#     result = response.json()

#     from pprint import pformat
#     current_app.logger.info("🧠 Réponse complète Vision API :\n" + pformat(result))

#     try:
#         description = result["responses"][0]["textAnnotations"][0]["description"]
#         current_app.logger.info(f"✅ Texte détecté : {description[:100]}...")
#         return description
#     except (KeyError, IndexError):
#         current_app.logger.warning("⚠️ Aucun texte détecté par Vision API")
#         return ""

# def extract_text_from_pdf(pdf_bytes: bytes) -> str:

#     text = ""
#     pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
#     current_app.logger.info(f"📑 Le PDF contient {len(pdf)} page(s)")

#     for page in pdf:
#         current_app.logger.info(f"📄 Page {page.number}")
#         pix = page.get_pixmap(dpi=200)
#         current_app.logger.info(f"🖼️ Image générée : {pix.width}x{pix.height}")
#         image_bytes = pix.tobytes("png")

#         page_text = extract_text_from_image_bytes(image_bytes)
#         current_app.logger.info(f"✍️ Texte extrait page {page.number} : {page_text[:100]}...")
#         text += page_text + "\n"

#     return text
from flask import Flask, request, render_template
from PIL import Image
import pytesseract
import tempfile
import fitz  # PyMuPDF
import requests
import io

def extract_text_from_image_bytes(image_bytes):
    image = Image.open(io.BytesIO(image_bytes))
    return pytesseract.image_to_string(image)

def extract_text_from_pdf(pdf_bytes):
    text = ""
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page in doc:
            pix = page.get_pixmap(dpi=300)
            img_bytes = pix.tobytes("png")
            text += pytesseract.image_to_string(Image.open(io.BytesIO(img_bytes)))
    return text

def extract_text_ocr_space(file_bytes, is_pdf=False):
    url = 'https://api.ocr.space/parse/image'
    files = {'file': ('file.pdf' if is_pdf else 'file.png', file_bytes)}
    data = {
        'apikey': 'helloworld',
        'language': 'fre'
    }
    try:
        response = requests.post(url, data=data, files=files)
        result = response.json()
        return result.get('ParsedResults', [{}])[0].get('ParsedText', '[Aucun texte extrait]')
    except Exception as e:
        return f"Erreur OCR.Space : {str(e)}"

def simulate_google_vision(file_bytes):
    return "[Simulation Google Vision] - Texte fictif extrait avec succès."
