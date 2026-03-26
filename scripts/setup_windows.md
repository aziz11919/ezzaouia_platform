# Guide d installation — Windows 10/11

## 1. Prérequis système (à installer une seule fois)

### A) ODBC Driver 17 for SQL Server
Télécharger et installer :
https://aka.ms/downloadmsodbcsql
→ Choisir "ODBC Driver 17 for SQL Server" pour Windows x64

### B) Memurai (Redis pour Windows) — Broker Celery
Site officiel : https://www.memurai.com/get-memurai
→ Télécharger Memurai Developer (gratuit)
→ Installer → il démarre automatiquement comme service Windows
→ Vérifier : ouvrir cmd et taper : memurai-cli ping  (doit répondre PONG)

### C) Ollama — LLM local
Site officiel : https://ollama.com/download
→ Télécharger OllamaSetup.exe → Installer
→ Après installation, ouvrir cmd et taper :
    ollama pull llama3
  (télécharge ~4.7 Go — à faire une seule fois)
→ Vérifier : ollama run llama3 "Bonjour"

---

## 2. Créer l environnement virtuel Python

Ouvrir un terminal (PowerShell ou cmd) dans le dossier du projet :

    python -m venv venv
    venv\Scripts\activate

Vous devez voir (venv) au début de la ligne.

---

## 3. Installer les dépendances

    pip install -r requirements/dev.txt

---

## 4. Configurer les variables d environnement

    copy .env.example .env

Ouvrir .env avec Notepad et remplir :
- DB_SERVER     : nom de votre instance SQL Server (ex: DESKTOP-XYZ\SQLEXPRESS)
- DB_NAME       : nom de votre base DWH (ex: EZZAOUIA_DWH)
- DB_USER / DB_PASSWORD : vos credentials SQL Server
  (ou mettre DB_TRUSTED_CONNECTION=yes pour auth Windows)

---

## 5. Créer le dossier logs

    mkdir logs

---

## 6. Appliquer les migrations Django

    python manage.py migrate

NB : Les tables warehouse (DWH) ne sont PAS migrées (managed=False).
     Seules les tables Django internes sont créées.

---

## 7. Créer un superutilisateur

    python manage.py createsuperuser

---

## 8. Lancer le serveur de développement

Terminal 1 — Django :
    venv\Scripts\activate
    python manage.py runserver

Terminal 2 — Celery worker :
    venv\Scripts\activate
    celery -A config worker --loglevel=info --pool=solo

(--pool=solo est nécessaire sur Windows)

---

## 9. Vérifier que tout fonctionne

Ouvrir le navigateur : http://127.0.0.1:8000/admin/
→ Se connecter avec le superutilisateur créé à l étape 7.

