# Diagrammes de Séquence — EZZAOUIA Platform

## 1. Authentification (Login / Logout)

```mermaid
sequenceDiagram
    autonumber
    actor U as Utilisateur
    participant B as Navigateur
    participant V as login_view
    participant Auth as Django Auth
    participant AL as AuditLog
    participant DB as Base de données

    U->>B: Saisir identifiants
    B->>V: POST /accounts/login/
    V->>Auth: authenticate(username, password)
    Auth->>DB: SELECT User WHERE username=...
    DB-->>Auth: User ou None

    alt Authentification réussie
        Auth-->>V: User valide
        V->>Auth: login(request, user)
        V->>AL: log(LOGIN, user, request)
        AL->>DB: INSERT AuditLog

        alt must_change_password = True
            V-->>B: redirect → /accounts/change-password/
            B-->>U: Page changement mot de passe
        else Mot de passe OK
            V-->>B: redirect → /dashboard/
            B-->>U: Tableau de bord
        end

    else Authentification échouée
        Auth-->>V: None
        V-->>B: Erreur "Identifiants incorrects"
        B-->>U: Message d'erreur
    end
```

---

## 2. Ingestion de Fichiers (Upload + Traitement Celery)

```mermaid
sequenceDiagram
    autonumber
    actor U as Utilisateur
    participant B as Navigateur
    participant V as upload_view
    participant DB as Base de données
    participant AL as AuditLog
    participant OD as OneDrive
    participant CQ as Celery Queue
    participant T as process_uploaded_file
    participant P as Parsers
    participant RAG as RAG Pipeline
    participant CS as ChromaDB

    U->>B: Sélectionner fichier (PDF/DOCX/XLSX)
    B->>V: POST /ingestion/upload/ + fichier
    V->>V: Valider extension

    alt Extension non supportée
        V-->>B: Erreur "Format non supporté"
        B-->>U: Message d'erreur
    else Extension valide
        V->>DB: CREATE UploadedFile(status=PENDING)
        DB-->>V: uploaded_file.id
        V->>AL: log(UPLOAD_FILE, filename, status)
        AL->>DB: INSERT AuditLog

        opt OneDrive configuré
            V->>OD: shutil.copy2(fichier)
        end

        V->>CQ: process_uploaded_file.delay(file_id)
        V-->>B: redirect → /ingestion/list/
        B-->>U: "Fichier uploadé — traitement en cours..."

        Note over CQ,T: Traitement asynchrone Celery

        CQ->>T: Exécuter tâche
        T->>DB: UPDATE status = PROCESSING

        alt Fichier XLSX
            T->>P: parse_excel(filepath)
            P-->>T: records[], error
        else Fichier PDF
            T->>P: parse_pdf(filepath)
            P-->>T: text, error
        else Fichier DOCX
            T->>P: parse_word(filepath)
            P-->>T: text, error
        end

        alt Erreur de parsing
            T->>DB: UPDATE status = ERROR, error_msg
        else Parsing réussi
            opt PDF ou DOCX
                T->>RAG: index_document(text, metadata, doc_id)
                RAG->>RAG: split_text → chunks
                RAG->>CS: add_documents(chunks) [doc store]
                RAG->>CS: add_documents(chunks) [global store]
                CS-->>RAG: OK
                RAG-->>T: nb_chunks
            end
            T->>DB: UPDATE status = SUCCESS, rows_extracted
        end
    end
```

---

## 3. Chatbot — Question RAG avec Mémoire

```mermaid
sequenceDiagram
    autonumber
    actor U as Utilisateur
    participant B as Navigateur
    participant V as ask_view
    participant DB as Base de données
    participant RAG as RAG Pipeline
    participant CS as ChromaDB
    participant SQL as SQL Context
    participant KPI as KPI Calculators
    participant DWH as Data Warehouse
    participant MEM as Memory Manager
    participant LLM as Ollama LLM
    participant AL as AuditLog

    U->>B: Poser une question
    B->>V: POST /chatbot/ask/ {question, session_id, doc_ids}

    alt Pas de session existante
        V->>DB: CREATE ChatSession(user, title)
        DB-->>V: session
    else Session existante
        V->>DB: GET ChatSession(id)
        DB-->>V: session
    end

    V->>DB: GET messages de la session (historique)
    DB-->>V: history[]

    V->>RAG: ask(question, history, doc_ids, user)

    RAG->>RAG: detect_language(question) → lang

    alt Salutation détectée
        RAG-->>V: greeting message
    else Question technique
        RAG->>RAG: normalize_well_code(question) → well?

        RAG->>CS: retrieve_smart(query, doc_id, filename, k=6)
        CS-->>RAG: doc_results[]

        RAG->>SQL: get_sql_context(question)
        SQL->>KPI: get_field_production_summary()
        SQL->>KPI: get_top_producers()
        SQL->>KPI: get_well_kpis()
        SQL->>KPI: get_monthly_trend()
        KPI->>DWH: SELECT ... FROM FactDailyProduction
        DWH-->>KPI: résultats agrégés
        KPI-->>SQL: données formatées
        SQL-->>RAG: sql_context

        RAG->>MEM: get_user_memory(user)
        MEM->>DB: SELECT UserMemory WHERE user=...
        DB-->>MEM: memories[]
        MEM-->>RAG: memory_context

        RAG->>RAG: Construire prompt expert
        RAG->>LLM: invoke(prompt)
        LLM-->>RAG: réponse texte

        opt Graphique détecté
            RAG->>RAG: build_chart_data(question)
        end

        RAG->>RAG: generate_suggestions(question, well, lang)
        RAG->>MEM: update_user_memory(user, question, answer, well)
        MEM->>DB: UPDATE/CREATE UserMemory

        RAG-->>V: {answer, chart_data, suggestions}
    end

    V->>DB: CREATE ChatMessage(session, question, answer, duration)
    V->>AL: log(CHATBOT_QUESTION, question, duration)
    AL->>DB: INSERT AuditLog

    V-->>B: JSON {answer, chart_data, suggestions, session_id}
    B-->>U: Afficher réponse + graphique + suggestions
```

---

## 4. Génération de Rapports PDF

```mermaid
sequenceDiagram
    autonumber
    actor U as Utilisateur
    participant B as Navigateur
    participant V as generate_report
    participant RPT as EzzaouiaReportGenerator
    participant KPI as KPI Calculators
    participant DWH as Data Warehouse
    participant ANO as Anomalie Model
    participant DB as Base de données
    participant AL as AuditLog

    U->>B: Sélectionner année/mois + cliquer "Télécharger"
    B->>V: GET /reports/generate/?year=2024&month=9&download=1

    V->>V: Vérifier rôle utilisateur

    alt Rôle non autorisé
        V-->>B: 403 Forbidden
    else Rôle autorisé
        V->>RPT: EzzaouiaReportGenerator()
        V->>RPT: generate_monthly_report(year, month, role)

        RPT->>KPI: get_field_production_summary(year, month)
        KPI->>DWH: SELECT SUM/AVG ... FROM FactDailyProduction
        DWH-->>KPI: résumé production
        KPI-->>RPT: current_summary

        RPT->>KPI: get_field_production_summary(prev_year, prev_month)
        KPI-->>RPT: previous_summary

        RPT->>ANO: Anomalie.objects.filter(detected_at__date)
        ANO->>DB: SELECT * FROM Anomalie
        DB-->>ANO: anomalies[]
        ANO-->>RPT: month_anomalies

        RPT->>KPI: get_top_producers(limit=16)
        KPI-->>RPT: ranking_rows

        RPT->>KPI: get_monthly_trend(year)
        KPI-->>RPT: trend_rows

        RPT->>RPT: _draw_cover_page()

        opt Rôle = direction ou admin
            RPT->>RPT: _draw_executive_page()
        end

        RPT->>RPT: _draw_wells_page()

        opt Rôle = ingenieur
            RPT->>RPT: _draw_trend_page()
        end

        RPT->>RPT: _draw_anomalies_page()
        RPT-->>V: BytesIO (PDF buffer)

        V->>AL: log(EXPORT_PDF, year, month, role)
        AL->>DB: INSERT AuditLog

        V-->>B: HttpResponse (PDF attachment)
        B-->>U: Téléchargement du rapport PDF
    end
```

---

## 5. Partage de Session Chatbot

```mermaid
sequenceDiagram
    autonumber
    actor U1 as Utilisateur A
    actor U2 as Utilisateur B
    participant B as Navigateur
    participant V as share_session
    participant SV as shared_session_view
    participant DB as Base de données

    U1->>B: Cliquer "Partager" sur une session
    B->>V: POST /chatbot/session/{id}/share/ {user_ids: [U2.id]}

    V->>DB: GET ChatSession WHERE id, user=U1
    DB-->>V: session

    V->>V: Générer share_token (secrets.token_hex)
    V->>DB: UPDATE ChatSession (share_token, is_shared=True, shared_at)

    loop Pour chaque user_id
        V->>DB: GET User WHERE id=user_id, is_active=True
        V->>DB: GET_OR_CREATE SessionShare(session, shared_with, shared_by)
    end

    V-->>B: JSON {share_url, shared_count}
    B-->>U1: Lien de partage affiché

    Note over U2: Plus tard...

    U2->>B: Ouvrir lien /chatbot/shared/{token}/
    B->>SV: GET /chatbot/shared/{token}/
    SV->>DB: GET ChatSession WHERE share_token, is_shared=True
    DB-->>SV: session + messages
    SV-->>B: Rendu page lecture seule
    B-->>U2: Consultation de la conversation partagée
```

---

## 6. Gestion des Utilisateurs (Admin)

```mermaid
sequenceDiagram
    autonumber
    actor A as Admin
    participant B as Navigateur
    participant V as create_user
    participant DB as Base de données
    participant EM as Email Service
    participant AL as AuditLog

    A->>B: Remplir formulaire création utilisateur
    B->>V: POST /accounts/create-user/

    V->>V: Valider username, email (@maretap.tn), rôle

    alt Erreurs de validation
        V-->>B: Formulaire avec erreurs
        B-->>A: Messages d'erreur
    else Validation OK
        V->>V: generate_random_password()
        V->>DB: CREATE User(username, email, password, role, ...)
        DB-->>V: user créé

        V->>EM: send_welcome_email(user, plain_password)

        alt Email envoyé
            EM-->>V: OK
            V-->>B: "Utilisateur créé. Mot de passe envoyé par email."
        else Échec email
            EM-->>V: Exception
            V-->>B: "Utilisateur créé mais email échoué. MDP: xxx"
        end

        V->>AL: log(CREATE_USER, created_user, role)
        AL->>DB: INSERT AuditLog

        V-->>B: redirect → /accounts/users/
        B-->>A: Liste des utilisateurs
    end
```

---

## 7. Bibliothèque documentaire

```mermaid
sequenceDiagram
    autonumber
    actor U as Utilisateur
    participant B as Navigateur
    participant V as bibliotheque
    participant DV as delete_document
    participant DB as Base de données
    participant FS as Système de fichiers
    participant CS as ChromaDB

    U->>B: Accéder à la bibliothèque
    B->>V: GET /bibliotheque/ ?q=&type=&year=&well=
    V->>DB: SELECT UploadedFile WHERE status=success + filtres
    DB-->>V: page_docs (paginé 15/page)
    V->>V: Calculer taille fichier, permissions suppression
    V-->>B: Rendu page bibliothèque
    B-->>U: Liste des documents avec stats

    Note over U: Suppression d'un document

    U->>B: Cliquer "Supprimer" sur un document
    B->>DV: POST /bibliotheque/delete/{pk}/
    DV->>DB: GET UploadedFile(pk)
    DV->>DV: Vérifier permission (admin ou propriétaire)

    alt Permission refusée
        DV-->>B: 403 "Permission refusée"
    else Permission OK
        DV->>FS: os.remove(file.path)
        DV->>CS: shutil.rmtree(chroma_db/doc_{pk})
        DV->>DB: DELETE UploadedFile
        DV-->>B: JSON {success: true}
        B-->>U: Document supprimé
    end
```
