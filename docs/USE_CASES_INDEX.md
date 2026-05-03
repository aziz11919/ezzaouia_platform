# EZZAOUIA Platform - Use Cases Index

Ce dossier contient les 12 diagrammes de cas d'utilisation (UC01 a UC12) pour le rapport.

## Diagramme global

```mermaid
flowchart LR
  Admin[Admin]
  User[User]
  Celery[Celery Worker]
  LLM[Ollama LLM]
  BI[Power BI]

  subgraph EZ[EZZAOUIA Platform]
    UC01([UC01 Authentication])
    UC02([UC02 User Management])
    UC03([UC03 File Ingestion])
    UC04([UC04 RAG Chatbot])
    UC05([UC05 Session Sharing])
    UC06([UC06 Production Analytics])
    UC07([UC07 Forecasting])
    UC08([UC08 Report Generation])
    UC09([UC09 Document Library])
    UC10([UC10 Audit Trail])
    UC11([UC11 Warehouse Data])
    UC12([UC12 User Memory])
  end

  User --> UC01
  User --> UC03
  User --> UC04
  User --> UC05
  User --> UC06
  User --> UC07
  User --> UC08
  User --> UC09
  User --> UC11
  User --> UC12

  Admin --> UC01
  Admin --> UC02
  Admin --> UC03
  Admin --> UC04
  Admin --> UC05
  Admin --> UC06
  Admin --> UC07
  Admin --> UC08
  Admin --> UC09
  Admin --> UC10
  Admin --> UC11
  Admin --> UC12

  Celery --> UC03
  LLM --> UC04
  LLM --> UC12
  BI --> UC06
  BI --> UC11
```

## Liste des fichiers

1. [UC01_authentication.md](UC01_authentication.md)
2. [UC02_user_management.md](UC02_user_management.md)
3. [UC03_file_ingestion.md](UC03_file_ingestion.md)
4. [UC04_rag_chatbot.md](UC04_rag_chatbot.md)
5. [UC05_session_sharing.md](UC05_session_sharing.md)
6. [UC06_production_analytics.md](UC06_production_analytics.md)
7. [UC07_forecasting.md](UC07_forecasting.md)
8. [UC08_report_generation.md](UC08_report_generation.md)
9. [UC09_document_library.md](UC09_document_library.md)
10. [UC10_audit_trail.md](UC10_audit_trail.md)
11. [UC11_warehouse_data.md](UC11_warehouse_data.md)
12. [UC12_user_memory.md](UC12_user_memory.md)

## Couverture pour rapport

- 12/12 fichiers UC presents
- 12/12 diagrammes UC presents
- 1 diagramme global present dans cet index
