# Utiliser une image de base Python
FROM python:3.8-slim

# Définir le répertoire de travail
WORKDIR /24kuk

# COPY requirements.txt .
# Copier les fichiers nécessaires dans le container
COPY . .

# Installer les dépendances
RUN pip install --no-cache-dir -r requirements.txt requests

ENV FLASK_APP=run.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=5000

EXPOSE 5000

# Lancer l'application Flask
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000", "--debug"]

