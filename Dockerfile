# Utiliser une image Python officielle
FROM python:3.11.9

# Définir le dossier de travail
WORKDIR /app

# Copier les fichiers dans le conteneur
COPY . .

# Installer les dépendances
RUN pip install -r requirements.txt

# Exposer le port 5000
EXPOSE 5000

# Lancer l’application
CMD ["python", "app.py"]
