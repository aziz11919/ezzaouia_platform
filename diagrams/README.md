# EZZAOUIA Platform — Architecture Diagrams

Three Mermaid.js diagrams documenting the full system architecture for the PFE project.

## Diagrams

| File | Type | Description |
|------|------|-------------|
| `sequence_diagram.md` | Sequence | 4 core system flows: auth, KPI, file import, RAG chatbot |
| `class_diagram.md` | Class | All Django models + DWH snowflake schema |
| `gantt_diagram.md` | Gantt | Full PFE timeline Feb–Jun 2026 |

---

## How to render

### Option 1 — Mermaid Live Editor (recommended, zero install)

1. Open [https://mermaid.live](https://mermaid.live)
2. Paste the content between the triple backticks from any `.md` file
3. Export as PNG or SVG using the toolbar

### Option 2 — VS Code + Mermaid Preview

1. Install extension: **Markdown Preview Mermaid Support** (id: `bierner.markdown-mermaid`)
2. Open any `.md` file in VS Code
3. Press `Ctrl+Shift+V` to open Markdown Preview
4. Diagrams render inline

### Option 3 — Mermaid CLI (generates PNG/SVG/PDF)

```bash
# Install
npm install -g @mermaid-js/mermaid-cli

# Extract and render (bash helper)
# 1. Copy the mermaid block from any .md into a .mmd file, then:
mmdc -i sequence_diagram.mmd  -o sequence_diagram.png  -t dark -b transparent
mmdc -i class_diagram.mmd     -o class_diagram.png     -t dark -b transparent
mmdc -i gantt_diagram.mmd     -o gantt_diagram.png     -t dark -b transparent
```

### Option 4 — GitHub / GitLab

Push the `.md` files to a GitHub/GitLab repository. Both platforms natively render Mermaid code blocks in Markdown files.

---

## Diagram contents

### Sequence Diagram — 4 flows

```
① Authentication     User → React → POST /accounts/login/ → Django → SQL Server → Session
② KPI Dashboard      React → GET /api/kpis/summary/ → Django calculators → T-SQL → Chart.js
③ File Import        Upload → Django → Celery (async) → parse → SentenceTransformer → ChromaDB
④ Chatbot RAG        Question → Django → get_sql_context() + ChromaDB MMR → Ollama llama3 → Answer
```

### Class Diagram — models

**Application (Django-managed):**
- `User` (extends AbstractUser) — roles: admin / ingenieur / direction
- `ChatSession`, `ChatMessage`, `AnalysisComment`, `SessionShare`, `UserMemory`
- `UploadedFile` — status machine: pending → processing → success/error
- `AuditLog` — immutable action log with JSON details

**Data Warehouse (managed=False — read-only SQL Server):**
- Dimensions: `DimDate`, `DimWell`, `DimWellStatus`, `DimPowerType`, `DimProdMethod`, `DimTypeWell`, `DimTank`
- Facts: `FactProduction` (oil STB/d, gas MSCF, water BWPD), `FactTankLevel` (volume BBLS)
- Snowflake schema: `DimWell → DimPowerType / DimProdMethod / DimTypeWell`

### Gantt — PFE phases

| Phase | Period |
|-------|--------|
| Analysis & Design | Feb 2026 |
| Data Warehouse + ETL Talend | Feb – Mar 2026 |
| Backend Django + DRF + Celery | Mar – Apr 2026 |
| AI & RAG Pipeline (Ollama + ChromaDB) | Apr 2026 |
| Frontend React (Dashboard, Chatbot, Library) | Apr – May 2026 |
| Integration & Testing | May 2026 |
| Documentation & PFE Defense | May – Jun 2026 |

**Defense milestone: 15 June 2026**
