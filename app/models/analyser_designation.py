import xmlrpc.client
import requests

# ======= CONFIGURATION =======
ODOO_URL = 'https://phareindustrie.odoo.com'
ODOO_DB = 'phareindustrie'
ODOO_USER = 'mr@phareindustries.com'
ODOO_PASSWORD = 'min001985#PI_odoo'

FLASK_URL = 'http://localhost:5001/verifier_designation'

# ======= CONNEXION À ODOO =======
common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")

# ======= 1. CHERCHER LES LIGNES À ANALYSER =======
domain = [('x_analyser_automatiquement', '=', True)]  # champ booléen déclencheur
fields = ['id', 'name', 'x_studio_categorie_id', 'x_studio_categorie_id_display_name']  # à adapter

records = models.execute_kw(
    ODOO_DB, uid, ODOO_PASSWORD,
    'sale.order.line', 'search_read',
    [domain], {'fields': fields, 'limit': 10}
)

for rec in records:
    designation = rec['name']
    categorie = rec.get('x_studio_categorie_id_display_name') or 'Inconnue'

    # Tu peux aussi appeler Odoo pour récupérer les attributs obligatoires liés à cette catégorie

    attributs_obligatoires = ["longueur", "largeur", "marque"]  # TODO : récupérer dynamiquement si possible

    payload = {
        "designation": designation,
        "categorie": categorie,
        "attributs": attributs_obligatoires
    }

    print(f"🧠 Envoi : {payload}")

    try:
        r = requests.post(FLASK_URL, json=payload)
        resultat = r.json()
        print("✅ Résultat IA :", resultat)

        # Prépare les valeurs à mettre à jour dans Odoo
        valeurs = {
            'x_studio_status_designation': resultat.get('status'),
        }

        for attr in attributs_obligatoires:
            champ_odoo = f"x_studio_{attr}"
            valeurs[champ_odoo] = resultat.get(attr, '')

        # Décocher le champ de déclenchement
        valeurs['x_analyser_automatiquement'] = False

        models.execute_kw(
            ODOO_DB, uid, ODOO_PASSWORD,
            'sale.order.line', 'write',
            [[rec['id']], valeurs]
        )

        print(f"✔️ Ligne {rec['id']} mise à jour avec succès.")

    except Exception as e:
        print("❌ Erreur IA :", str(e))
