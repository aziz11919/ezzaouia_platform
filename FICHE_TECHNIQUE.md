# FICHE TECHNIQUE — Plateforme EZZAOUIA / MARETAP
> Révision soutenance technique — Document complet par fichier

---

## ARCHITECTURE GLOBALE

```
┌─────────────────────────────────────────────────────────┐
│                     NAVIGATEUR                          │
│              React SPA (index.html)                     │
│   Login / Dashboard / Chatbot / Users / Reports ...     │
└──────────────────┬──────────────────────────────────────┘
                   │  HTTP (JSON) + Session Cookie + CSRF
┌──────────────────▼──────────────────────────────────────┐
│                 DJANGO (Backend)                         │
│  Middleware stack → URL router → Views → JSON/HTML      │
└──────┬──────────────────┬────────────────┬──────────────┘
       │                  │                │
  SQL Server          Redis/Celery      Ollama (LLM)
  (Data Warehouse      (tâches async     (IA locale,
   + App DB)           d'ingestion)      chatbot RAG)
```

**Principe clé :** Django ne génère plus de HTML. Chaque page charge React via `serve_react()`. React appelle ensuite des endpoints JSON (`api_*`) pour les données.

---

## 1. CONFIG/

### `config/settings.py`
Fichier de configuration central. Points importants :

| Paramètre | Valeur / Rôle |
|---|---|
| `SECRET_KEY` | Clé secrète Django (depuis `.env`) |
| `DEBUG` | True en dev, False en prod |
| `AUTH_USER_MODEL` | `accounts.User` — modèle utilisateur personnalisé |
| `DATABASES` | SQL Server On-Premise via `mssql` + ODBC Driver 18 |
| `MIDDLEWARE` | Pile de 11 middlewares (voir section dédiée) |
| `SESSION_COOKIE_AGE` | 1800 secondes = 30 min d'inactivité |
| `CELERY_BROKER_URL` | Redis (port 6379) — file de tâches async |
| `CELERY_RESULT_BACKEND` | `django-db` — résultats stockés en SQL Server |
| `TIME_ZONE` | `Africa/Tunis` |
| `STATICFILES_STORAGE` | WhiteNoise — sert les fichiers statiques compressés |

**Apps installées :**
```
core · accounts · warehouse · ingestion · bibliotheque
reports · kpis · chatbot · dashboard · audit · forecasting
```

---

### `config/urls.py`
Routeur principal — distribue chaque URL vers l'app concernée.

```python
/admin/            → Django Admin
/accounts/         → apps.accounts.urls
/dashboard/        → apps.dashboard.urls
/ingestion/        → apps.ingestion.urls
/bibliotheque/     → apps.bibliotheque.urls
/reports/          → apps.reports.urls
/chatbot/          → apps.chatbot.urls
/audit/            → apps.audit.urls
/api/forecasting/  → apps.forecasting.urls
/api/kpis/         → apps.kpis.urls
/api/warehouse/    → apps.warehouse.urls
/api/maintenance/  → apps.core.maintenance_views
/api/powerbi/      → apps.dashboard.powerbi_views
/                  → serve_react()   ← catch-all → React SPA
re_path(tout le reste) → serve_react()
```

**La dernière ligne** est essentielle : toute URL non reconnue par Django (ex: `/chatbot/session/12`) est renvoyée à React qui gère son propre routage.

---

### `config/celery.py`
Configure Celery pour les tâches asynchrones (traitement de fichiers, indexation RAG).

```python
app = Celery('ezzaouia_platform')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()  # trouve tous les tasks.py automatiquement
```

Utilisé principalement par `apps/ingestion/tasks.py` pour parser les fichiers uploadés en arrière-plan.

---

### `config/wsgi.py`
Point d'entrée WSGI — utilisé par Gunicorn/uWSGI en production pour démarrer Django.

---

## 2. APPS/CORE/

> Couche fondation. Tous les autres apps en dépendent. Ne dépend d'aucune autre app.

### `core/models.py`

**`BaseModel`** (abstrait)
```python
class BaseModel(models.Model):
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
    class Meta:
        abstract = True
```
Hérité par tous les modèles métier (ChatSession, ChatMessage, UploadedFile…). Donne `created_at` et `updated_at` automatiquement.

**`SiteConfiguration`** (singleton)
```python
class SiteConfiguration(models.Model):
    maintenance_mode    = BooleanField(default=False)
    maintenance_message = TextField(...)
    maintenance_start   = DateTimeField(null=True)
    estimated_end       = DateTimeField(null=True)
```
- Toujours `pk=1` (une seule ligne en base). Le `save()` force `self.pk = 1`.
- `get()` → `get_or_create(pk=1)` : crée l'entrée si elle n'existe pas encore.

---

### `core/views.py`

**`serve_react(request)`** — fonction la plus utilisée du projet
```python
@ensure_csrf_cookie
def serve_react(request):
    react_path = BASE_DIR / 'static/react/index.html'
    if not os.path.exists(react_path):
        return HttpResponse('<h1>Frontend not built</h1>', status=503)
    return FileResponse(open(react_path, 'rb'), content_type='text/html')
```
- Envoie `index.html` au navigateur → React prend le relais.
- `@ensure_csrf_cookie` : injecte le cookie CSRF pour que React puisse faire des POST.
- Si le build React n'existe pas, retourne 503 avec instructions.

---

### `core/admin.py`
Enregistre `SiteConfiguration` dans `/admin/` :
- `has_add_permission` → interdit d'ajouter une 2e instance (singleton).
- `has_delete_permission` → interdit la suppression.
- Widget `datetime-local` pour `estimated_end`.

---

### `core/maintenance_middleware.py` — `MaintenanceMiddleware`

S'exécute avant toute vue. Logique :

```
1. URL dans PUBLIC_ALLOWED (login, static, forgot-password...) → laisser passer
2. maintenance_mode == False → laisser passer
3. User admin + URL dans ADMIN_ALLOWED (admin panel, toggle, logout) → laisser passer
4. Requête JSON/API → retourner 503 JSON {"detail": "maintenance", "message": ...}
5. User admin → redirect /administration/maintenance
6. User normal → redirect /maintenance
```

**URLs toujours autorisées :**
`/static/`, `/accounts/login/`, `/accounts/forgot-password/`, `/accounts/reset-password/`, `/login`, `/maintenance`

---

### `core/middleware.py` — `ContentSecurityPolicyMiddleware`
Ajoute un header HTTP à chaque réponse :
```
Content-Security-Policy: frame-src 'self' https://app.powerbi.com https://*.powerbi.com
```
Nécessaire pour que les iframes Power BI fonctionnent (sinon le navigateur les bloque).

---

### `core/maintenance_views.py`

| Endpoint | Méthode | Rôle |
|---|---|---|
| `maintenance_status` | GET `/api/maintenance/status/` | Retourne l'état maintenance en JSON (public — React l'appelle au démarrage) |
| `maintenance_toggle` | POST `/api/maintenance/toggle/` | Admin active/désactive maintenance, modifie message et date de fin |

---

### `core/powerbi_views.py` — `powerbi_reports`
Gère une liste de rapports Power BI stockés dans `/app/data/powerbi_config.json`.

| Méthode | Qui | Action |
|---|---|---|
| GET | Tout utilisateur connecté | Retourne la liste des rapports avec embed URLs |
| POST | Staff admin uniquement | Sauvegarde la config mise à jour sur disque |

Si le fichier n'existe pas → retourne `DEFAULT_REPORTS` (placeholder).

---

## 3. APPS/ACCOUNTS/

> Gestion des utilisateurs, authentification, sessions, permissions.

### `accounts/models.py` — `User`
Étend `AbstractUser` de Django avec des champs supplémentaires :

```python
class User(AbstractUser):
    role       = CharField(choices=['admin', 'user'], default='user')
    department = CharField(max_length=100)
    phone      = CharField(max_length=20)

    # Gestion mot de passe
    must_change_password   = BooleanField(default=True)
    password_reset_token   = CharField(max_length=64, null=True)
    password_reset_expires = DateTimeField(null=True)
    last_password_change   = DateTimeField(null=True)

    @property
    def is_admin(self): return self.role == 'admin'
    @property
    def is_user(self):  return self.role == 'user'
```

- `must_change_password=True` par défaut → tout nouveau compte force le changement au 1er login.
- `password_reset_token` : token URL-safe généré pour reset par email, valide 1 heure.

---

### `accounts/utils.py`
Fonctions utilitaires de sécurité et email :

| Fonction | Rôle |
|---|---|
| `generate_random_password(length=12)` | Mot de passe aléatoire sécurisé via `secrets.choice`. Garantit 1 majuscule + 1 minuscule + 1 chiffre + 1 symbole. Boucle jusqu'à satisfaire toutes les conditions. |
| `generate_reset_token()` | Token URL-safe 32 bytes via `secrets.token_urlsafe`. |
| `send_welcome_email(user, password)` | Email de bienvenue avec mot de passe temporaire. |
| `send_password_reset_email(user, token)` | Email avec lien reset valable 1 heure. |
| `send_password_changed_email(user)` | Notification de changement de mot de passe réussi. |

---

### `accounts/middleware.py`

**`ForcePasswordChangeMiddleware`**
- Si `user.must_change_password == True` et l'URL n'est pas dans `EXEMPT_PATHS` → redirige vers `/accounts/change-password/`.
- `EXEMPT_PATHS` : change-password, logout, login, me, api-change-password, api-logout, ping.

**`SessionTimeoutMiddleware`**
- Expire la session après **1800 secondes** (30 min) d'inactivité.
- Stocke le timestamp de dernière activité en session (`last_activity`).
- Optimisation : ne met à jour la session que toutes les 60 secondes (`write_throttle_seconds`) pour éviter les écritures inutiles en base.
- Si timeout : logout + message d'avertissement + redirect login avec `?next=`.
- Enregistre l'événement dans `AuditLog` (action `SESSION_EXPIRED`).

---

### `accounts/views.py`
Deux catégories de fonctions :

**Vues React SPA (servent `index.html`) :**
```
login_view        → GET: serve_react | POST: authentification JSON ou HTML
logout_view       → logout + redirect login
change_password   → serve_react (React gère via api_change_password)
forgot_password   → serve_react
reset_password    → serve_react
user_list         → serve_react
user_edit         → serve_react
user_delete       → serve_react
create_user       → serve_react
edit_profile      → GET: serve_react | POST: mise à jour profil (Django form)
```

**API JSON pour React (`api_*`) :**
| Endpoint | Vue | Rôle |
|---|---|---|
| GET `/accounts/me/` | `api_me` | Retourne l'utilisateur connecté en JSON |
| POST `/accounts/api-logout/` | `api_logout` | Déconnexion JSON |
| POST `/accounts/api-change-password/` | `api_change_password` | Change le mot de passe (gère forced + voluntary) |
| POST `/accounts/api-profile/` | `api_update_profile` | Met à jour prénom, nom, email, téléphone, département |
| GET `/accounts/users-api/` | `api_users` | Liste paginée des utilisateurs (admin) |
| POST `/accounts/users-api/<id>/toggle/` | `api_user_toggle` | Active/désactive un compte |
| POST `/accounts/users-api/<id>/delete/` | `api_user_delete` | Supprime un utilisateur |
| GET `/accounts/users-api/<id>/detail/` | `api_get_user` | Détail d'un utilisateur pour le formulaire d'édition |
| POST `/accounts/users-api/<id>/edit/` | `api_edit_user` | Modifie un utilisateur |
| POST `/accounts/users-api/<id>/reset-password/` | `api_admin_reset_password` | Admin remet un mot de passe |
| POST `/accounts/api-create-user/` | `api_create_user` | Crée un compte + envoie email avec mot de passe temporaire |
| POST `/accounts/api-forgot-password/` | `api_forgot_password` | Demande de reset par email |
| GET+POST `/accounts/api-reset-password/<token>/` | `api_reset_password` | Valide le token / enregistre le nouveau mot de passe |

**Décorateurs de rôle :**
```python
@admin_required   # user.role == 'admin'
@user_required    # user.role in ['admin', 'user']
@role_required(*roles)  # générique
```
Redirige vers `dashboard:home` si accès refusé.

---

### `accounts/urls.py`
Définit les routes sous le préfixe `/accounts/` avec `app_name='accounts'`.

---

## 4. APPS/AUDIT/

> Traçabilité de toutes les actions utilisateurs.

### `audit/models.py` — `AuditLog`

```python
class AuditLog(models.Model):
    user       = ForeignKey(User, SET_NULL, null=True)
    action     = CharField(choices=Action)  # LOGIN, LOGOUT, UPLOAD_FILE, CHATBOT_QUESTION...
    details    = TextField()   # JSON stocké en texte
    ip_address = GenericIPAddressField()
    user_agent = TextField()
    created_at = DateTimeField(auto_now_add=True, db_index=True)
```

**Actions tracées :**
`LOGIN · LOGOUT · UPLOAD_FILE · CHATBOT_QUESTION · EXPORT_PDF · EXPORT_EXCEL · VIEW_PAGE · DELETE_SESSION · SESSION_EXPIRED`

**Méthode clé `AuditLog.log()`** :
- Méthode de classe appelée partout dans le projet.
- Extrait automatiquement l'IP (`X-Forwarded-For` ou `REMOTE_ADDR`) et le User-Agent.
- Sérialise `details` en JSON si c'est un dict.
- Tronque `details` à 4000 chars, `user_agent` à 1000.
- Ne plante jamais (try/except → return None).

**Propriétés d'affichage :**
- `parsed_details` : parse le JSON stocké en dict Python.
- `details_display` : format lisible `"clé: valeur | clé: valeur"`.
- `duration_display` : extrait et formate la durée en secondes.

---

### `audit/middleware.py` — `AuditMiddleware`
S'exécute après chaque requête. Ignore `/static/`, `/media/`, erreurs 4xx.

Détecte automatiquement le type d'action :
- URL match `/chatbot/session/<id>/delete/` → `DELETE_SESSION`
- Content-Type `application/pdf` → `EXPORT_PDF`
- Content-Type `spreadsheetml` ou `text/csv` → `EXPORT_EXCEL`
- Réponse HTML sur GET → `VIEW_PAGE`

Mesure le temps de réponse (`time.perf_counter`) et le stocke dans `details.duration_ms`.

---

### `audit/views.py`

| Vue | Rôle |
|---|---|
| `audit_log_list` | Sert React (page admin des logs) |
| `api_logs` (GET) | Retourne logs JSON paginés (20/page) avec filtres : user, action, start_date, end_date |

---

## 5. APPS/WAREHOUSE/

> Lecture seule sur le Data Warehouse SQL Server EZZAOUIA.

### `warehouse/models.py`
Tous les modèles ont `managed = False` → Django ne crée/modifie jamais ces tables. Il lit uniquement des tables SQL Server existantes.

| Modèle | Table SQL | Contenu |
|---|---|---|
| `DimDate` | `DimDate` | Dimension temps (jour, mois, année, trimestre) |
| `DimWell` | `DimWell` | Dimension puits (code, libellé, couche, statut fermé/ouvert) |
| `DimWellStatus` | `DimWellStatus` | Données opérationnelles journalières par puits (BSW, GOR, pression, débit…) |
| `DimPowerType` | `DimPowerType` | Type d'énergie du puits (ESP, gas lift…) |
| `DimProdMethod` | `DimProdMethod` | Méthode de production |
| `DimTypeWell` | `DimTypeWell` | Type de puits |
| `DimTank` | `DimTank` | Bacs de stockage |
| `FactProduction` | `FactProduction` | **Table de faits** : production journalière par puits (huile STB/j, gaz MSCF, eau BWPD) |
| `FactTankLevel` | `FactTankLevel` | Niveau journalier des bacs (volume BBLS) |

Architecture **Data Warehouse en étoile** : `FactProduction` reliée à `DimWell`, `DimDate`, `DimWellStatus`.

---

## 6. APPS/INGESTION/

> Upload et traitement de fichiers (PDF, Word, Excel).

### `ingestion/models.py` — `UploadedFile`
```python
class UploadedFile(BaseModel):
    file          = FileField(upload_to='uploads/%Y/%m/%d/')
    original_name = CharField(max_length=255)
    file_type     = CharField(choices=['pdf', 'docx', 'xlsx'])
    status        = CharField(choices=['pending', 'processing', 'success', 'error'])
    uploaded_by   = ForeignKey(User)
    error_msg     = TextField()
    rows_extracted = IntegerField(default=0)
```

### `ingestion/views.py` — `upload_view`
- GET → `serve_react`
- POST → sauvegarde le fichier, crée `UploadedFile(status='pending')`, log audit `UPLOAD_FILE`, copie automatiquement vers dossier OneDrive (`ONEDRIVE_SYNC_DIR`), lance `process_uploaded_file.delay(id)` (tâche Celery asynchrone).

### `ingestion/tasks.py` — `process_uploaded_file`
Tâche Celery. Passe le statut à `processing`, appelle le bon parser selon l'extension, enregistre le texte extrait, passe à `success` ou `error`.

### `ingestion/parsers.py`
Trois parsers :
- `parse_pdf()` → PyMuPDF / pdfplumber
- `parse_word()` → python-docx
- `parse_excel()` → openpyxl / pandas

---

## 7. APPS/CHATBOT/

> Chatbot IA (RAG — Retrieval Augmented Generation) sur les données EZZAOUIA.

### `chatbot/models.py`

| Modèle | Rôle |
|---|---|
| `ChatSession` | Session de conversation. 1 user → N sessions. Titre auto (1ère question). Peut être partagée via `share_token`. |
| `ChatMessage` | 1 question + 1 réponse + durée + `is_satisfied` (like/dislike) + `chart_data` (JSON graphique) |
| `AnalysisComment` | Commentaire d'équipe sur une réponse chatbot. Public ou privé. |
| `SessionShare` | Partage explicite d'une session avec un autre utilisateur. |
| `UserMemory` | Mémoire persistante par utilisateur : résumés d'analyses précédentes par puits et par topic (PRODUCTION, BUDGET, WORKOVER, RESERVOIR, GENERAL). |

---

### `chatbot/rag_pipeline.py`
Cœur IA du projet. Fonctions principales :
- `ask(question, history, doc_ids, filename, user)` → appelle Ollama (LLM local), construit le prompt avec contexte DWH + documents indexés + historique + mémoire utilisateur. Retourne `{answer, chart_data, suggestions}`.
- `index_document(text, metadata, doc_id)` → découpe le texte en chunks, les indexe dans la base vectorielle (ChromaDB ou équivalent).

---

### `chatbot/memory.py`
Gestion de la mémoire persistante par utilisateur :
- `get_user_memory(user)` → retourne les 10 dernières mémoires formatées en texte, injectées dans le prompt du LLM.
- `update_user_memory(user, question, answer, well)` → détecte le topic (PRODUCTION, BUDGET…) via mots-clés, sauvegarde ou met à jour le résumé (`update_or_create`).

---

### `chatbot/morning_suggestions.py`
Génère des suggestions de questions contextuelles pour le matin/après-midi. Mise en cache 4 heures (`cache.set(key, value, 60*60*4)`). Retourne liste vide en dehors des heures ouvrées (avant 6h ou après 17h).

---

### `chatbot/views.py` — Endpoints React

| Endpoint | Vue | Rôle |
|---|---|---|
| POST `/chatbot/ask/` | `ask_view` | Question → réponse LLM, crée/reprend session, log audit, retourne answer + chart_data + suggestions + related_comments |
| GET `/chatbot/sessions/` | `api_sessions` | Liste des sessions de l'utilisateur (30 max) |
| GET `/chatbot/session/<id>/messages/` | `api_session_messages` | Messages d'une session |
| POST `/chatbot/session/<id>/delete/` | `delete_session` | Supprime une session |
| POST `/chatbot/session/<id>/rename/` | `rename_session` | Renomme une session |
| POST `/chatbot/stop/` | `stop_generation` | Signal d'arrêt de génération (via `_stop_requests` set en mémoire) |
| POST `/chatbot/upload/` | `upload_chat_file` | Upload + indexation immédiate d'un fichier pour une question |
| POST `/chatbot/rate/` | `rate_view` | Like/Dislike sur une réponse |
| POST `/chatbot/comment/` | `add_comment` | Ajoute un commentaire analytique |
| GET `/chatbot/comments/<id>/` | `get_comments` | Retourne commentaires publics + propres |
| POST `/chatbot/session/<id>/share/` | `share_session` | Partage une session avec d'autres utilisateurs |
| GET `/chatbot/shared-with-me/` | `shared_with_me` | Sessions partagées avec l'utilisateur |
| GET `/chatbot/api/shared/<token>/` | `api_shared_session` | Données d'une session partagée (public) |
| GET `/chatbot/morning-suggestions/` | `morning_suggestions_view` | Suggestions de questions (cachées 4h) |

---

## 8. APPS/DASHBOARD/

> Page d'accueil et intégration Power BI.

### `dashboard/views.py`
- `home` → `serve_react` (page principale du dashboard)
- Endpoints JSON pour KPIs résumés : production totale, nombre de puits actifs, dernière date de données.

### `dashboard/powerbi_views.py`
API pour gérer les rapports Power BI dans la base de données :
- `api_powerbi_list` → liste des rapports configurés
- `api_powerbi_detail` → détail d'un rapport (embed URL, titre)

### `dashboard/powerbi_models.py` + `powerbi_serializers.py`
Modèle `PowerBIReport` (titre, embed_url, description, ordre) + sérialiseur DRF pour l'API.

---

## 9. APPS/KPIs/

> Calcul des indicateurs clés de production.

### `kpis/calculators.py`
Fonctions de calcul pur sur les données DWH :
- Production totale champ (STBPD)
- Production par puits
- BSW moyen pondéré
- GOR moyen
- Puits actifs vs fermés
- Comparaison mensuelle / annuelle

### `kpis/views.py`
Endpoints GET JSON consommés par React pour alimenter les graphiques du dashboard.

---

## 10. APPS/FORECASTING/

> Prévisions de production par méthodes statistiques.

### `forecasting/models.py`
- `Anomalie` : anomalies détectées (puits, type, sévérité, description, statut). Stockées en base Django (pas DWH).

### `forecasting/forecaster.py`
Moteur de prévision avec 3 modèles (import optionnel — ne plante pas si non installé) :
- **Prophet** (Facebook) — modèle de séries temporelles avec saisonnalité
- **Holt-Winters** (statsmodels) — lissage exponentiel triple
- **Auto-ARIMA** (pmdarima) — sélection automatique du meilleur modèle ARIMA

Données lues directement via `django.db.connection` (requête SQL brute sur `FactProduction`).
`safe_val()` et `safe_int()` convertissent NaN/Inf en 0.0 pour une sérialisation JSON propre.

### `forecasting/views.py`
Endpoints API :
- `GET /api/forecasting/wells/` — liste des puits
- `POST /api/forecasting/forecast/` — lance prévision pour un puits, retourne N mois de prévision JSON

---

## 11. APPS/REPORTS/

> Génération de rapports PDF et Excel.

### `reports/models.py` — `Anomalie`
Même modèle que `forecasting.Anomalie` (anomalies puits détectées).

### `reports/pdf_generator.py`
Génère des PDFs de rapports de production via ReportLab ou WeasyPrint. Inclut tableaux de données, graphiques, en-tête MARETAP.

### `reports/views.py`
- GET → `serve_react` (page de rapports)
- `export_pdf` → génère et retourne un PDF (Content-Type: application/pdf) — déclenche `EXPORT_PDF` dans AuditLog
- `export_excel` → génère et retourne un fichier Excel (openpyxl) — déclenche `EXPORT_EXCEL` dans AuditLog

---

## 12. APPS/BIBLIOTHEQUE/

> Gestion de la bibliothèque de documents internes.

### `bibliotheque/views.py`

| Vue | Rôle |
|---|---|
| Page liste | `serve_react` |
| `api_documents` (GET) | Liste des documents indexés (titre, type, date) |
| `api_delete_document` (POST) | Supprime un document de la bibliothèque et de l'index vectoriel |

---

## 13. MIDDLEWARE STACK (ordre d'exécution)

```
1. CorsMiddleware          → autorise les requêtes cross-origin (dev React → Django)
2. SecurityMiddleware      → headers HTTPS, HSTS
3. WhiteNoiseMiddleware    → sert les fichiers statiques sans serveur web séparé
4. SessionMiddleware       → charge/sauvegarde la session utilisateur
5. CommonMiddleware        → redirections www, slash final
6. CsrfViewMiddleware      → protection CSRF (vérifie le token sur les POST)
7. AuthenticationMiddleware → attache request.user depuis la session
8. MaintenanceMiddleware   → bloque si maintenance_mode == True (core)
9. MessageMiddleware       → flash messages Django
10. SessionTimeoutMiddleware → expire session après 30 min inactivité (accounts)
11. ForcePasswordChangeMiddleware → redirige si must_change_password == True (accounts)
12. AuditMiddleware        → logue automatiquement les actions (audit)
13. ContentSecurityPolicyMiddleware → header CSP pour Power BI (core)
14. XFrameOptionsMiddleware → protection clickjacking (SAMEORIGIN pour Power BI)
```

**Important :** l'ordre est critique. `AuthenticationMiddleware` doit précéder tous les middlewares qui vérifient `request.user`.

---

## 14. FRONTEND REACT

### Structure `frontend/src/`
```
api/
  axios.js      → Instance Axios avec injection CSRF + gestion 401
  auth.js       → 15 fonctions API accounts (login, logout, users...)

contexts/
  AuthContext.jsx → Hook useAuth() : user, login(), logout(), refreshUser()

pages/
  Login.jsx           → Formulaire de connexion
  ChangePassword.jsx  → Changement mot de passe (forcé ou volontaire)
  ForgotPassword.jsx  → Demande reset par email
  ResetPassword.jsx   → Nouveau mot de passe via token
  Profile.jsx         → Profil utilisateur + changement MDP
  UserManagement.jsx  → Liste utilisateurs (admin)
  CreateUser.jsx      → Création utilisateur (admin)
  EditUser.jsx        → Édition utilisateur + reset MDP (admin)

components/
  Layout/Sidebar.jsx  → Navigation + bouton logout

App.jsx               → Routeur React (routes publiques vs protégées)
```

### Routes React (`App.jsx`)
```
/login                          → Login (public, redirige si connecté)
/accounts/change-password       → ChangePassword (protégé)
/accounts/forgot-password       → ForgotPassword (public)
/accounts/reset-password/:token → ResetPassword (public)
/accounts/users                 → UserManagement (admin)
/accounts/users/create          → CreateUser (admin)
/accounts/users/:id/edit        → EditUser (admin)
/profile                        → Profile (connecté)
/dashboard                      → Dashboard principal
/chatbot                        → Chatbot IA
```

---

## 15. FLUX COMPLETS (pour la soutenance)

### Flux Login
```
1. Navigateur → GET /login → Django → serve_react → index.html
2. React charge, render Login.jsx
3. User soumet formulaire → POST /accounts/login/ (JSON)
4. login_view : authenticate() → login() → AuditLog.log(LOGIN)
5. Réponse JSON : {success, user, must_change_password, redirect}
6. React → AuthContext.login() → stocke user → navigue vers /dashboard
7. Si must_change_password → navigue vers /accounts/change-password
```

### Flux Chatbot Question
```
1. User tape question → POST /chatbot/ask/ (JSON)
2. ask_view : crée/reprend ChatSession
3. Appelle rag_pipeline.ask() → Ollama LLM local
4. Si _stop_requests contient user.id → retourne {stopped: True}
5. Sinon → sauvegarde ChatMessage, AuditLog(CHATBOT_QUESTION)
6. Cherche commentaires publics similaires (related_comments)
7. Retourne {answer, chart_data, suggestions, related_comments}
```

### Flux Upload Fichier
```
1. POST /ingestion/upload/ → Django → UploadedFile(status=pending)
2. AuditLog(UPLOAD_FILE), copie vers OneDrive si configuré
3. Celery task process_uploaded_file.delay(id) → parsing async
4. Parser extrait le texte → rag_pipeline.index_document() → ChromaDB
5. UploadedFile.status = 'success' (ou 'error')
```

### Flux Maintenance
```
1. Admin → POST /api/maintenance/toggle/ → SiteConfiguration.maintenance_mode = True
2. Prochaine requête utilisateur → MaintenanceMiddleware intercepte
3. API/JSON → 503 JSON {"detail": "maintenance"}
4. Page HTML → redirect /maintenance (React SPA affiche page maintenance)
5. React appelle GET /api/maintenance/status/ au démarrage → détecte maintenance
```

---

## 16. POINTS CLÉS À RETENIR POUR LA SOUTENANCE

| Point | Détail |
|---|---|
| Base de données | **Deux bases** : Django app (SQL Server) + Data Warehouse SQL Server (lecture seule, `managed=False`) |
| Authentification | Sessions Django (cookie `sessionid`) + CSRF token. Pas de JWT. |
| LLM | Ollama local — aucune donnée ne sort du réseau MARETAP |
| Asynchrone | Celery + Redis pour le traitement des fichiers uploadés |
| Sécurité session | Timeout 30 min + ForcePasswordChange + AuditLog |
| Architecture frontend | React SPA — Django ne génère aucune page HTML métier |
| Maintenance | Singleton `SiteConfiguration` + Middleware qui intercepte toutes les requêtes |
| Traçabilité | `AuditLog.log()` appelé partout — login, logout, upload, chatbot, export, session expirée |
| Rôles | `admin` ou `user` — vérifié via `request.user.role != 'admin'` dans les API JSON |
