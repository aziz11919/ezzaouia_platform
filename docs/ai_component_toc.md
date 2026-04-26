# Chapter 3: Development of the AI Component

---

## Table of Contents

3.1 Introduction . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . XX

3.2 Business Understanding . . . . . . . . . . . . . . . . . . . . . . . . . . XX

&nbsp;&nbsp;&nbsp;&nbsp;3.2.1 Business Needs and Objectives . . . . . . . . . . . . . . . . . . . . XX

&nbsp;&nbsp;&nbsp;&nbsp;3.2.2 Stakeholders . . . . . . . . . . . . . . . . . . . . . . . . . . . . . XX

&nbsp;&nbsp;&nbsp;&nbsp;3.2.3 Deployment Constraints . . . . . . . . . . . . . . . . . . . . . . . XX

&nbsp;&nbsp;&nbsp;&nbsp;3.2.4 Solution Strategy . . . . . . . . . . . . . . . . . . . . . . . . . . XX

&nbsp;&nbsp;&nbsp;&nbsp;3.2.5 Success Criteria . . . . . . . . . . . . . . . . . . . . . . . . . . . XX

3.3 Data Understanding . . . . . . . . . . . . . . . . . . . . . . . . . . . . XX

&nbsp;&nbsp;&nbsp;&nbsp;3.3.1 Data Sources . . . . . . . . . . . . . . . . . . . . . . . . . . . . . XX

&nbsp;&nbsp;&nbsp;&nbsp;3.3.2 Data Quality and Petroleum Keyword Validation . . . . . . . . . . . XX

&nbsp;&nbsp;&nbsp;&nbsp;3.3.3 Training Dataset Generation . . . . . . . . . . . . . . . . . . . . . XX

3.4 Data Preparation . . . . . . . . . . . . . . . . . . . . . . . . . . . . . XX

&nbsp;&nbsp;&nbsp;&nbsp;3.4.1 Text Extraction (PDF, DOCX, XLSX) . . . . . . . . . . . . . . . . . XX

&nbsp;&nbsp;&nbsp;&nbsp;3.4.2 Text Chunking . . . . . . . . . . . . . . . . . . . . . . . . . . . . XX

&nbsp;&nbsp;&nbsp;&nbsp;3.4.3 Embedding and Vectorization . . . . . . . . . . . . . . . . . . . . . XX

&nbsp;&nbsp;&nbsp;&nbsp;3.4.4 Document Domain Validation . . . . . . . . . . . . . . . . . . . . . XX

3.5 Modeling . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . XX

&nbsp;&nbsp;&nbsp;&nbsp;3.5.1 Embedding Model (all-MiniLM-L6-v2) . . . . . . . . . . . . . . . . XX

&nbsp;&nbsp;&nbsp;&nbsp;3.5.2 Vector Store (ChromaDB — per-document and global collections) . . . XX

&nbsp;&nbsp;&nbsp;&nbsp;3.5.3 SQL Context Enrichment . . . . . . . . . . . . . . . . . . . . . . . XX

&nbsp;&nbsp;&nbsp;&nbsp;3.5.4 Retrieval Strategy (MMR — k=6, lambda=0.6) . . . . . . . . . . . . XX

&nbsp;&nbsp;&nbsp;&nbsp;3.5.5 RAG Pipeline Architecture . . . . . . . . . . . . . . . . . . . . . . XX

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3.5.5.1 Prompt Construction and System Identity . . . . . . . . . . . XX

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3.5.5.2 LLM Integration (Ollama llama3.1:8b) . . . . . . . . . . . . XX

&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3.5.5.3 SQL vs Document Context Priority Logic . . . . . . . . . . . XX

&nbsp;&nbsp;&nbsp;&nbsp;3.5.6 Language Detection (French / English / Arabic) . . . . . . . . . . XX

&nbsp;&nbsp;&nbsp;&nbsp;3.5.7 Chart Data Generation . . . . . . . . . . . . . . . . . . . . . . . . XX

3.6 Evaluation . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . XX

&nbsp;&nbsp;&nbsp;&nbsp;3.6.1 User Satisfaction Rating . . . . . . . . . . . . . . . . . . . . . . XX

&nbsp;&nbsp;&nbsp;&nbsp;3.6.2 Response Quality via Team Annotations . . . . . . . . . . . . . . . XX

&nbsp;&nbsp;&nbsp;&nbsp;3.6.3 Multilingual Dataset Validation . . . . . . . . . . . . . . . . . . . XX

3.7 Deployment . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . XX

&nbsp;&nbsp;&nbsp;&nbsp;3.7.1 Ollama On-Premise Deployment . . . . . . . . . . . . . . . . . . . . XX

&nbsp;&nbsp;&nbsp;&nbsp;3.7.2 Celery Asynchronous Document Indexing . . . . . . . . . . . . . . . XX

&nbsp;&nbsp;&nbsp;&nbsp;3.7.3 Session Management and Audit Logging . . . . . . . . . . . . . . . XX

&nbsp;&nbsp;&nbsp;&nbsp;3.7.4 Persistent User Memory . . . . . . . . . . . . . . . . . . . . . . . XX

&nbsp;&nbsp;&nbsp;&nbsp;3.7.5 Fine-Tuning Dataset and Modelfile . . . . . . . . . . . . . . . . . XX

3.8 Conclusion . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . XX

---

## 3.1 Introduction

The AI component of the EZZAOUIA / MARETAP platform is a **Retrieval-Augmented Generation (RAG)
chatbot** that answers technical questions about the EZZAOUIA oil field (CPF Zarzis, Tunisia).
It combines real-time production data from the SQL Server data warehouse with domain documents
(PDF, Word, Excel) to produce structured, multilingual responses in the role of *Dr. EZZAOUIA —
Chief Petroleum Engineer*.

The component is implemented in `apps/chatbot/` and is tightly integrated with:
- `apps/ingestion/` — async document indexing pipeline (Celery)
- `apps/kpis/calculators.py` — SQL context provider
- `apps/warehouse/` — read-only DWH dimension and fact tables

---

## 3.2 Business Understanding

### 3.2.1 Business Needs and Objectives

| Problem | AI Solution |
|---------|------------|
| Engineers query production data through manual SQL reports | Conversational Q&A over live DWH data |
| PDF/Word technical reports are not searchable | Semantic document retrieval via ChromaDB |
| Decision-makers need instant field KPI summaries | Structured markdown responses with tables and recommendations |
| No access to cloud AI services (data confidentiality) | Fully local LLM via Ollama |

### 3.2.2 Stakeholders

Three user roles are defined in `apps/accounts/models.py`:

| Role | Access | AI Usage |
|------|--------|----------|
| `ADMIN` | Full platform | Session management, statistics, all shared sessions |
| `INGENIEUR` | Production + ingestion | Document upload, well analysis, RAG queries |
| `DIRECTION` | Reports + dashboard | Field KPI queries, shared session viewing |

### 3.2.3 Deployment Constraints

- **On-premise only**: No internet connection; all models run locally on the MARETAP server
- **Windows environment**: Celery requires `--pool=solo`; Memurai (Windows Redis) as broker
- **No GPU**: `all-MiniLM-L6-v2` embeddings run on CPU; Ollama serves `llama3.1:8b` on CPU
- **SQL Server**: `mssql-django` via ODBC Driver 18; raw T-SQL used in calculators to avoid ORM incompatibilities
- **Max upload**: 50 MB; accepted formats: PDF, DOCX, XLSX (`FILE_UPLOAD_MAX_MEMORY_SIZE`)

### 3.2.4 Solution Strategy

The solution combines two complementary data sources in every query:

1. **SQL context** — Live production numbers from the DWH (authoritative for numerical questions)
2. **Document context** — Semantic chunks from indexed PDF/DOCX files (qualitative reference only)

When both sources are available and the question is production-related, SQL data takes priority and document context is excluded from the prompt (`sql_has_data + has_production_question` guard in `ask()`).

### 3.2.5 Success Criteria

| Metric | Implementation |
|--------|---------------|
| Response accuracy | `ChatMessage.is_satisfied` (thumbs up/down, `rate_view`) |
| Response speed | `ChatMessage.duration_seconds` recorded on every exchange |
| Domain compliance | `is_petroleum_document()` rejects non-petroleum uploads |
| Multilingual coverage | FR / EN / AR validated via `training_data.jsonl` |

---

## 3.3 Data Understanding

### 3.3.1 Data Sources

**Source 1 — SQL Server Data Warehouse** (`apps/warehouse/`, `apps/kpis/calculators.py`)

| Table | Content |
|-------|---------|
| `FactProduction` | Daily oil/water/gas per well (1994–2025) |
| `DimWell` | Well inventory: code, name, layer, status (active/shut-in) |
| `DimWellStatus` | Operational data: BSW, GOR, ProdHours, pressures, temperatures |
| `FactTankLevel` | Daily tank storage volumes (BBL) |
| `DimDate` | Date dimension: Year, Month, FullDate |

**Source 2 — Indexed Document Corpus** (`apps/ingestion/`, ChromaDB)

- PDF reports, Word documents, Excel files uploaded via `apps/ingestion/`
- Stored in ChromaDB at `CHROMA_PERSIST_DIR` — one sub-directory per document (`doc_{id}`)
- A global collection `ezzaouia_global` aggregates all indexed content for cross-document search

### 3.3.2 Data Quality and Petroleum Keyword Validation

`is_petroleum_document(text)` in `rag_pipeline.py` checks a document against a 40-term
petroleum keyword list (MARETAP, BOPD, MSCF, STB, well, reservoir, workover, BSW, GOR, etc.).
A document is accepted only if **≥ 3 keywords** are found in the text.

Documents that fail this check are:
- **Rejected** during async ingestion (`status = 'rejected'`) and the file is deleted
- **Filtered** during chat-time inline uploads with a user-facing error message

### 3.3.3 Training Dataset Generation

A supervised training dataset is generated by `apps/chatbot/training/generate_dataset.py`
and saved as `apps/chatbot/training/training_data.jsonl`.

The dataset consists of structured Q&A pairs in **three languages** (French, English, Arabic)
covering every well in the field across 8 question types:

| Question Category | Example |
|------------------|---------|
| Average daily production | "What is the average BOPD of well EZZ1?" |
| BSW (water cut) | "What is the BSW of well EZZ2?" |
| GOR (gas-oil ratio) | "What is the GOR of well EZZ3?" |
| Operational status | "Is well EZZ4 active or shut-in?" |
| Cumulative production | "What is the total oil production of EZZ5?" |
| Production hours | "How many production hours does EZZ6 average?" |
| Reservoir layer | "What layer does EZZ7 produce from?" |
| Field comparison | "Compare well EZZ8 with field average" |

A companion `apps/chatbot/training/Modelfile` defines an Ollama custom model based on
`llama3.1:8b` with the Dr. EZZAOUIA system prompt, temperature 0.05, and context window 8192.

---

## 3.4 Data Preparation

### 3.4.1 Text Extraction (PDF, DOCX, XLSX)

Parsing is handled by `apps/ingestion/parsers.py`, called from two entry points:

| Entry Point | Trigger | Parser |
|------------|---------|--------|
| `process_uploaded_file` (Celery task) | File upload via ingestion module | `parse_pdf`, `parse_word`, `parse_excel` |
| `upload_chat_file` (chat inline upload) | User attaches a file in the chatbot UI | Same parsers, immediate processing |

- **PDF**: extracted via `parse_pdf()` — returns plain text with line count
- **DOCX**: extracted via `parse_word()` — returns plain text
- **XLSX**: extracted via `parse_excel()` — returns tabular records; not indexed into ChromaDB
  (Excel files are processed for row count only; RAG indexing applies to PDF and DOCX only)

### 3.4.2 Text Chunking

`index_document()` in `rag_pipeline.py` splits extracted text using
`RecursiveCharacterTextSplitter`:

```
chunk_size    = 800 characters
chunk_overlap = 150 characters
separators    = ["\n\n", "\n", ".", " "]
```

Each chunk becomes a `langchain.schema.Document` with metadata:
`filename`, `file_type`, `uploaded_by`, `doc_id`, `chunk_index`, `chunk_total`.

### 3.4.3 Embedding and Vectorization

Embeddings are computed by `get_embeddings()` using the
`SentenceTransformerEmbeddings` wrapper around `all-MiniLM-L6-v2` (384-dimensional, CPU).

The model is lazy-loaded as a module-level singleton (`_embeddings`) to avoid reloading
on every request. Chunks are stored in two ChromaDB collections simultaneously:

| Collection | Path | Purpose |
|-----------|------|---------|
| `doc_{md5[:12]}` | `CHROMA_PERSIST_DIR/doc_{id}/` | Isolated per-document retrieval |
| `ezzaouia_global` | `CHROMA_PERSIST_DIR/` | Cross-document global search |

### 3.4.4 Document Domain Validation

`is_petroleum_document(text)` acts as a domain gate applied **twice** in the pipeline:

1. **During async indexing** (`process_uploaded_file` task): document rejected before ChromaDB
   storage; file deleted from disk; `UploadedFile.status` set to `'rejected'`
2. **During query answering** (`ask()` function): if a `doc_id` is provided and the top-3
   retrieved chunks fail the petroleum check, the query is refused with an explanatory message

---

## 3.5 Modeling

### 3.5.1 Embedding Model (all-MiniLM-L6-v2)

| Property | Value |
|----------|-------|
| Model | `sentence-transformers/all-MiniLM-L6-v2` |
| Dimensions | 384 |
| Hardware | CPU (no GPU required) |
| Wrapper | `langchain_community.embeddings.SentenceTransformerEmbeddings` |
| Singleton | `_embeddings` module-level cache |

### 3.5.2 Vector Store (ChromaDB)

Two vector store configurations exist side-by-side:

**Per-document store** — `get_vectorstore_for_doc(doc_id)`:
- Path: `{CHROMA_PERSIST_DIR}/doc_{doc_id}/`
- Collection name: `doc_{md5(doc_id)[:12]}`
- Purpose: scoped retrieval when the user selects a specific document
- Cache: `_vectorstores` dict keyed by `doc_id`

**Global store** — `get_global_vectorstore()`:
- Path: `{CHROMA_PERSIST_DIR}/`
- Collection name: `ezzaouia_global`
- Purpose: fallback and cross-document search
- Cache: `_global_vectorstore` module-level singleton

### 3.5.3 SQL Context Enrichment

`get_sql_context(question)` in `rag_pipeline.py` injects live production numbers into the
prompt by routing keyword-matched queries to the appropriate KPI calculator function:

| Trigger Keywords | Calculator Called | Data Returned |
|-----------------|------------------|---------------|
| production, total, bopd, champ, field, kpi | `get_field_production_summary()` | avg_bopd, avg_bsw, avg_gor, total_oil, last_date |
| meilleur, top, classement, ranking, performers | `get_top_producers(limit=20)` | Ranked list of all active wells with BOPD, cumulative oil, BSW |
| Year patterns (e.g. 2024, 2023–2025) | `get_monthly_trend()` | Monthly STB + BSW breakdown for the detected period |
| Well code (EZZn) | `get_well_kpis()` + `get_monthly_trend()` | Full per-well KPIs + monthly history |
| wct, bsw, gor, reservoir | `get_field_production_summary()` + `get_top_producers()` | Reservoir analysis with per-well BSW ranking |
| tank, bac, stockage | `get_tank_levels()` | Latest tank volumes in BBL |
| statut, choke, tubing, casing, pressure | `get_well_status_kpis()` | Operational pressures, temperatures, ProdHours |
| liste, inventaire, all wells | `DimWell.objects.all()` | Full well inventory with status and layer |

Well code extraction uses `normalize_well_code()` which applies regex patterns
(`EZZ[-#]?\d+`, `EZ[-#]?\d+`) and resolves to a `DimWell` ORM object via
case-insensitive lookup.

### 3.5.4 Retrieval Strategy (MMR — k=6, lambda=0.6)

`retrieve_smart(query, doc_id, filename, k=6)` in `rag_pipeline.py` applies a
three-level fallback strategy:

```
1. If doc_id provided:
   → MMR search on per-document vectorstore
     (k=6, fetch_k=18, lambda_mult=0.6)
   → If results found: return immediately

2. If filename provided:
   → Similarity search on global vectorstore
     filtered by metadata["filename"] == filename

3. Fallback:
   → MMR search on global vectorstore
     (k=6, fetch_k=24, lambda_mult=0.5)
```

**MMR (Maximum Marginal Relevance)** balances relevance and diversity:
`lambda_mult=0.6` weights 60% relevance / 40% diversity to reduce redundant chunks.

The search query is augmented before retrieval by appending detected year and well code
context (e.g., `"EZZ11 workover intervention performance"`).

### 3.5.5 RAG Pipeline Architecture

The main orchestration function is `ask(question, history, doc_id, doc_ids, filename, user)`
in `rag_pipeline.py`. The execution flow is:

```
1. Detect language (FR/EN/AR)
2. Handle greetings (early return)
3. Augment search query with year/well context
4. retrieve_smart() → doc_results (up to 6 chunks)
5. get_sql_context() → sql_context (live DWH data)
6. If production question + SQL has data → clear doc_context
7. Inject last conversation turn (history[-1])
8. get_user_memory(user) → persistent memory context
9. Build final prompt with SYSTEM_PROMPT + all contexts
10. OllamaLLM.invoke(prompt) → answer
11. build_chart_data() if chart request detected
12. generate_suggestions() → 3 follow-up questions
13. update_user_memory(user, question, answer)
14. Return {answer, chart_data, suggestions}
```

#### 3.5.5.1 Prompt Construction and System Identity

The system prompt (`SYSTEM_PROMPT`) establishes the AI persona as *Dr. EZZAOUIA,
Chief Petroleum Engineer, MARETAP S.A., CPF Zarzis, Tunisia — 35 years experience*.

The prompt enforces **three structured response templates** (Case A/B/C) selected by
question type:

| Case | Trigger | Response Structure |
|------|---------|-------------------|
| A | Well ranking / top producers | Ranked table + Technical Analysis + Critical Alerts + Recommendations |
| B | Global field KPIs (WCT, GOR, BSW) | KPI table + Reservoir Analysis + Recommendations |
| C | Single well deep analysis | Performance Summary + Monthly History + Decline Analysis + Interventions |

15 absolute rules are enforced in the prompt (units, number formatting, BSW > 80% flagging,
GOR = 0 handling, shut-in wells, source citation with date).

#### 3.5.5.2 LLM Integration (Ollama llama3.1:8b)

| Parameter | Value |
|-----------|-------|
| Model | `llama3.1:8b` (configurable via `OLLAMA_MODEL`) |
| Base URL | `http://127.0.0.1:11434` (configurable via `OLLAMA_BASE_URL`) |
| Temperature | 0.05 (near-deterministic) |
| Context window | 8192 tokens |
| Max tokens | 3000 |
| Top-p | 0.85 |
| Repeat penalty | 1.15 |
| Timeout | 240 seconds |

The LLM is lazy-loaded as a module-level singleton (`_llm`) via `get_llm()`.

#### 3.5.5.3 SQL vs Document Context Priority Logic

When both SQL data and document chunks are available, the pipeline decides which to include:

```python
sql_has_data = len(sql_context.strip()) > 50
has_production_question = any(w in question for w in production_keywords)

if sql_has_data and has_production_question:
    doc_context = ""   # documents excluded — SQL is authoritative
```

`production_keywords` covers 20 terms: top, bopd, stb, well, puits, huile, bsw, gor, wct,
champ, field, kpi, performance, reservoir, etc.

### 3.5.6 Language Detection (French / English / Arabic)

`detect_language(text)` in `rag_pipeline.py`:

1. **Arabic**: Unicode range `؀–ۿ` (immediate detection)
2. **French vs English**: scored word list matching (9 FR words, 10 EN words)
3. **Default**: French

The detected language controls:
- `langue_nom` injected into the prompt (`RESPONSE LANGUAGE: français / English / عربي`)
- `generate_suggestions()` — follow-up questions generated in the same language
- Greeting responses hardcoded in FR / EN / AR

### 3.5.7 Chart Data Generation

`build_chart_data(question)` produces a **Chart.js-compatible JSON object** when the question
contains temporal/visual keywords (évolution, historique, graphique, trend, chart, etc.)
AND a well code is detected.

```
Output structure:
{
  "well_code": "EZZ11",
  "well_name": "...",
  "labels": ["Janvier 2024", "Février 2024", ...],
  "datasets": [
    { "label": "Oil Production (STB)", "type": "bar",  "yAxisID": "y"  },
    { "label": "BSW (%)",              "type": "line", "yAxisID": "y1" }
  ]
}
```

`parse_date_range(question)` extracts French month names and year patterns to determine
the chart time range. `detect_chart_request(question)` returns `True` only when both
a chart keyword and a valid well code are present.

---

## 3.6 Evaluation

### 3.6.1 User Satisfaction Rating

Every chatbot response can be rated via `rate_view` (POST `/chatbot/rate/`).
The rating is stored as `ChatMessage.is_satisfied` (Boolean, nullable):

| Value | Meaning |
|-------|---------|
| `True` | Thumbs up — answer was correct and useful |
| `False` | Thumbs down — answer was incorrect or unhelpful |
| `None` | Not yet rated (default) |

This field can be aggregated to compute per-session and global satisfaction rates.
Response latency is tracked separately in `ChatMessage.duration_seconds`.

### 3.6.2 Response Quality via Team Annotations

`AnalysisComment` model allows any authenticated user to annotate a chatbot answer:

- `is_public=True` — visible to all users (team knowledge)
- `is_public=False` — private note for the author only

Public comments on similar past questions are retrieved and appended to the API response
(`related_comments` field), enabling implicit peer review of AI answers.

### 3.6.3 Multilingual Dataset Validation

`apps/chatbot/training/training_data.jsonl` provides a ground-truth reference dataset
of correct answers per well, per question type, in all three supported languages.
Each entry has `{"prompt": "...", "response": "..."}` in JSONL format.

This dataset can be used to:
- Validate LLM response format and content accuracy
- Fine-tune a custom Ollama model using the companion `Modelfile`
- Regression-test the RAG pipeline after model or prompt changes

---

## 3.7 Deployment

### 3.7.1 Ollama On-Premise Deployment

Ollama runs as a local HTTP service on the MARETAP Windows server:

| Configuration | Value |
|--------------|-------|
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` (`.env` configurable) |
| `OLLAMA_MODEL` | `llama3.1:8b` (`.env` configurable) |
| Fine-tuned variant | Defined in `apps/chatbot/training/Modelfile` |

The `Modelfile` derives from `llama3.1:8b` and injects the Dr. EZZAOUIA system prompt
with production parameters (temperature 0.05, num_ctx 8192, num_predict 3000).

### 3.7.2 Celery Asynchronous Document Indexing

`process_uploaded_file` in `apps/ingestion/tasks.py` is a Celery shared task with:
- `max_retries=3`, `countdown=60` seconds between retries
- Full pipeline: parse → validate → index → update status

| Status | Meaning |
|--------|---------|
| `pending` | File received, task not yet started |
| `processing` | Task running — parsing and indexing in progress |
| `success` | Fully indexed in ChromaDB, ready for RAG queries |
| `error` | Parsing or indexing failed (error message stored in `error_msg`) |
| `rejected` | Domain validation failed — not a petroleum document |

Celery broker: **Memurai (Windows Redis)** on port 6379 (`redis://redis:6379/0`).
Result backend: `django-db` (SQL Server via `django_celery_results`).

### 3.7.3 Session Management and Audit Logging

**Chat sessions** (`ChatSession` model):
- Auto-created on first question if no session_id provided
- Title set to the first 60 characters of the opening question
- Empty sessions auto-deleted on `new_session` and `api_sessions` calls
- Limited to 30 sessions per user in the API response

**Audit logging** (`AuditLog.log`):
- Every chatbot question triggers an `AuditLog` entry with action `CHATBOT_QUESTION`
- Logged fields: question (truncated to 200 chars), response duration, session_id

**Stop generation** mechanism:
- `_stop_requests` in-memory set per Django worker process
- POST `/chatbot/stop/` adds the user ID to the set
- After `ask()` completes, the result is discarded if the user ID is in the set

**Session sharing**:
- `SessionShare` model enables user-to-user sharing with a `share_token` (UUID hex)
- Public view at `/chatbot/shared/{token}/` renders the session in read-only mode
- `viewed` flag tracks whether the recipient has opened the shared session

### 3.7.4 Persistent User Memory

`UserMemory` model (one record per user/well_code/topic combination) persists the
last 200 characters of the AI's answer for up to 10 topics per user.

**Topics**: PRODUCTION, BUDGET, WORKOVER, RESERVOIR, GENERAL

**Lifecycle** (`apps/chatbot/memory.py`):
- `get_user_memory(user)` — called before prompt construction; injects a
  `=== MÉMOIRE SESSIONS PRÉCÉDENTES ===` block into the prompt
- `update_user_memory(user, question, answer, well)` — called after each successful response;
  `update_or_create` on the (user, well_code, topic) triple

This gives the AI continuity across sessions without storing full conversation history.

### 3.7.5 Fine-Tuning Dataset and Modelfile

| Artifact | Location | Purpose |
|----------|----------|---------|
| `training_data.jsonl` | `apps/chatbot/training/` | ~8 questions × N wells × 3 languages — ground-truth Q&A pairs |
| `generate_dataset.py` | `apps/chatbot/training/` | Script to regenerate the dataset from live DWH data |
| `Modelfile` | `apps/chatbot/training/` | Ollama model definition for local fine-tuning on the training set |

The `Modelfile` creates a named Ollama model (`FROM llama3.1:8b`) with the Dr. EZZAOUIA
system prompt and deterministic inference parameters pre-configured.

---

## 3.8 Conclusion

The AI component of the EZZAOUIA platform implements a complete, production-ready RAG system
operating entirely on-premise. It combines live SQL Server production data with semantic
document retrieval, a domain-specific petroleum engineer persona, and a persistent user memory
layer. The system supports trilingual interaction (French, English, Arabic), automatic chart
generation for production trends, and a quality feedback loop through user ratings and team
annotations. The training dataset and Modelfile provide a foundation for future fine-tuning of
the local LLM to further improve domain accuracy.
