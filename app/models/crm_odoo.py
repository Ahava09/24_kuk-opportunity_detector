import re
from datetime import datetime

def parse_french_date(date_str):
    try:
        if date_str.strip():
            return datetime.strptime(date_str, "%d/%m/%Y").strftime("%Y-%m-%d")
        return None
    except:
        return None

def clean_special_characters(text):
    """Nettoyer les caractères spéciaux problématiques pour Odoo."""
    if not isinstance(text, str):
        return text
    replacements = {
        "Ü": "U",
        "&": "et",
        "<": "",
        ">": "",
        '"': "'",
        "’": "'",
        "“": '"',
        "”": '"',
        "–": "-",
        "—": "-",
        "é": "e",
        "è": "e",
        "ê": "e",
        "à": "a",
        "ç": "c",
        "ô": "o",
        "œ": "oe",
        "€": "EUR",
        "©": "(c)",
        "\n": " ",
        "\r": " "
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return re.sub(r'\s+', ' ', text).strip()

# def structure_lead_payload_for_odoo(info):
#     dea = info.get("DEA", {})
#     det = info.get("DET", {})

#     fallback_name = clean_special_characters(info.get("email_sender", ""))
#     fallback_email = clean_special_characters(info.get("email_address", ""))

#     client_name = clean_special_characters(info.get("client_name") or fallback_name)
#     client_email = clean_special_characters(info.get("client_email") or fallback_email)
#     client_phone = clean_special_characters(info.get("client_phone", ""))

#     company_name = clean_special_characters(info.get("company_name", ""))
#     company_phone = clean_special_characters(info.get("company_phone", ""))
#     company_street = clean_special_characters(info.get("company_street", ""))
#     company_website = clean_special_characters(info.get("company_website", ""))

#     sujet = clean_special_characters(dea.get("objet_demande", "Demande client"))
#     contexte = clean_special_characters(dea.get("contexte", ""))
#     date_limite_reponse = dea.get("date_limite_reponse", "")
#     criteres = clean_special_characters(dea.get("criteres_selection", ""))
#     path = info.get("path_mail", "")
#     lien_email = f"[📬 Consulter l'email dans Odoo]({path})"

#     products = []
#     order_lines = []
#     for category, items in det.get("categories", {}).items():
#         for product in items:
#             nom_produit = clean_special_characters(product.get('nom_produit', 'Produit inconnu'))
#             specs = clean_special_characters(product.get('specifications_techniques', ''))
#             certif = clean_special_characters(product.get("certification_requise", ""))
#             qty = clean_special_characters(product.get("quantite_estimee", 1))
#             qty = int(qty) if str(qty).isdigit() else 1

#             line = f"- {nom_produit} ({specs})"
#             if certif:
#                 line += f" ✅ Certif: {certif}"
#             products.append(line)

#             order_lines.append({
#                 "category": category,
#                 "name": nom_produit,
#                 "product_uom_qty": qty,
#                 "price_unit": 0,
#             })

#     description = f"""📩 **Email reçu de {client_name}**

# 📧 Email : {client_email}
# 📞 Téléphone : {client_phone}
# 🏢 Société : {company_name}
# 🌐 Site Web : {company_website}
# 📍 Adresse : {company_street}

# 🎯 **Objet de la demande** : {sujet}

# 📌 **Contexte** : {contexte}

# 🎯 **Critères de sélection** : {criteres}

# 🔗 **Lien vers l'email** : {lien_email}

# 🛠️ **Produits demandés** :
# {chr(10).join(products)}
# """

#     lead_payload = {
#         "name": f"{sujet} - {company_name}",
#         "contexte": contexte,
#         "date_limite_reponse": date_limite_reponse,
#         "contact_name": client_name,
#         "partner_name": company_name,
#         "path": path,
#         "email_from": client_email,
#         "phone": client_phone,
#         "website": company_website,
#         "description": description,
#         "order_lines": order_lines,  # 🧩 données prêtes pour sale.order.line
#         "street": company_street
#     }

#     return lead_payload

def structure_lead_payload_for_odoo(info):
    dea = info.get("DEA", {})
    det = info.get("DET", {})

    demandeur = dea.get("demandeur", {}) or {}

    nom = clean_special_characters(demandeur.get("nom", "")).strip()
    prenom = clean_special_characters(demandeur.get("prenom", "")).strip()

    # Si aucun nom ni prénom, on prend le nom de l'expéditeur
    fallback_name = clean_special_characters(info.get("email_sender", "")).strip()
    fallback_email = clean_special_characters(info.get("email_address", "")).strip()

    # Nom complet : soit nom + prénom, soit nom expéditeur
    client_name = f"{nom} {prenom}".strip() if nom or prenom else fallback_name

    # Email : soit l'email du demandeur s'il existe, sinon celui de l'expéditeur
    client_email = clean_special_characters(demandeur.get("email", "") or fallback_email)

    client_phone = clean_special_characters(demandeur.get("telephone", ""))

    company_name = clean_special_characters(dea.get("entreprise_demandeuse", info.get("company_name", "")))
    company_phone = clean_special_characters(dea.get("coordonnees_entreprise", {}).get("telephone", info.get("company_phone", "")))
    company_street = clean_special_characters(dea.get("adresse_entreprise", info.get("company_street", "")))
    company_website = clean_special_characters(dea.get("coordonnees_entreprise", {}).get("site_web", info.get("company_website", "")))

    sujet = clean_special_characters(dea.get("objet_demande", "Demande client"))
    email_body = clean_special_characters(info.get("email_body", ""))
    contexte = clean_special_characters(dea.get("contexte", ""))
    criteres = clean_special_characters(dea.get("criteres_selection", ""))
    path = info.get("path_mail", "")
    lien_email = f"[📬 Consulter l'email dans Odoo]({path})"

    # Champs additionnels
    reference_demande = clean_special_characters(dea.get("reference_demande", ""))
    date_limite_reponse = parse_french_date(clean_special_characters(dea.get("date_limite_reponse", "")))
    date_limite_livraison = parse_french_date(clean_special_characters(dea.get("date_limite_livraison", "")))
    budget_estime = clean_special_characters(dea.get("budget_estime", ""))
    adresse_livraison = clean_special_characters(dea.get("adresse_livraison", ""))
    modalites_paiement = clean_special_characters(dea.get("modalites_paiement", ""))
    probability = info.get("probability", 0)
    try:
        probability = float(str(probability).replace(",", "."))
    except:
        probability = 0
    products = []
    order_lines = []

    for product in det.get("produits", []):
        nom_produit = clean_special_characters(product.get('designation_client', ''))
        specs = clean_special_characters(product.get('specifications_techniques', ''))
        ref = clean_special_characters(product.get('reference_fournisseur', ''))
        certif = clean_special_characters(product.get("certification_requise", ""))
        qty = product.get("quantite_estimee", 1)
        try:
            qty = float(str(qty).replace(",", "."))
            # qty = int(float(qty)) if isinstance(qty, str) else int(qty)
        except:
            qty = 1

        line = f"- {nom_produit} ({specs})"
        if certif:
            line += f" ✅ Certif: {certif}"
        products.append(line)

        order_lines.append({
            "ref_fournisseur": ref,  
            "name": nom_produit,
            "product_uom_qty": qty,
            "price_unit": 0,
        })

    description = f"""📩 **Email reçu de {client_name}**

📧 Email : {client_email}
📞 Téléphone : {client_phone}
🏢 Société : {company_name}
🌐 Site Web : {company_website}
📍 Adresse : {company_street}

🎯 **Objet de la demande** : {sujet}
📌 **Contexte** : {contexte}
🎯 **Critères de sélection** : {criteres}
🗓 **Date limite de réponse** : {date_limite_reponse}
📅 **Date limite de livraison** : {date_limite_livraison}
💰 **Budget estimé** : {budget_estime}
📦 **Adresse de livraison** : {adresse_livraison}
💳 **Modalités de paiement** : {modalites_paiement}
🔗 **Lien vers l'email** : {lien_email}

🛠️ **Produits demandés** :
{chr(10).join(products)}
"""

    lead_payload = {
        "name": f"{sujet} - {company_name}",
        "contexte": contexte,
        "contact_name": client_name,
        "partner_name": company_name,
        "path": path,
        "email_from": client_email,
        "email_body": email_body,
        "phone": client_phone,
        "phone_company": company_phone,
        "website": company_website,
        "description": description,
        "order_lines": order_lines,
        "street": company_street,
        # Champs personnalisés ou à mapper dans Odoo
        "reference_demande": reference_demande,
        "date_limite_reponse": date_limite_reponse,
        "date_limite_livraison": date_limite_livraison,
        "budget_estime": budget_estime,
        "adresse_livraison": adresse_livraison,
        "modalites_paiement": modalites_paiement,
        "probability": probability
    }
    # Supprimer les champs None ou vides (uniquement pour les dates et autres champs sensibles)
    # lead_payload = {k: v for k, v in lead_payload.items() if v not in [None, ""]}
    return lead_payload
