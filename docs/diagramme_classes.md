# Diagramme de Classes — EZZAOUIA Platform

## 1. Diagramme de Classes Global

```mermaid
classDiagram
    direction TB

    %% ══════════════════════════════════════════
    %% CORE — Modèle abstrait de base
    %% ══════════════════════════════════════════
    class BaseModel {
        <<abstract>>
        +DateTimeField created_at
        +DateTimeField updated_at
    }

    %% ══════════════════════════════════════════
    %% ACCOUNTS — Gestion des utilisateurs
    %% ══════════════════════════════════════════
    class User {
        +CharField role
        +CharField department
        +CharField phone
        +BooleanField must_change_password
        +CharField password_reset_token
        +DateTimeField password_reset_expires
        +DateTimeField last_password_change
        +is_admin() bool
        +is_ingenieur() bool
        +is_direction() bool
    }

    class Role {
        <<enumeration>>
        ADMIN
        INGENIEUR
        DIRECTION
    }

    User --> Role : role

    %% ══════════════════════════════════════════
    %% INGESTION — Upload et traitement fichiers
    %% ══════════════════════════════════════════
    class UploadedFile {
        +FileField file
        +CharField original_name
        +CharField file_type
        +CharField status
        +ForeignKey uploaded_by
        +TextField error_msg
        +IntegerField rows_extracted
    }

    class FileType {
        <<enumeration>>
        PDF
        DOCX
        XLSX
    }

    class FileStatus {
        <<enumeration>>
        PENDING
        PROCESSING
        SUCCESS
        ERROR
    }

    UploadedFile --|> BaseModel
    UploadedFile --> FileType : file_type
    UploadedFile --> FileStatus : status
    UploadedFile --> User : uploaded_by

    %% ══════════════════════════════════════════
    %% CHATBOT — Sessions, Messages, Mémoire
    %% ══════════════════════════════════════════
    class ChatSession {
        +ForeignKey user
        +CharField title
        +BooleanField is_active
        +CharField share_token
        +BooleanField is_shared
        +DateTimeField shared_at
        +ForeignKey shared_by
        +get_first_question() str
    }

    class ChatMessage {
        +ForeignKey session
        +TextField question
        +TextField answer
        +FloatField duration
        +FloatField duration_seconds
        +BooleanField is_satisfied
    }

    class AnalysisComment {
        +ForeignKey message
        +ForeignKey author
        +TextField content
        +BooleanField is_public
    }

    class SessionShare {
        +ForeignKey session
        +ForeignKey shared_by
        +ForeignKey shared_with
        +BooleanField viewed
    }

    class UserMemory {
        +ForeignKey user
        +CharField well_code
        +CharField topic
        +TextField summary
    }

    class TopicChoices {
        <<enumeration>>
        PRODUCTION
        BUDGET
        WORKOVER
        RESERVOIR
        GENERAL
    }

    ChatSession --|> BaseModel
    ChatMessage --|> BaseModel
    AnalysisComment --|> BaseModel
    SessionShare --|> BaseModel
    UserMemory --|> BaseModel

    ChatSession --> User : user
    ChatSession --> User : shared_by
    ChatSession "1" --o "*" ChatMessage : messages
    ChatMessage "1" --o "*" AnalysisComment : comments
    AnalysisComment --> User : author
    SessionShare --> ChatSession : session
    SessionShare --> User : shared_by
    SessionShare --> User : shared_with
    UserMemory --> User : user
    UserMemory --> TopicChoices : topic

    %% ══════════════════════════════════════════
    %% AUDIT — Journal d'activités
    %% ══════════════════════════════════════════
    class AuditLog {
        +ForeignKey user
        +CharField action
        +TextField details
        +GenericIPAddressField ip_address
        +TextField user_agent
        +DateTimeField created_at
        +log() AuditLog
        +get_client_ip() str
        +parsed_details() dict
        +details_display() str
        +duration_seconds() float
        +duration_display() str
    }

    class AuditAction {
        <<enumeration>>
        LOGIN
        LOGOUT
        UPLOAD_FILE
        CHATBOT_QUESTION
        EXPORT_PDF
        EXPORT_EXCEL
        VIEW_PAGE
        DELETE_SESSION
        SESSION_EXPIRED
    }

    AuditLog --> User : user
    AuditLog --> AuditAction : action

    %% ══════════════════════════════════════════
    %% REPORTS — Anomalies et génération PDF
    %% ══════════════════════════════════════════
    class Anomalie {
        +CharField well_code
        +CharField anomaly_type
        +CharField severity
        +TextField description
        +DateTimeField detected_at
        +CharField status
    }

    class EzzaouiaReportGenerator {
        -BytesIO buffer
        -Canvas canvas
        -Color primary_red
        +generate_monthly_report(year, month, role) BytesIO
        -_draw_cover_page()
        -_draw_executive_page()
        -_draw_wells_page()
        -_draw_trend_page()
        -_draw_anomalies_page()
    }

    EzzaouiaReportGenerator ..> Anomalie : utilise
    EzzaouiaReportGenerator ..> DimWell : utilise
```

---

## 2. Diagramme de Classes — Data Warehouse (Star Schema)

```mermaid
classDiagram
    direction TB

    %% ══════════════════════════════════════════
    %% DIMENSIONS
    %% ══════════════════════════════════════════
    class DimDate {
        +IntegerField datekey [PK]
        +DateField fulldate
        +SmallIntegerField day
        +SmallIntegerField month
        +SmallIntegerField year
        +SmallIntegerField quarter
        +CharField monthname
    }

    class DimWell {
        +AutoField wellkey [PK]
        +CharField wellcode
        +CharField libelle
        +CharField layer
        +CharField closed
        +IntegerField maxprod
        +CharField affichable
        +IntegerField ordre
        +ForeignKey powertypekey
        +ForeignKey prodmethodkey
        +ForeignKey typewellkey
        +is_active() bool
    }

    class DimPowerType {
        +AutoField powertypekey [PK]
        +IntegerField powertypecode
        +CharField powertypename
    }

    class DimProdMethod {
        +AutoField prodmethodkey [PK]
        +IntegerField prodmethodcode
        +CharField prodmethodname
    }

    class DimTypeWell {
        +AutoField typewellkey [PK]
        +IntegerField typewellcode
        +CharField typewellname
    }

    class DimTank {
        +AutoField tankkey [PK]
        +CharField tankcode
        +CharField tankname
    }

    %% ══════════════════════════════════════════
    %% TABLES DE FAITS
    %% ══════════════════════════════════════════
    class FactDailyProduction {
        +AutoField factprodkey [PK]
        +ForeignKey wellkey
        +ForeignKey datekey
        +IntegerField dailyoilprodstbd
        +IntegerField dailywaterprodblsd
        +IntegerField dailygasprodmscf
        +DecimalField prodhours
        +IntegerField flowtempdegf
        +DecimalField bsw
        +DecimalField wellstatuswaterbwpd
        +IntegerField gorscfstb
        +IntegerField cumoilstbcorrected
        +IntegerField cumwaterbbls
        +IntegerField cumgasmscf
        +DecimalField sales
        +DecimalField fuel
        +IntegerField lifting
    }

    class FactTankLevel {
        +AutoField facttankkey [PK]
        +ForeignKey tankkey
        +ForeignKey datekey
        +IntegerField volumebbls
    }

    class FactWellTest {
        +AutoField facttestkey [PK]
        +ForeignKey wellkey
        +ForeignKey datekey
        +IntegerField testhours
        +IntegerField oilbopd
        +DecimalField waterbwpd
        +IntegerField gasmscfd
        +IntegerField gor
    }

    %% ══════════════ RELATIONS ═══════════════
    DimWell --> DimPowerType : powertypekey
    DimWell --> DimProdMethod : prodmethodkey
    DimWell --> DimTypeWell : typewellkey

    FactDailyProduction --> DimWell : wellkey
    FactDailyProduction --> DimDate : datekey

    FactTankLevel --> DimTank : tankkey
    FactTankLevel --> DimDate : datekey

    FactWellTest --> DimWell : wellkey
    FactWellTest --> DimDate : datekey
```

---

## 3. Diagramme de Classes — Services & Pipeline RAG

```mermaid
classDiagram
    direction LR

    class RAGPipeline {
        -OllamaLLM _llm
        -SentenceTransformerEmbeddings _embeddings
        -dict _vectorstores
        -Chroma _global_vectorstore
        +get_llm() OllamaLLM
        +get_embeddings() Embeddings
        +get_vectorstore_for_doc(doc_id) Chroma
        +get_global_vectorstore() Chroma
        +index_document(text, metadata, doc_id) int
        +retrieve_smart(query, doc_id, filename, k) list
        +get_available_documents() list
        +normalize_well_code(text) DimWell
        +get_sql_context(question) str
        +detect_chart_request(question) bool
        +build_chart_data(question) dict
        +detect_language(text) str
        +generate_suggestions(question, well, lang) list
        +ask(question, history, doc_ids, filename, user) dict
    }

    class MemoryManager {
        +get_user_memory(user) str
        +update_user_memory(user, question, answer, well) void
    }

    class KPICalculators {
        +get_field_production_summary(year, month) dict
        +get_well_kpis(well_key, year, month) list
        +get_monthly_trend(year, well_key) list
        +get_well_test_kpis(well_key, year) list
        +get_top_producers(limit, year, month) list
        +get_cumulative_production(well_key) dict
    }

    class Parsers {
        +parse_excel(filepath) tuple
        +parse_pdf(filepath) tuple
        +parse_word(filepath) tuple
    }

    class CeleryTasks {
        +process_uploaded_file(file_id) str
    }

    class AuditMiddleware {
        -tuple SKIP_PREFIXES
        +__call__(request) response
        -_log_request(request, response, started_at)
        -_resolve_action(request, response, path, duration_ms)
        -_detect_export_action(request, response, path)
    }

    RAGPipeline ..> MemoryManager : utilise
    RAGPipeline ..> KPICalculators : get_sql_context
    RAGPipeline ..> DimWell : normalize_well_code
    CeleryTasks ..> Parsers : parse fichiers
    CeleryTasks ..> RAGPipeline : index_document
    AuditMiddleware ..> AuditLog : log actions
    EzzaouiaReportGenerator ..> KPICalculators : données KPI
```
