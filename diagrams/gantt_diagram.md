# Gantt Chart — EZZAOUIA Platform PFE Timeline

> **Project:** EZZAOUIA Platform — MARETAP S.A.
> **Student:** Aziz (Stage PFE)
> **Period:** February 2026 – June 2026
> **Stack:** Django 4.2 · React · SQL Server DWH · Ollama LLM · ChromaDB · Docker

```mermaid
gantt
    title EZZAOUIA Platform — PFE Timeline — MARETAP S.A.
    dateFormat  YYYY-MM-DD
    axisFormat  %d %b
    todayMarker on

    section 📋 Analysis & Design
    Study existing system & business requirements    :done,    a1, 2026-02-01, 7d
    Design DWH star/snowflake schema                 :done,    a2, 2026-02-06, 8d
    Application architecture (Django + React + RAG)  :done,    a3, 2026-02-12, 7d

    section 🗄️ Data Warehouse (SQL Server)
    Dimension tables — DimDate, DimWell, DimTank     :done,    d1, 2026-02-14, 7d
    Dimension tables — DimWellStatus, DimPowerType   :done,    d2, 2026-02-18, 7d
    Fact table — FactProduction                       :done,    d3, 2026-02-21, 10d
    Fact table — FactTankLevel                        :done,    d4, 2026-02-25, 7d
    ETL Talend — DimWellStatus load                  :done,    d5, 2026-03-01, 10d
    ETL Talend — FactProduction load                 :done,    d6, 2026-03-05, 14d
    ETL Talend — FactTankLevel load                  :done,    d7, 2026-03-10, 10d
    Data quality validation & cleaning               :done,    d8, 2026-03-14, 7d

    section ⚙️ Backend Django
    Django project setup + Docker compose            :done,    b1, 2026-03-07, 7d
    Models managed=False + DRF API endpoints         :done,    b2, 2026-03-14, 7d
    KPI calculators — BOPD, BSW, GOR, trends         :done,    b3, 2026-03-20, 10d
    Well status & top producers endpoints            :done,    b4, 2026-03-24, 8d
    Authentication RBAC + JWT + email reset          :done,    b5, 2026-03-21, 10d
    Celery tasks + Redis + ingestion pipeline        :done,    b6, 2026-04-01, 9d
    Audit logging system                             :done,    b7, 2026-04-05, 5d

    section 🤖 AI & RAG Pipeline
    Ollama LLM integration (llama3, local)           :done,    r1, 2026-04-01, 6d
    ChromaDB vector store — per-doc collections      :done,    r2, 2026-04-03, 5d
    RAG pipeline — SQL context enrichment            :done,    r3, 2026-04-07, 7d
    RAG pipeline — vector similarity search (MMR)   :done,    r4, 2026-04-08, 7d
    Chatbot sessions + history + stop generation    :done,    r5, 2026-04-10, 7d

    section ⚛️ Frontend React
    React + Vite + React Router + AuthContext        :done,    f1, 2026-04-01, 7d
    Dashboard — KPI cards + Chart.js (trend, top-5) :done,    f2, 2026-04-07, 8d
    Chatbot UI — sessions, messages, share, rename  :done,    f3, 2026-04-10, 10d
    Library + File Import + drag-drop upload         :done,    f4, 2026-04-14, 7d
    User Management + create + edit + delete         :done,    f5, 2026-04-17, 7d
    Reports page + PDF generation                    :done,    f6, 2026-04-14, 7d
    Audit log page + Stats page (Chart.js)           :done,    f7, 2026-04-17, 5d
    Dark/light mode — CSS variables                  :done,    f8, 2026-04-10, 5d
    Django templates → React SPA migration          :done,    f9, 2026-04-14, 14d

    section 🔗 Integration & Testing
    End-to-end integration testing                   :         t1, 2026-04-28, 10d
    Performance profiling & query optimization       :         t2, 2026-05-05, 9d
    Security review — CSRF, RBAC, input validation   :         t3, 2026-05-07, 7d
    Bug fixes & regression testing                   :         t4, 2026-05-12, 9d

    section 📝 Documentation & Delivery
    Technical documentation (architecture, APIs)     :         doc1, 2026-05-14, 14d
    User manual & deployment guide                   :         doc2, 2026-05-21, 10d
    PFE report writing                               :         doc3, 2026-05-14, 21d
    Final PFE presentation preparation               :         doc4, 2026-06-01, 14d
    Final PFE defense                                :milestone, m1, 2026-06-15, 0d
```
