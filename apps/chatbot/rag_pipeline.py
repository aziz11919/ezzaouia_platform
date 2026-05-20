import logging
import re
import hashlib
import datetime
import calendar
from collections import Counter  # FIX: was missing — caused NameError crash in _other_year_dominates
from django.conf import settings
from langchain_ollama import OllamaLLM
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

logger = logging.getLogger('apps')

TODAY = datetime.date.today().strftime('%d/%m/%Y')

# ============================================================================
# TUNING CONSTANTS
# ============================================================================
CHUNK_CONTENT_CHARS = 1800
MAX_DOC_CONTEXT_CHARS_NORMAL = 18000
MAX_DOC_CONTEXT_CHARS_FIELD = 24000
MAX_SQL_CONTEXT_CHARS = 6000
RETRY_DOC_CONTEXT_CHARS = 12000
MAX_DOC_CHUNKS_NORMAL = 18
MAX_DOC_CHUNKS_FIELD = 60
FIELD_WIDE_CHUNKS_PER_WELL = 4
FIELD_WIDE_CHARS_PER_CHUNK = 1200


PROMPT_WELL_ANALYSIS = """You are Dr. EZZAOUIA, Senior Petroleum Engineer at MARETAP S.A.
Your task: Write a complete well analysis combining SQL production data AND document history.

ALWAYS structure your answer EXACTLY like this:

## 🔬 Well {well_code} — Technical Analysis

### Production Performance (from SQL)
| Parameter | Value | Unit | Assessment |
|-----------|------:|------|-----------|
| Avg BOPD | **[value]** | STB/j | ✅/⚠️/🔴 |
| Peak BOPD | **[value]** | STB/j | — |
| Cumulative Oil | **[value]** | STB | — |
| Total Gas | **[value]** | MSCF | — |
| Avg BSW | **[value]** | % | ✅/⚠️/🔴 |
| Avg GOR | **[value]** | SCF/STB | ✅/DATA UNAVAILABLE |
| Avg Prod Hours | **[value]** | h/j | — |

### Operational History (from Documents)
| Date | Event | Source |
|------|-------|--------|
| [date] | [event description] | [filename] |

### Assessment
2-3 sentences summarizing well health based on the data above.

RULES:
- ALWAYS use markdown tables — NEVER plain text paragraphs for data
- Use ONLY numbers from SQL DATABASE section
- Use ONLY events from DOCUMENT CONTEXT section
- BOLD all numeric values: **181.3 STB/j**
- Flag BSW > 80% as 🔴 CRITICAL
- Flag BSW 50-80% as ⚠️ Elevated
- Flag BSW < 50% as ✅ Normal
- If SQL is empty say "No production data available"
- If documents are empty say "No document history available"
- NEVER invent data
"""

PROMPT_PRODUCTION_KPIS = """You are Dr. EZZAOUIA, Senior Petroleum Engineer at MARETAP S.A.
Your task: Answer production KPI questions using ONLY the SQL data provided.

ALWAYS structure your answer with markdown tables:

## 📊 [Descriptive Title]

| # | Well | Avg BOPD | Cumulative (STB) | BSW% | Status |
|:-:|------|----------:|-----------------:|-----:|--------|
| 1 | EZZ11 | **463.3** | 3,814,559 | 1.6% | ✅ Excellent |

OR for field KPIs:

| Indicator | Value | Unit | Status |
|-----------|------:|------|--------|
| Avg BOPD | **[value]** | STB/j | ✅/⚠️/🔴 |

**Critical Alerts:** [BSW > 80% wells flagged here]

*Source: EZZAOUIA DWH — [date]*

RULES:
- ⚠️ CRITICAL: Copy the ranking EXACTLY as numbered in SQL DATABASE section — number 1 is first, number 2 is second, etc. NEVER reorder.
- The ranking is already correct in the SQL section — do NOT sort by any other column
- If SQL shows EZZ4 at position 2, EZZ4 MUST be row 2 in your table
- ALWAYS use markdown tables — NEVER plain text only
- BOLD all numeric values: **99,126 STB**
- Use ONLY numbers from SQL DATABASE section — copy them exactly
- Present rankings in EXACT order as they appear in SQL section
- Flag BSW > 80% as 🔴 CRITICAL
- Flag GOR = 0 as DATA UNAVAILABLE
- NEVER invent well names or production figures
- Respond in same language as the question
"""

PROMPT_DOCUMENT_QA = """You are Dr. EZZAOUIA, Senior Petroleum Engineer at MARETAP S.A.
Your task: Answer questions by extracting information from the provided documents.

Structure your answer clearly:

## 📋 [Topic Title]

For factual questions: use a short summary paragraph + table if multiple items.
For event/history questions: use a chronological list or table with dates.

| Date | Event | Details |
|------|-------|---------|
| [date] | [event] | [details] |

OR for single-fact answers: 2-4 clear sentences with **bold key facts**.

*Source: [document name]*

RULES:
{well_confusion_rule}
- Answer ONLY from DOCUMENT CONTEXT section
- For tubing integrity or workover history on a SINGLE well:
  * Read the ENTIRE context from start to finish before writing
  * Create ONE row per workover event found in context
  * Order rows chronologically — oldest first
  * Add a final row for current production status if mentioned in context
  * Use this generic table structure:
    | Year | Period | Tubing Event | Result |
    |------|--------|-------------|--------|
    | [year] | [dates] | [event description from context] | [outcome from context] |
    | Current | [date] | [current condition from context] | [status] |
  * NEVER stop after finding 1 event — scan ALL context for ALL years
  * NEVER invent rows not present in context
  * NEVER skip rows that exist in context
  * If context has 3 workovers → generate 3 rows + Current
  * BOLD critical findings: **rejected joints**, **tubing leak**, **integrity failure**
- For workover history: create ONE row per workover year, summarizing the purpose
- NEVER list individual drilling steps — only summarize the campaign objective and result
- The DOCUMENT CONTEXT may contain SEVERAL workovers from different
  years (e.g. 2010, 2013, 2015, 2017) using identical technical
  vocabulary. Before answering, identify every year present and use
  ONLY the passages whose year matches the question. Ignore workovers
  from other years even if they look relevant.
- For a workover OBJECTIVE or PURPOSE question:
  * The objective is stated at the START of the workover description
    (e.g. "Pull existing completion", "due to confirmed hole in tubing").
  * The packer setting depth, rig release date, and final completion
    depths are the RESULT, NOT the objective. NEVER report a final
    packer depth or a rig release date as the goal of the workover.
  * Read the workover block from its first line — the reason for the
    intervention always precedes the execution steps and the result.
- Extract facts directly: dates, causes, actions, results
- BOLD key facts: **58 tubing joints rejected**, **April 24th, 2015**
- Always cite which document the answer comes from
- If you find ANY relevant information, USE IT
- Only say "The indexed documents do not contain specific information about this query." if context has ZERO relevant content
- When a chunk starts with "EZZ#9:", extract it directly for EZZ9 questions
- NEVER add information not present in the documents
- For narrative answers, write a complete and thorough explanation of up to 12 sentences (NOT for tables — tables have no sentence limit). Do not artificially shorten the answer if the context contains more relevant facts.

- For field-wide questions (all wells / tous les puits / every well):
  * CRITICAL: Each chunk is labeled [EZZ-XX DATA] — this label shows
    which well the information belongs to. NEVER use [EZZ-01 DATA]
    chunks to describe EZZ-05, EZZ-07, EZZ-15, or any other well.
  * If a well's labeled chunks contain no tubing integrity data,
    write "No data in documents" — do NOT borrow data from another well.
  * Create EXACTLY ONE row per well in the summary table
  * Include ALL wells from EZZ-01 to EZZ-18 (EZZ-13 does not exist — skip it)
  * NEVER stop the table at EZZ-10 — always continue until EZZ-18
  * Extract ALL information EXCLUSIVELY from the DOCUMENT CONTEXT section
  * NEVER copy from memory or invent data — use ONLY what is in the context
  * If a well has NO information in the context: write "No data in documents"
  * For tubing integrity questions use this table structure:
    | Well | Well Status | Key Tubing Events | Current Condition |
    |------|-------------|-------------------|-------------------|
    | [well_code] | [ACTIVE/CLOSED/SHUT-IN/DISPOSAL/P&A from context] | [events extracted from context only] | [condition from context only] |
  * For workover history questions use this table structure:
    | Well | Last WO Year | WO Purpose | Result |
    |------|-------------|------------|--------|
    | [well_code] | [year from context] | [purpose from context] | [result from context] |
  * For production questions use this table structure:
    | Well | Status | Key Production Events | Current Status |
    |------|--------|-----------------------|----------------|
    | [well_code] | [status from context] | [events from context] | [status from context] |
"""

PROMPT_OPERATIONAL_HISTORY = """You are Dr. EZZAOUIA, Senior Petroleum Engineer at MARETAP S.A.
Your task: Answer questions about field operations using operator logs from DimDate.

ALWAYS structure your answer like this:

## 📋 Field Notes — [Well/Topic]

**[N] records found — [N] distinct period(s) identified**

### Periods Identified
| # | Start | End | Duration |
|:-:|-------|-----|----------|
| 1 | DD/MM/YYYY | DD/MM/YYYY | X days |

### Key Excerpts
| Date | Activity |
|------|---------|
| DD/MM/YYYY | [description of activity] |

*Source: EZZAOUIA DWH — DimDate.comments*

RULES:
- Use ONLY data from OPERATOR COMMENTS section
- Present events chronologically with dates
- BOLD key technical terms: **workover**, **SRP intervention**, **shut-in**
- If no comments found say: "No operator log entries found for this activity in the database."
- NEVER invent dates or events
"""

PROMPT_FIELD_SUMMARY = """You are Dr. EZZAOUIA, Senior Petroleum Engineer at MARETAP S.A.
Your task: Provide a field-level summary using SQL KPI data.

ALWAYS structure your answer EXACTLY like this:

## 📊 EZZAOUIA Field — Summary

> **Executive Summary:** [2-3 sentences with most critical numbers]

### Key Performance Indicators
| Indicator | Value | Unit | Benchmark | Status |
|-----------|------:|------|-----------|--------|
| Avg BOPD | **[value]** | STB/j | >200 target | ✅/⚠️/🔴 |
| Total Cumulative Oil | **[value]** | STB | — | — |
| Field BSW | **[value]** | % | <50% OK | ✅/⚠️/🔴 |
| Field GOR | **[value]** | SCF/STB | >500 alert | ✅/DATA UNAVAILABLE |
| Avg Prod Hours | **[value]** | h/j | >20 optimal | ✅/⚠️/🔴 |

### Critical Alerts
| Well | BSW% | BOPD | Risk |
|------|-----:|-----:|------|
| [well] | **[bsw]%** | [bopd] | 🔴 CRITICAL |

### Monthly Breakdown (if available)
| Month | Oil (STB) | BSW% |
|-------|----------:|-----:|

*Source: EZZAOUIA DWH — [date]*

RULES:
- ALWAYS use markdown tables — NEVER plain text paragraphs for data
- BOLD all numeric values
- Use ONLY numbers from SQL DATABASE section
- NEVER invent field statistics
- Replace [date] with the DATE value from the context header
- GOR > 0 means data IS available — only flag as DATA UNAVAILABLE if GOR = 0
"""

KEYWORDS = [
    'maretap', 'ezzaouia', 'zarzis', 'tunisia', 'tunisie',
    'bopd', 'bwpd', 'mscf', 'stb', 'barrel', 'baril',
    'well', 'puits', 'production', 'reservoir', 'petroleum',
    'petrole', 'oil', 'gas', 'gaz', 'bsw', 'gor', 'wct',
    'offshore', 'onshore', 'perforation', 'workover',
    'completion', 'tubing', 'casing', 'choke', 'separator',
    'cpf', 'field', 'champ', 'formation', 'layer', 'couche',
    'injection', 'pressure', 'pression', 'productivity',
]


def is_petroleum_document(text):
    text_lower = text.lower()
    count = sum(1 for kw in KEYWORDS if kw in text_lower)
    return count >= 3


_llm = None
_embeddings = None
_vectorstores = {}
_global_vectorstore = None


def get_llm():
    global _llm
    if _llm is None:
        _llm = OllamaLLM(
            model=settings.OLLAMA_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=0.05,
            num_ctx=16384,
            num_predict=4096,
            top_p=0.85,
            repeat_penalty=1.08,
            timeout=300,
        )
    return _llm


def get_embeddings():
    global _embeddings
    if _embeddings is None:
        _embeddings = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
    return _embeddings


def _get_doc_collection_name(doc_id):
    safe = hashlib.md5(str(doc_id).encode()).hexdigest()[:12]
    return f"doc_{safe}"


def get_vectorstore_for_doc(doc_id):
    global _vectorstores
    if doc_id not in _vectorstores:
        import os
        persist_dir = os.path.join(settings.CHROMA_PERSIST_DIR, f"doc_{doc_id}")
        _vectorstores[doc_id] = Chroma(
            persist_directory=persist_dir,
            embedding_function=get_embeddings(),
            collection_name=_get_doc_collection_name(doc_id),
        )
    return _vectorstores[doc_id]


def get_global_vectorstore():
    global _global_vectorstore
    if _global_vectorstore is None:
        _global_vectorstore = Chroma(
            persist_directory=settings.CHROMA_PERSIST_DIR,
            embedding_function=get_embeddings(),
            collection_name="ezzaouia_global",
        )
    return _global_vectorstore


def _chunk_key(chunk_text):
    return hashlib.md5((chunk_text or "").encode('utf-8')).hexdigest()


def _extract_well_num_from_chunk(chunk):
    import re as _re
    matches = list(_re.finditer(
        r'(?:EZZ|EZZAOUIA)\s*#?\s*0*(\d{1,2})(?!\d)',
        chunk, _re.IGNORECASE
    ))
    if not matches:
        return None
    nums = [m.group(1).lstrip('0') or '0' for m in matches]
    most_common = Counter(nums).most_common(1)[0][0]
    return most_common


def index_document(text, metadata=None, doc_id=None):
    if not text or not text.strip():
        return 0
    metadata = metadata or {}
    if doc_id:
        metadata['doc_id'] = str(doc_id)

    try:
        estimated_pages = max(1, len(text) // 2000)
        if estimated_pages <= 3:
            chunk_size = 2000
            chunk_overlap = 200
        elif estimated_pages <= 10:
            chunk_size = 1200
            chunk_overlap = 300
        else:
            chunk_size = 800
            chunk_overlap = 200

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=[
                "\nWORKOVER",
                "\n2.",
                "\n\n\n",
                "\n\n",
                "\n",
                ".",
                " ",
            ],
        )
        chunks = splitter.split_text(text)
        docs = []
        for i, chunk in enumerate(chunks):
            chunk_meta = {
                **metadata,
                'chunk_index': i,
                'chunk_total': len(chunks)
            }
            import re as _re
            _filename = metadata.get('filename', '')
            filename_well = _re.search(
                r'DGH_EZZ(\d{1,2})\.pdf', _filename, _re.IGNORECASE)

            if filename_well:
                chunk_meta['well_num'] = filename_well.group(1).lstrip('0') or '0'
            else:
                well_num = _extract_well_num_from_chunk(chunk)
                if well_num:
                    chunk_meta['well_num'] = well_num
            docs.append(Document(
                page_content=chunk,
                metadata=chunk_meta
            ))
        if doc_id:
            get_vectorstore_for_doc(doc_id).add_documents(docs)
        get_global_vectorstore().add_documents(docs)
        logger.info(f"Indexed {len(docs)} chunks")
        return len(docs)
    except Exception as e:
        logger.error(f"Indexing error: {e}")
        return 0


def _well_num_matches(chunk_well, target_well):
    if not chunk_well or not target_well:
        return False
    return chunk_well.lstrip('0') == target_well.lstrip('0')


def _rank_attached_file_chunks(query, all_docs, k):
    if len(all_docs) <= k:
        return all_docs

    try:
        embeddings = get_embeddings()
        q_vec = embeddings.embed_query(query)
        import numpy as np

        def cosine(a, b):
            a = np.array(a, dtype=float)
            b = np.array(b, dtype=float)
            denom = (np.linalg.norm(a) * np.linalg.norm(b)) or 1.0
            return float(np.dot(a, b) / denom)

        scored = []
        for d in all_docs:
            try:
                d_vec = embeddings.embed_query(d.page_content[:512])
                scored.append((cosine(q_vec, d_vec), d))
            except Exception:
                scored.append((0.0, d))
        scored.sort(key=lambda x: x[0], reverse=True)
        top = [d for _, d in scored[:k]]
    except Exception as e:
        logger.warning(f"Attached-file ranking failed, falling back: {e}")
        top = all_docs[:k]

    tail = sorted(all_docs, key=lambda d: int(d.metadata.get('chunk_index', 0)))[-2:]
    seen = {_chunk_key(d.page_content) for d in top}
    for t in tail:
        if _chunk_key(t.page_content) not in seen:
            top.append(t)
            seen.add(_chunk_key(t.page_content))
    return top


def retrieve_smart(query, doc_id=None, filename=None, k=6, well_num=None):
    try:
        results = []

        if doc_id:
            vs = get_vectorstore_for_doc(doc_id)
            try:
                col = vs._collection
                all_chunks = col.get(include=['documents', 'metadatas'])
                if all_chunks and all_chunks.get('documents'):
                    from langchain.schema import Document as LCDoc
                    all_docs = [
                        LCDoc(page_content=doc, metadata=meta)
                        for doc, meta in zip(all_chunks['documents'], all_chunks['metadatas'])
                    ]
                    ranked = _rank_attached_file_chunks(query, all_docs, max(k, MAX_DOC_CHUNKS_NORMAL))
                    logger.info(
                        f"File attached — {len(all_docs)} total chunks, "
                        f"returning {len(ranked)} ranked chunks"
                    )
                    return ranked
            except Exception as e:
                logger.warning(f"Full file retrieval error: {e}")
            results = vs.max_marginal_relevance_search(
                query, k=k, fetch_k=k*3, lambda_mult=0.6)
            if results:
                return results

        vs = get_global_vectorstore()

        if filename:
            results = vs.similarity_search(
                query, k=k, filter={"filename": {"$eq": filename}})
            if results:
                return results

        main_results = vs.max_marginal_relevance_search(
            query, k=k, fetch_k=k*4, lambda_mult=0.5)

        if well_num:
            target_wnum = str(well_num).lstrip('0') or '0'
            well_results = []
            dgh_results = []
            other_results = []
            DGH_FILENAME = f"DGH_EZZ{well_num}.pdf"

            for r in main_results:
                chunk_well = r.metadata.get('well_num', '')
                chunk_file = r.metadata.get('filename', '')
                if _well_num_matches(chunk_well, target_wnum):
                    well_results.append(r)
                elif chunk_file == DGH_FILENAME:
                    dgh_results.append(r)
                else:
                    other_results.append(r)

            try:
                col = vs._collection
                all_dgh = col.get(
                    where={"filename": DGH_FILENAME},
                    include=['documents', 'metadatas']
                )
                existing_keys = {_chunk_key(r.page_content) for r in dgh_results}
                from langchain.schema import Document as LCDoc
                import re as _re
                well_pattern = _re.compile(
                    rf'(?:EZZAOUIA|EZZ)\s*#?\s*0*{re.escape(target_wnum)}\b', _re.IGNORECASE)
                for doc, meta in zip(all_dgh['documents'], all_dgh['metadatas']):
                    if _chunk_key(doc) in existing_keys:
                        continue
                    if well_pattern.search(doc):
                        dgh_results.append(LCDoc(page_content=doc, metadata=meta))
                        existing_keys.add(_chunk_key(doc))
                logger.info(f"DGH keyword fetch: {len(dgh_results)} total DGH chunks")
            except Exception as e:
                logger.warning(f"DGH extra fetch error: {e}")

            if len(dgh_results) < 30:
                try:
                    all_dgh = col.get(
                        where={"filename": DGH_FILENAME},
                        include=['documents', 'metadatas']
                    )
                    existing_keys = {_chunk_key(r.page_content) for r in dgh_results}
                    for doc, meta in zip(all_dgh['documents'], all_dgh['metadatas']):
                        if _chunk_key(doc) not in existing_keys:
                            dgh_results.append(LCDoc(page_content=doc, metadata=meta))
                            existing_keys.add(_chunk_key(doc))
                    logger.info(f"Small file — all {len(dgh_results)} DGH chunks included")
                except Exception as e:
                    logger.warning(f"Small file fetch error: {e}")

            TECHNICAL_KEYWORDS = [
                'rejected', 'lost thickness', 'sucker rod', 'wash out',
                'tubing failure', 'wall thickness', 'integrity failure',
                'circulation loss', 'fractured', 'hydrocarbons',
                'packer', 'completion', 'workover sequence'
            ]
            q_lower = query.lower()
            matched_keywords = [kw for kw in TECHNICAL_KEYWORDS if kw in q_lower]

            if matched_keywords:
                try:
                    all_well_chunks = col.get(
                        where={"filename": DGH_FILENAME},
                        include=['documents', 'metadatas']
                    )
                    existing_keys = {_chunk_key(r.page_content) for r in dgh_results}
                    for doc, meta in zip(all_well_chunks['documents'], all_well_chunks['metadatas']):
                        doc_lower = doc.lower()
                        if any(kw in doc_lower for kw in TECHNICAL_KEYWORDS):
                            if _chunk_key(doc) not in existing_keys:
                                dgh_results.append(LCDoc(page_content=doc, metadata=meta))
                                existing_keys.add(_chunk_key(doc))
                    logger.info(f"Keyword fallback added chunks, total DGH: {len(dgh_results)}")
                except Exception as e:
                    logger.warning(f"Keyword fallback error: {e}")

            main_results = well_results + dgh_results + other_results

            if well_num:
                import re as _re
                year_in_query = _re.search(r'\b(20\d{2}|19\d{2})\b', query)
                target_year = year_in_query.group(1) if year_in_query else None

                PRIORITY_KEYWORDS = [
                    'rejected', 'lost thickness', 'sucker rod', 'wash out',
                    'failure', 'integrity', 'workover', 'abandoned', 'plug',
                    'hydrocarbons', 'circulation loss'
                ]

                def chunk_score(r):
                    score = 0
                    content = r.page_content
                    content_lower = content.lower()

                    if target_year and target_year in content:
                        score += 50

                    # FIX: penalise chunks where wrong year is majority
                    if target_year:
                        all_years = re.findall(r'\b((?:19|20)\d{2})\b', content)
                        other_years = [y for y in all_years if y != str(target_year)]
                        if all_years and len(other_years) > len(all_years) // 2:
                            score -= 20

                    if any(kw in content_lower for kw in PRIORITY_KEYWORDS):
                        score += 5
                    return score

                main_results = sorted(main_results, key=chunk_score, reverse=True)
                logger.info(f"Chunks re-sorted by year={target_year} and keywords")

            logger.info(
                f"Well {well_num} filtering: {len(well_results)} tagged, "
                f"{len(dgh_results)} DGH, {len(other_results)} others"
            )

        if well_num:
            DGH_FILENAME = f"DGH_EZZ{well_num}.pdf"
        else:
            DGH_FILENAME = "DGH_INTRO.pdf"
        dgh_present = any(
            r.metadata.get('filename') == DGH_FILENAME
            for r in main_results
        )

        if not dgh_present:
            try:
                embeddings = get_embeddings()
                query_embedding = embeddings.embed_query(query)
                col = vs._collection
                dgh_raw = col.query(
                    query_embeddings=[query_embedding],
                    n_results=4,
                    where={"filename": DGH_FILENAME}
                )
                dgh_docs = []
                if dgh_raw and dgh_raw.get('documents'):
                    for doc, meta in zip(
                        dgh_raw['documents'][0],
                        dgh_raw['metadatas'][0]
                    ):
                        from langchain.schema import Document as LCDoc
                        dgh_docs.append(LCDoc(
                            page_content=doc,
                            metadata=meta
                        ))

                if dgh_docs:
                    combined = main_results + dgh_docs
                    seen = set()
                    deduped = []
                    for r in combined:
                        key = _chunk_key(r.page_content)
                        if key not in seen:
                            seen.add(key)
                            deduped.append(r)
                    logger.info(f"DGH report forced: {len(dgh_docs)} chunks added")
                    return deduped[:k + 4]
            except Exception as e:
                logger.warning(f"DGH forced retrieval error: {e}")

        return main_results

    except Exception as e:
        logger.error(f"Retrieval error: {e}")
        return []


def get_available_documents():
    try:
        collection = get_global_vectorstore()._collection
        results = collection.get(include=['metadatas'])
        filenames = set()
        for meta in results.get('metadatas', []):
            if meta and meta.get('filename'):
                filenames.add(meta['filename'])
        return list(filenames)
    except Exception as e:
        logger.error(f"Docs list error: {e}")
        return []


def normalize_well_code(text):
    from apps.warehouse.models import DimWell
    for pattern in [r'\b(ezz\s*[-#]?\s*\d+)\b', r'\b(ez\s*[-#]?\s*\d+)\b']:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            raw = match.group(1).upper().replace(' ', '').replace('#', '')
            well = DimWell.objects.filter(well_code__icontains=raw.replace('-', '')).first()
            if not well:
                well = DimWell.objects.filter(well_code__icontains=raw).first()
            if well:
                return well
    return None


def _get_date_comments(date_value):
    if not date_value or date_value == 'N/A':
        return None
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT comments FROM dbo.DimDate WHERE FullDate = %s",
                [date_value]
            )
            row = cursor.fetchone()
            if row and row[0] and str(row[0]).strip():
                return str(row[0]).strip()
    except Exception as e:
        logger.warning(f"DimDate comments fetch error: {e}")
    return None


def search_date_comments(keyword: str = None, well_code: str = None,
                         limit: int = 200) -> list:
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            conditions = ["comments IS NOT NULL", "LTRIM(RTRIM(comments)) != ''"]
            params = []
            if keyword:
                conditions.append("comments LIKE %s")
                params.append(f"%{keyword}%")
            if well_code:
                num = re.search(r'\d+', well_code)
                if num:
                    n = num.group()
                    conditions.append(
                        "(comments LIKE %s OR comments LIKE %s OR comments LIKE %s)"
                    )
                    params.append(f"%EZZ#{n}[^0-9]%")
                    params.append(f"%EZZ# {n}[^0-9]%")
                    # FIX: added trailing % so it matches even when well code
                    # is not at the very end of the comments string
                    params.append(f"%EZZ#{n}%")
                else:
                    conditions.append("comments LIKE %s")
                    params.append(f"%{well_code}%")
            where = " AND ".join(conditions)
            cursor.execute(
                f"SELECT TOP {limit} FullDate, comments "
                f"FROM dbo.DimDate "
                f"WHERE {where} "
                f"ORDER BY FullDate ASC",
                params
            )
            rows = cursor.fetchall()
            return [{"date": str(row[0]), "comments": str(row[1]).strip()}
                    for row in rows]
    except Exception as e:
        logger.warning(f"DimDate search error: {e}")
        return []


def search_date_comments_multi(keywords: list, well_code: str = None,
                                limit: int = 50) -> list:
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            conditions = ["comments IS NOT NULL", "LTRIM(RTRIM(comments)) != ''"]
            params = []
            for kw in keywords:
                conditions.append("comments LIKE %s")
                params.append(f"%{kw}%")
            if well_code:
                num = re.search(r'\d+', well_code)
                if num:
                    n = num.group()
                    conditions.append(
                        "(comments LIKE %s OR comments LIKE %s OR comments LIKE %s)"
                    )
                    params.append(f"%EZZ#{n}[^0-9]%")
                    params.append(f"%EZZ# {n}[^0-9]%")
                    # FIX: added trailing % (same fix as search_date_comments)
                    params.append(f"%EZZ#{n}%")
                else:
                    conditions.append("comments LIKE %s")
                    params.append(f"%{well_code}%")
            where = " AND ".join(conditions)
            cursor.execute(
                f"SELECT TOP {limit} FullDate, comments "
                f"FROM dbo.DimDate "
                f"WHERE {where} "
                f"ORDER BY FullDate ASC",
                params
            )
            rows = cursor.fetchall()
            return [{"date": str(row[0]), "comments": str(row[1]).strip()}
                    for row in rows]
    except Exception as e:
        logger.warning(f"DimDate multi search error: {e}")
        return []


def get_sql_context(question):
    from apps.kpis.calculators import (
        get_field_production_summary, get_top_producers,
        get_well_kpis, get_monthly_trend,
    )
    from apps.warehouse.models import DimWell

    context = ""
    q = question.lower()
    lang = detect_language(question)

    years_found_early = re.findall(r'\b(20\d{2})\b', q)
    if any(w in q for w in ['production', 'total', 'champ', 'bopd', 'huile',
                             'résumé', 'resume', 'situation', 'global',
                             'bilan', 'analyse', 'performance', 'kpi',
                             'field', 'summary', 'overview']) and not years_found_early:
        s = get_field_production_summary()
        avg_bopd = s.get('avg_bopd', 0) or 0
        avg_bsw = s.get('avg_bsw', 0) or 0
        avg_gor = s.get('avg_gor', 0) or 0
        total_oil = s.get('total_oil_stbd', 0) or 0
        total_water = s.get('total_water_bwpd', 0) or 0
        total_gas = s.get('total_gas_mscf', 0) or 0
        avg_prodhours = s.get('avg_prodhours', 0) or 0
        last_date = s.get('last_date', 'N/A')

        context += f"""
=== EZZAOUIA FIELD — GLOBAL PRODUCTION KPIs ===
Last reporting date  : {last_date}
Average BOPD         : {avg_bopd:,.1f} STB/j
Total cumulative oil : {total_oil:,.0f} STB
Total water (BWPD)   : {total_water:,.0f} BWPD
Total gas            : {total_gas:,.0f} MSCF
Field average BSW    : {avg_bsw:.2f}%
Field average GOR    : {avg_gor:,.0f} SCF/STB  {'[DATA UNAVAILABLE — measurement required]' if avg_gor == 0 else ''}
Avg production hours : {avg_prodhours:.1f} h/j  {'[CRITICAL — wells not at full capacity]' if avg_prodhours < 20 else ''}
"""
        comments = _get_date_comments(last_date)
        if comments:
            context += f"\nRemarques du terrain ({last_date}): {comments}\n"

    if any(w in q for w in ['meilleur', 'top', 'performer', 'classement',
                             'faible', 'low', 'analyse', 'performance',
                             'best', 'worst', 'ranking', 'producers']):
        top = get_top_producers(limit=20)
        context += f"\n=== WELL RANKING — ALL {len(top)} ACTIVE WELLS ===\n"
        for i, w in enumerate(top, 1):
            bsw_flag = " 🔴 CRITICAL" if float(w.get('avg_bsw', 0) or 0) > 80 else ""
            context += (
                f"{i:2}. {w['well_code']:8} | "
                f"BOPD: {float(w.get('avg_bopd', 0) or 0):>8,.1f} STB/j | "
                f"Total: {float(w.get('total_oil', 0) or 0):>12,.0f} STB | "
                f"BSW: {float(w.get('avg_bsw', 0) or 0):>5.1f}%{bsw_flag}\n"
            )

    years_found = re.findall(r'\b(20\d{2})\b', q)
    if years_found:
        if len(years_found) >= 2:
            y_start, y_end = int(min(years_found)), int(max(years_found))
            trend = get_monthly_trend(year_start=y_start, year_end=y_end, lang=lang)
            context += f"\n=== PRODUCTION {y_start}–{y_end} (MONTHLY) ===\n"
            if trend:
                for t in trend:
                    context += (
                        f"  {str(t['month_name']):12} {t['year']} : "
                        f"{float(t.get('total_oil', 0) or 0):>10,.0f} STB | "
                        f"BSW {float(t.get('avg_bsw', 0) or 0):.1f}%\n"
                    )
            else:
                context += f"  No data available for {y_start}–{y_end}.\n"
        else:
            year = int(years_found[0])
            summary = get_field_production_summary(year=year)
            trend = get_monthly_trend(year=year, lang=lang)
            if summary and summary.get('total_oil_stbd', 0) > 0:
                context += f"\n=== PRODUCTION YEAR {year} ===\n"
                context += f"  Average BOPD : {summary.get('avg_bopd', 0):,.1f} STB/j\n"
                context += f"  Total oil    : {summary.get('total_oil_stbd', 0):,.0f} STB\n"
                context += f"  Field BSW    : {summary.get('avg_bsw', 0):.2f}%\n"
                context += f"  Field GOR    : {summary.get('avg_gor', 0):,.0f} SCF/STB\n"
                if trend:
                    context += f"\n  Monthly breakdown {year}:\n"
                    for t in trend:
                        context += (
                            f"    {str(t['month_name']):12} : "
                            f"{float(t.get('total_oil', 0) or 0):>10,.0f} STB | "
                            f"BSW {float(t.get('avg_bsw', 0) or 0):.1f}%\n"
                        )
            else:
                context += f"\n  No production data found for year {year}.\n"

    well = normalize_well_code(question)
    if well:
        year = int(years_found[0]) if years_found and len(years_found) == 1 else None
        kpis = get_well_kpis(well_key=well.well_key, year=year)
        trend = get_monthly_trend(well_key=well.well_key, year=year, lang=lang)

        context += f"\n=== WELL {well.well_code} — {well.libelle} ===\n"
        context += f"  Status       : {'SHUT-IN' if well.closed == 'Y' else 'ACTIVE'}\n"
        context += f"  Formation    : {well.layer}\n"

        if kpis:
            k = kpis[0]
            avg_bopd_w = float(k.get('avg_bopd', 0) or 0)
            max_bopd_w = float(k.get('max_bopd', 0) or 0)
            total_oil_w = float(k.get('total_oil', 0) or 0)
            avg_bsw_w = float(k.get('avg_bsw', 0) or 0)
            avg_gor_w = float(k.get('avg_gor', 0) or 0)
            total_gas_w = float(k.get('total_gas', 0) or 0)
            total_water_w = float(k.get('total_water', 0) or 0)
            avg_prodhours_w = float(k.get('avg_prodhours', 0) or 0)

            bsw_flag = " ⚠️ CRITICAL — Advanced reservoir flooding" if avg_bsw_w > 80 else (
                " ⚠️ Elevated" if avg_bsw_w > 50 else " ✅ Normal")
            gor_note = " [DATA UNAVAILABLE]" if avg_gor_w == 0 else ""

            context += f"  Avg BOPD     : {avg_bopd_w:,.1f} STB/j\n"
            context += f"  Peak BOPD    : {max_bopd_w:,.0f} STB/j\n"
            context += f"  Cum. oil     : {total_oil_w:,.0f} STB\n"
            context += f"  Total gas    : {total_gas_w:,.0f} MSCF\n"
            context += f"  Total water  : {total_water_w:,.0f} BWPD\n"
            context += f"  Avg BSW      : {avg_bsw_w:.2f}%{bsw_flag}\n"
            context += f"  Avg GOR      : {avg_gor_w:,.0f} SCF/STB{gor_note}\n"
            context += f"  Prod hours   : {avg_prodhours_w:.1f} h/j\n"

        if trend:
            context += "\n  Monthly production history (last 12 months):\n"
            for t in trend[-12:]:
                context += (
                    f"    {str(t['month_name']):12} {t['year']} : "
                    f"{float(t.get('total_oil', 0) or 0):>10,.0f} STB | "
                    f"BSW {float(t.get('avg_bsw', 0) or 0):.1f}%\n"
                )

    if any(w in q for w in ['wct', 'water cut', 'bsw', 'gor', 'réservoir',
                             'reservoir', 'forecast', 'pression', 'pressure']):
        s = get_field_production_summary()
        top = get_top_producers(limit=20)
        avg_bsw_f = float(s.get('avg_bsw', 0) or 0)
        avg_gor_f = float(s.get('avg_gor', 0) or 0)

        context += f"\n=== RESERVOIR ANALYSIS ===\n"
        context += f"  Field WCT/BSW : {avg_bsw_f:.2f}%  {'[CRITICAL > 80%]' if avg_bsw_f > 80 else '[NORMAL < 15%]' if avg_bsw_f < 15 else '[ELEVATED]'}\n"
        context += f"  Field GOR     : {avg_gor_f:,.0f} SCF/STB  {'[DATA UNAVAILABLE]' if avg_gor_f == 0 else ''}\n"
        context += "\n  BSW by well (sorted highest to lowest):\n"
        sorted_wells = sorted(top, key=lambda x: float(x.get('avg_bsw', 0) or 0), reverse=True)
        for w in sorted_wells:
            bsw_w = float(w.get('avg_bsw', 0) or 0)
            flag = " 🔴 CRITICAL" if bsw_w > 80 else " ⚠️ HIGH" if bsw_w > 50 else ""
            context += f"    {w['well_code']:8} | BSW: {bsw_w:>5.1f}% | BOPD: {float(w.get('avg_bopd', 0) or 0):>8,.1f}{flag}\n"

    if any(w in q for w in ['tank', 'bac', 'stockage', 'volumebbls', 'niveau', 'bbls']):
        from apps.kpis.calculators import get_tank_levels
        tanks = get_tank_levels()
        if tanks:
            context += f"\n=== TANK LEVELS (latest data) ===\n"
            seen = {}
            for t in tanks:
                code = t.get('tank_code', '-')
                seen[code] = t
            for code, t in seen.items():
                context += (
                    f"  {code:10} ({t.get('tank_name', ''):20}) "
                    f"| {t.get('date', '')} : {t.get('volume') or 0:,} BBL\n"
                )

    if any(w in q for w in ['statut', 'status', 'heures', 'prodhours',
                             'pression', 'choke', 'tubing', 'casing', 'pressure']):
        from apps.kpis.calculators import get_well_status_kpis
        well_ref = normalize_well_code(question)
        if well_ref:
            status_data = get_well_status_kpis(well_key=well_ref.well_key)
            if status_data:
                latest = status_data[0]
                context += f"\n=== OPERATIONAL STATUS — {well_ref.well_code} (latest entry) ===\n"
                context += f"  Prod hours : {latest.get('prodhours_val') or 'N/A'} h\n"
                context += f"  BSW        : {latest.get('bsw_val') or 'N/A'} %\n"
                context += f"  GOR        : {latest.get('gor_val') or 'N/A'} SCF/STB\n"
                context += f"  Flow temp  : {latest.get('flowtemp_val') or 'N/A'} °F\n"
                context += f"  Choke 16\"  : {latest.get('choke_val') or 'N/A'}\n"
                context += f"  Tubing     : {latest.get('tubing_val') or 'N/A'} psig\n"
                context += f"  Casing     : {latest.get('casing_val') or 'N/A'} psig\n"

    if any(w in q for w in ['liste', 'tous les puits', 'combien', 'inventaire', 'list all', 'all wells']):
        from apps.warehouse.models import DimWell
        wells = DimWell.objects.all().order_by('well_code')
        active = wells.filter(closed='N').count()
        shut = wells.filter(closed='Y').count()
        context += f"\n=== WELL INVENTORY — {wells.count()} TOTAL ({active} active, {shut} shut-in) ===\n"
        for w in wells:
            context += (
                f"  {w.well_code:8} ({w.libelle[:25]:25}) "
                f"| {'SHUT-IN' if w.closed == 'Y' else 'ACTIVE ':7} "
                f"| Layer: {w.layer}\n"
            )

    # FIX: guard against SQL context overflow
    if len(context) > MAX_SQL_CONTEXT_CHARS:
        logger.warning(f"SQL context pre-truncated: {len(context)} -> {MAX_SQL_CONTEXT_CHARS}")
        context = context[:MAX_SQL_CONTEXT_CHARS] + "\n[... truncated ...]"

    return context


_MONTHS_FR = {
    'janvier': 1, 'février': 2, 'fevrier': 2, 'mars': 3, 'avril': 4,
    'mai': 5, 'juin': 6, 'juillet': 7, 'août': 8, 'aout': 8,
    'septembre': 9, 'octobre': 10, 'novembre': 11, 'décembre': 12, 'decembre': 12,
}


def parse_date_range(question):
    from datetime import date
    from dateutil.relativedelta import relativedelta
    import calendar as _cal
    q = question.lower()

    relative_pat = re.search(
        r'les\s+(\d+)\s+derniers?\s+mois'
        r'|(?:last|derniers?)\s+(\d+)\s+mois'
        r'|last\s+(\d+)\s+months?',
        q
    )
    if relative_pat:
        n = int(next(g for g in relative_pat.groups() if g is not None))
        today = date.today()
        return today - relativedelta(months=n), today

    month_pat = '|'.join(_MONTHS_FR.keys())
    my_matches = re.findall(rf'({month_pat})\s+(20\d{{2}})', q)
    year_matches = re.findall(r'\b(20\d{2})\b', q)

    if len(my_matches) >= 2:
        m1, y1 = my_matches[0]
        m2, y2 = my_matches[-1]
        d_start = date(int(y1), _MONTHS_FR[m1], 1)
        ey, em = int(y2), _MONTHS_FR[m2]
        d_end = date(ey, em, _cal.monthrange(ey, em)[1])
        return d_start, d_end
    if len(my_matches) == 1:
        m1, y1 = my_matches[0]
        start_m, start_y = _MONTHS_FR[m1], int(y1)
        years = [int(y) for y in year_matches]
        other = [y for y in years if y != start_y]
        if other:
            end_y = max(other)
            return date(start_y, start_m, 1), date(end_y, 12, 31)
        return (date(start_y, start_m, 1),
                date(start_y, start_m, _cal.monthrange(start_y, start_m)[1]))
    if len(year_matches) >= 2:
        years = sorted(int(y) for y in year_matches)
        return date(years[0], 1, 1), date(years[-1], 12, 31)
    if len(year_matches) == 1:
        y = int(year_matches[0])
        return date(y, 1, 1), date(y, 12, 31)
    return None, None


def detect_chart_request(question):
    chart_kw = ['évolution', 'evolution', 'historique', 'tendance', 'trend',
                 'graphique', 'chart', 'courbe', 'progression', 'mensuel', 'annuel',
                 'affiche', 'montre', 'visualis', 'show', 'plot']
    q = question.lower()
    return any(kw in q for kw in chart_kw) and normalize_well_code(question) is not None


def build_chart_data(question):
    try:
        from apps.kpis.calculators import get_monthly_trend
        from dateutil.relativedelta import relativedelta
        well = normalize_well_code(question)
        if not well:
            return None
        date_start, date_end = parse_date_range(question)
        if date_start is None or date_end is None:
            date_end = datetime.date.today()
            date_start = date_end - relativedelta(months=12)
        lang = detect_language(question)
        trend = get_monthly_trend(well_key=well.well_key, date_start=date_start, date_end=date_end, lang=lang)
        if not trend:
            return None
        labels = [f"{t['month_name']} {t['year']}" for t in trend]
        oil_data = [round(float(t['total_oil'] or 0), 1) for t in trend]
        bsw_data = [round(float(t['avg_bsw'] or 0), 2) for t in trend]
        return {
            'well_code': well.well_code,
            'well_name': well.libelle or '',
            'labels': labels,
            'datasets': [
                {
                    'label': 'Oil Production (STB)',
                    'data': oil_data,
                    'type': 'bar',
                    'yAxisID': 'y',
                    'backgroundColor': 'rgba(201,168,76,0.55)',
                    'borderColor': '#C9A84C',
                    'borderWidth': 1,
                },
                {
                    'label': 'BSW (%)',
                    'data': bsw_data,
                    'type': 'line',
                    'yAxisID': 'y1',
                    'borderColor': '#E05555',
                    'backgroundColor': 'rgba(224,85,85,0.08)',
                    'borderWidth': 2,
                    'pointRadius': 3,
                    'fill': False,
                },
            ],
        }
    except Exception as e:
        logger.error(f"Chart build error: {e}")
        return None


def detect_language(text):
    if not text:
        return 'fr'
    arabic_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
    if arabic_chars > 2:
        return 'ar'
    lowered = text.lower()
    fr_keywords = [
        'montre', 'montrer', 'affiche', 'afficher', 'donne', 'donner',
        'analyse', 'analyser', 'quelle', 'quel', 'quels', 'quelles',
        'tendance', 'puits', 'champ', 'mois', 'ann\u00E9e',
        'pour', 'avec', 'dans', 'sur', 'les', 'des', 'du', 'la', 'le',
        'janvier', 'f\u00E9vrier', 'mars', 'avril', 'juin',
        'juillet', 'ao\u00FBt', 'septembre', 'octobre', 'novembre', 'd\u00E9cembre',
    ]
    en_keywords = [
        'show', 'display', 'give', 'tell', 'analyze', 'analyse',
        'what', 'which', 'how', 'trend', 'field', 'well', 'month',
        'year', 'for', 'the', 'and', 'with', 'from', 'to', 'me',
        'january', 'february', 'march', 'april', 'june',
        'july', 'august', 'september', 'october', 'november', 'december',
    ]
    fr_score = sum(1 for kw in fr_keywords if kw in lowered)
    en_score = sum(1 for kw in en_keywords if kw in lowered)
    if fr_score > en_score:
        return 'fr'
    elif en_score > fr_score:
        return 'en'
    elif en_score > 0:
        return 'en'
    return 'fr'


MONTH_NAMES = {
    'fr': {
        1: 'Janvier', 2: 'F\u00E9vrier', 3: 'Mars', 4: 'Avril',
        5: 'Mai', 6: 'Juin', 7: 'Juillet', 8: 'Ao\u00FBt',
        9: 'Septembre', 10: 'Octobre', 11: 'Novembre', 12: 'D\u00E9cembre',
    },
    'en': {
        1: 'January', 2: 'February', 3: 'March', 4: 'April',
        5: 'May', 6: 'June', 7: 'July', 8: 'August',
        9: 'September', 10: 'October', 11: 'November', 12: 'December',
    },
    'ar': {
        1: '\u064A\u0646\u0627\u064A\u0631', 2: '\u0641\u0628\u0631\u0627\u064A\u0631',
        3: '\u0645\u0627\u0631\u0633', 4: '\u0623\u0628\u0631\u064A\u0644',
        5: '\u0645\u0627\u064A\u0648', 6: '\u064A\u0648\u0646\u064A\u0648',
        7: '\u064A\u0648\u0644\u064A\u0648', 8: '\u0623\u063A\u0633\u0637\u0633',
        9: '\u0633\u0628\u062A\u0645\u0628\u0631', 10: '\u0623\u0643\u062A\u0648\u0628\u0631',
        11: '\u0646\u0648\u0641\u0645\u0628\u0631', 12: '\u062F\u064A\u0633\u0645\u0628\u0631',
    },
}


def format_month(month_num, year, lang):
    month_str = MONTH_NAMES.get(lang, MONTH_NAMES['fr']).get(month_num, str(month_num))
    return f"{month_str} {year}"


def _force_english_month_names(text):
    if not text:
        return text
    replacements = {
        r'\bjanvier\b': 'January', r'\bfévrier\b': 'February',
        r'\bfevrier\b': 'February', r'\bmars\b': 'March',
        r'\bavril\b': 'April', r'\bmai\b': 'May',
        r'\bjuin\b': 'June', r'\bjuillet\b': 'July',
        r'\baoût\b': 'August', r'\baout\b': 'August',
        r'\bseptembre\b': 'September', r'\boctobre\b': 'October',
        r'\bnovembre\b': 'November', r'\bdécembre\b': 'December',
        r'\bdecembre\b': 'December',
    }
    normalized = text
    for pattern, target in replacements.items():
        normalized = re.sub(pattern, target, normalized, flags=re.IGNORECASE)
    return normalized


def _extract_year(text):
    match = re.search(r'\b(20\d{2})\b', text or "")
    return int(match.group(1)) if match else None


def _is_well_year_trend_request(question):
    if not question:
        return False
    q = question.lower()
    has_well = bool(normalize_well_code(question))
    has_year = bool(_extract_year(question))
    trend_words = [
        'trend', 'monthly', 'history', 'evolution',
        'tendance', 'historique', '\u00e9volution',
        'montrez', 'montrer', 'afficher', 'affiche',
        'mensuel', 'mensuelle', 'courbe', 'graphique',
        '\u0627\u062a\u062c\u0627\u0647', '\u062a\u0637\u0648\u0631', '\u0634\u0647\u0631\u064a',
    ]
    metric_words = ['bopd', 'production', 'huile', 'oil', '\u0627\u0646\u062a\u0627\u062c']
    has_trend_word = any(w in q for w in trend_words)
    has_metric_word = any(w in q for w in metric_words)
    return has_well and has_year and has_trend_word and has_metric_word


def _is_current_status_question(question):
    if not question:
        return False
    q = question.lower()
    status_terms = [
        'current status', 'statut actuel', 'statut courant',
        'actuellement', 'currently', 'now', 'maintenant',
        'latest status', 'latest', 'most recent', 'dernier statut', "aujourd",
        'still producing', 'still active', 'toujours', '\u00e9tat actuel',
        'present condition', 'condition actuelle',
    ]
    return any(t in q for t in status_terms)


def _is_history_overview_question(question):
    if not question:
        return False
    q = question.lower()
    overview_terms = [
        'history', 'historique', 'all workover', 'tous les workover',
        'all interventions', 'toutes les interventions', 'list the',
        'liste des', 'every workover', 'chaque workover', 'overview',
        'all the', 'complete history', 'summary of all',
        'résumé', 'resume', 'what work', 'travaux',
        'bilan des', 'all operations', 'toutes les opérations',
        'what was done', 'ce qui a été fait',
    ]
    return any(t in q for t in overview_terms)


def _is_failed_answer(answer_text):
    """
    FIX: detect answers that are errors or empty so they are never
    injected back into the prompt as prior context — doing so confuses
    the LLM and causes placeholder / template output.
    """
    if not answer_text:
        return True
    markers = [
        'Technical error:', 'name \'', 'is not defined',
        'Traceback', 'Exception', 'Not specified',
        'do not contain specific information',
        'Unfortunately', 'NameError', 'AttributeError',
    ]
    return any(m in answer_text for m in markers)


def _other_year_dominates(chunk, target_year):
    """
    True only if another year clearly dominates — with noise floor.
    FIX: requires dominating year to appear 3+ times AND by a margin > 1
    over target_year count. Single header mentions no longer discard chunks.
    Counter is now imported at module level.
    """
    years = re.findall(r'\b(?:19|20)\d{2}\b', chunk.page_content)
    if not years:
        return False
    target_count = years.count(str(target_year))
    most_common_year, most_common_count = Counter(years).most_common(1)[0]
    return (
        most_common_year != str(target_year)
        and most_common_count > target_count + 1   # clear margin
        and most_common_count >= 3                  # ignore noise
    )


def _extract_event_blocks(chunks):
    """
    Locate workover title chunks ('WORKOVER - YYYY / Sequences of Events')
    and split all chunks into per-year blocks. Returns list of
    (year_str, [chunks]) sorted by chunk_index. Generic — works on any
    indexed document.
    """
    title_re = re.compile(
        r'WORKOVER\s*[-–—]?\s*((?:19|20)\d{2})\s*/?\s*'
        r'Sequences\s+of\s+Events',
        re.IGNORECASE
    )
    by_idx = sorted(chunks, key=lambda d: int(d.metadata.get('chunk_index', 0)))
    blocks = []
    current_year = None
    current_chunks = []
    for d in by_idx:
        m = title_re.search(d.page_content)
        if m:
            if current_year and current_chunks:
                blocks.append((current_year, current_chunks))
            current_year = m.group(1)
            current_chunks = [d]
        else:
            if current_year:
                current_chunks.append(d)
    if current_year and current_chunks:
        blocks.append((current_year, current_chunks))
    return blocks


def _select_event_block(chunks, target_year):
    """
    Return the chunks belonging to the workover block for target_year,
    sorted by chunk_index. Returns None when no title matches (caller
    falls back to existing logic).

    FIX: regex now makes 'Sequences of Events' optional so a chunk
    containing only 'WORKOVER - 2015' also anchors the block.
    """
    title_re = re.compile(
        r'WORKOVER\s*[-–—]?\s*((?:19|20)\d{2})'
        r'(?:\s*/?\s*Sequences?\s+of\s+Events?)?',
        re.IGNORECASE
    )

    anchor_filename = None
    for d in sorted(chunks, key=lambda d: int(d.metadata.get('chunk_index', 0))):
        m = title_re.search(d.page_content)
        if m and str(m.group(1)) == str(target_year):
            anchor_filename = d.metadata.get('filename')
            break

    blocks = _extract_event_blocks(chunks)
    if not blocks:
        return None

    for year, block_chunks in blocks:
        if str(year) == str(target_year):
            if anchor_filename:
                block_chunks = [c for c in block_chunks
                                if c.metadata.get('filename') == anchor_filename]
            return sorted(block_chunks,
                          key=lambda d: int(d.metadata.get('chunk_index', 0)))
    return None


def _find_densest_year_window(chunks, target_year, window=None):
    """
    Find the contiguous block of chunks (by chunk_index) most dense in
    target_year mentions, then filter chunks where another year dominates.

    FIX 1: window is now dynamic — sized from the number of chunks that
            actually mention target_year (min 12, max 35). This handles
            long workovers like the 2013 EZZ9 WO that spans 26 days.
    FIX 2: cross-year workovers — chunks from year+1 that are adjacent
            to the block are kept (handles Dec 2013 → Jan 2014 WO).
    FIX 3: Counter imported at module level — no more NameError.
    """
    if not chunks or not target_year:
        return chunks

    by_idx = sorted(chunks, key=lambda d: int(d.metadata.get('chunk_index', 0)))
    n = len(by_idx)

    # Dynamic window: count year hits, add buffer for conclusion chunks
    if window is None:
        year_hit_count = sum(1 for d in by_idx if str(target_year) in d.page_content)
        window = max(12, min(year_hit_count + 6, 35))

    if n <= window:
        return [d for d in by_idx if not _other_year_dominates(d, target_year)]

    # Sliding window to find densest region
    best_start, best_score = 0, -1
    for start in range(n - window + 1):
        win = by_idx[start:start + window]
        score = sum(1 for d in win if str(target_year) in d.page_content)
        if score > best_score:
            best_score, best_start = score, start

    block = by_idx[best_start:best_start + window]

    # Keep year+1 chunks — they are likely the conclusion of a cross-year WO
    next_year = str(int(target_year) + 1)

    def should_keep(chunk):
        content = chunk.page_content
        if str(target_year) in content:
            return True
        # Keep year+1 chunks only if no other contaminating year is present
        if next_year in content and str(target_year) not in content:
            years_in_chunk = re.findall(r'\b(?:19|20)\d{2}\b', content)
            counts = Counter(years_in_chunk)
            other_years = set(counts.keys()) - {next_year}
            if not other_years:
                return True
        return not _other_year_dominates(chunk, target_year)

    return [d for d in block if should_keep(d)]


def _localized_trend_word(direction, lang):
    labels = {
        'fr': {'up': 'En hausse', 'down': 'En baisse', 'flat': 'Stable'},
        'en': {'up': 'Increasing', 'down': 'Decreasing', 'flat': 'Stable'},
        'ar': {'up': '\u0645\u062a\u0632\u0627\u064a\u062f', 'down': '\u0645\u062a\u0631\u0627\u062c\u0639', 'flat': '\u0645\u0633\u062a\u0642\u0631'},
    }
    key = direction if direction in {'up', 'down'} else 'flat'
    return labels.get(lang, labels['fr'])[key]


def _trend_direction(previous_oil, current_oil):
    prev = float(previous_oil or 0)
    cur = float(current_oil or 0)
    if prev <= 0:
        return 'flat'
    delta_pct = ((cur - prev) / prev) * 100.0
    if delta_pct > 1.0:
        return 'up'
    if delta_pct < -1.0:
        return 'down'
    return 'flat'


def _sanitize_answer_language(answer, lang):
    if not answer:
        return answer
    replacements = {
        'fr': {
            r'\bExecutive Summary\b': 'Resume executif',
            r'\bMonthly Production History\b': 'Historique mensuel de production',
            r'\bTechnical Analysis\b': 'Analyse technique',
            r'\bEngineering Recommendations\b': 'Recommandations',
            r'\bIntervention Recommendations\b': 'Recommandations',
            r'\bRecommendations\b': 'Recommandations',
        },
        'en': {
            r'\bResume executif\b': 'Executive Summary',
            r'\bR\u00e9sum\u00e9 ex\u00e9cutif\b': 'Executive Summary',
            r'\bHistorique mensuel de production\b': 'Monthly Production History',
            r'\bAnalyse technique\b': 'Technical Analysis',
            r'\bRecommandations\b': 'Recommendations',
        },
        'ar': {
            r'\bExecutive Summary\b': '\u0627\u0644\u0645\u0644\u062e\u0635 \u0627\u0644\u062a\u0646\u0641\u064a\u0630\u064a',
            r'\bResume executif\b': '\u0627\u0644\u0645\u0644\u062e\u0635 \u0627\u0644\u062a\u0646\u0641\u064a\u0630\u064a',
            r'\bR\u00e9sum\u00e9 ex\u00e9cutif\b': '\u0627\u0644\u0645\u0644\u062e\u0635 \u0627\u0644\u062a\u0646\u0641\u064a\u0630\u064a',
            r'\bMonthly Production History\b': '\u0627\u0644\u062a\u0627\u0631\u064a\u062e \u0627\u0644\u0634\u0647\u0631\u064a \u0644\u0644\u0625\u0646\u062a\u0627\u062c',
            r'\bTechnical Analysis\b': '\u0627\u0644\u062a\u062d\u0644\u064a\u0644 \u0627\u0644\u062a\u0642\u0646\u064a',
            r'\bRecommendations\b': '\u0627\u0644\u062a\u0648\u0635\u064a\u0627\u062a',
            r'\bEngineering Recommendations\b': '\u0627\u0644\u062a\u0648\u0635\u064a\u0627\u062a',
            r'\bIntervention Recommendations\b': '\u0627\u0644\u062a\u0648\u0635\u064a\u0627\u062a',
        },
    }
    normalized = answer
    for pattern, target in replacements.get(lang, {}).items():
        normalized = re.sub(pattern, target, normalized, flags=re.IGNORECASE)
    return normalized


def _build_structured_well_year_trend_answer(question, lang, today_str):
    if not _is_well_year_trend_request(question):
        return None
    from apps.kpis.calculators import get_monthly_trend

    well = normalize_well_code(question)
    year = _extract_year(question)
    if not well or not year:
        return None

    rows = get_monthly_trend(well_key=well.well_key, year=year, lang=lang)
    if not rows:
        return None

    total_oil = sum(float(r.get('total_oil', 0) or 0) for r in rows)
    import calendar as _cal
    total_days = sum(_cal.monthrange(int(r.get('year', year)), int(r.get('month', 1)))[1] for r in rows)
    avg_bopd = (total_oil / total_days) if total_days > 0 else 0.0

    first_oil = float(rows[0].get('total_oil', 0) or 0)
    last_oil = float(rows[-1].get('total_oil', 0) or 0)
    annual_direction = _localized_trend_word(_trend_direction(first_oil, last_oil), lang)

    text = {
        'fr': {
            'title': f"## \U0001F6E2\uFE0F Champ EZZAOUIA - Tendance de production du puits {well.well_code}",
            'summary': f"**Resume executif:** La tendance BOPD du puits {well.well_code} en {year} montre une production {annual_direction.lower()}, avec une moyenne de {avg_bopd:,.1f} STB/j.",
            'monthly': "### Historique mensuel de production",
            'month_col_1': "Mois", 'month_col_2': "Huile (STB)",
            'month_col_3': "BSW%", 'month_col_4': "Tendance",
            'analysis_title': "### Analyse technique",
            'analysis_body': f"La tendance de production du puits {well.well_code} en {year} montre une moyenne BOPD stable de {avg_bopd:,.1f} STB/j, avec des fluctuations mensuelles.",
            'reco_title': "### Recommandations",
            'reco_1': "Suivi production: Continuer le suivi mensuel du debit et ajuster les conditions d'exploitation si necessaire.",
            'reco_2': "Maintenance puits: Planifier la maintenance preventive pour maintenir la stabilite de production.",
            'source': f"*Source: EZZAOUIA DWH - {today_str} - historical data 1994-2025*",
        },
        'en': {
            'title': f"## \U0001F6E2\uFE0F EZZAOUIA Field - Well {well.well_code} Production Trend",
            'summary': f"**Executive Summary:** The BOPD trend for well {well.well_code} in {year} shows {annual_direction.lower()} production, with an average of {avg_bopd:,.1f} STB/j.",
            'monthly': "### Monthly Production History",
            'month_col_1': "Month", 'month_col_2': "Oil (STB)",
            'month_col_3': "BSW%", 'month_col_4': "Trend",
            'analysis_title': "### Technical Analysis",
            'analysis_body': f"The production trend for {well.well_code} in {year} shows an average BOPD of {avg_bopd:,.1f} STB/j, with monthly fluctuations.",
            'reco_title': "### Recommendations",
            'reco_1': "Monitor Production: Continue monthly rate surveillance and adjust operating conditions when needed.",
            'reco_2': "Well Maintenance: Schedule preventive maintenance to sustain stable production.",
            'source': f"*Source: EZZAOUIA DWH - {today_str} - historical data 1994-2025*",
        },
        'ar': {
            'title': f"## \U0001F6E2\uFE0F \u062d\u0642\u0644 EZZAOUIA - \u0627\u062a\u062c\u0627\u0647 \u0625\u0646\u062a\u0627\u062c \u0627\u0644\u0628\u0626\u0631 {well.well_code}",
            'summary': f"**\u0627\u0644\u0645\u0644\u062e\u0635 \u0627\u0644\u062a\u0646\u0641\u064a\u0630\u064a:** \u064a\u064f\u0638\u0647\u0631 \u0627\u062a\u062c\u0627\u0647 BOPD \u0644\u0644\u0628\u0626\u0631 {well.well_code} \u0641\u064a {year} \u0625\u0646\u062a\u0627\u062c\u0627\u064b {annual_direction}\u060c \u0628\u0645\u062a\u0648\u0633\u0637 {avg_bopd:,.1f} STB/j.",
            'monthly': "### \u0627\u0644\u062a\u0627\u0631\u064a\u062e \u0627\u0644\u0634\u0647\u0631\u064a \u0644\u0644\u0625\u0646\u062a\u0627\u062c",
            'month_col_1': "\u0627\u0644\u0634\u0647\u0631", 'month_col_2': "\u0627\u0644\u0646\u0641\u0637 (STB)",
            'month_col_3': "BSW%", 'month_col_4': "\u0627\u0644\u0627\u062a\u062c\u0627\u0647",
            'analysis_title': "### \u0627\u0644\u062a\u062d\u0644\u064a\u0644 \u0627\u0644\u062a\u0642\u0646\u064a",
            'analysis_body': f"\u064a\u064f\u0638\u0647\u0631 \u0627\u062a\u062c\u0627\u0647 \u0625\u0646\u062a\u0627\u062c \u0627\u0628\u0626\u0631 {well.well_code} \u0641\u064a {year} \u0645\u062a\u0648\u0633\u0637 BOPD \u0628\u0642\u064a\u0645\u0629 {avg_bopd:,.1f} STB/j \u0645\u0639 \u062a\u0630\u0628\u0630\u0628\u0627\u062a \u0634\u0647\u0631\u064a\u0629.",
            'reco_title': "### \u0627\u0644\u062a\u0648\u0635\u064a\u0627\u062a",
            'reco_1': "\u0645\u062a\u0627\u0628\u0639\u0629 \u0627\u0644\u0625\u0646\u062a\u0627\u062c: \u0627\u0644\u0627\u0633\u062a\u0645\u0631\u0627\u0631 \u0641\u064a \u0627\u0644\u0645\u0631\u0627\u0642\u0628\u0629 \u0627\u0644\u0634\u0647\u0631\u064a\u0629 \u0648\u062a\u0639\u062f\u064a\u0644 \u0638\u0631\u0648\u0641 \u0627\u0644\u062a\u0634\u063a\u064a\u0644 \u0639\u0646\u062f \u0627\u0644\u062d\u0627\u062c\u0629.",
            'reco_2': "\u0635\u064a\u0627\u0646\u0629 \u0627\u0644\u0628\u0626\u0631: \u062c\u062f\u0648\u0644\u0629 \u0635\u064a\u0627\u0646\u0629 \u0648\u0642\u0627\u0626\u064a\u0629 \u0644\u0644\u062d\u0641\u0627\u0638 \u0639\u0644\u0649 \u0627\u0633\u062a\u0642\u0631\u0627\u0631 \u0627\u0644\u0625\u0646\u062a\u0627\u062c.",
            'source': f"*\u0627\u0644\u0645\u0635\u062f\u0631: EZZAOUIA DWH - {today_str} - historical data 1994-2025*",
        },
    }.get(lang, None)

    if text is None:
        return None

    lines = [
        text['title'], "",
        text['summary'], "",
        text['monthly'],
        f"| {text['month_col_1']} | {text['month_col_2']} | {text['month_col_3']} | {text['month_col_4']} |",
        "|---|---:|---:|---|",
    ]
    prev_oil = None
    for r in rows:
        oil = float(r.get('total_oil', 0) or 0)
        bsw = float(r.get('avg_bsw', 0) or 0)
        trend_word = _localized_trend_word(_trend_direction(prev_oil, oil), lang) if prev_oil is not None else _localized_trend_word('flat', lang)
        month_label = f"{r.get('month_name', '')} {r.get('year', year)}"
        lines.append(f"| {month_label} | {oil:,.0f} | {bsw:.1f}% | {trend_word} |")
        prev_oil = oil

    lines.extend([
        "", text['analysis_title'], text['analysis_body'], "",
        text['reco_title'],
        f"1. {text['reco_1']}",
        f"2. {text['reco_2']}",
        "", text['source'],
    ])
    return "\n".join(lines)


def _build_structured_comments_answer(question, comments_rows, lang, today_str,
                                      search_words=None):
    if not comments_rows:
        return None

    well_ref = normalize_well_code(question)
    well_code_str = well_ref.well_code if well_ref else "FIELD"

    from datetime import datetime

    periods = []
    current_period = [comments_rows[0]]
    for row in comments_rows[1:]:
        try:
            prev_date = datetime.strptime(current_period[-1]['date'][:10], '%Y-%m-%d')
            curr_date = datetime.strptime(row['date'][:10], '%Y-%m-%d')
            if (curr_date - prev_date).days <= 5:
                current_period.append(row)
            else:
                periods.append(current_period)
                current_period = [row]
        except Exception:
            current_period.append(row)
    periods.append(current_period)

    L = {
        'en': {
            'title': f"## 📋 Field Notes — {well_code_str}",
            'found': (
                f"{len(comments_rows)} records found in DimDate field notes"
                + (f" for well {well_code_str}" if well_ref else "")
                + f" — {len(periods)} distinct period(s) identified."
            ),
            'periods_title': "### Periods identified",
            'p_header': "| # | Start | End | Days |",
            'p_sep': "|:-:|-------|-----|-----:|",
            'excerpts_title': "### Field note excerpts",
            'e_header': "| Date | Excerpt |",
            'e_sep': "|------|---------|",
            'source': f"*Source: EZZAOUIA DWH — DimDate.comments — {today_str}*",
        },
        'fr': {
            'title': f"## 📋 Notes de terrain — {well_code_str}",
            'found': (
                f"{len(comments_rows)} entrées trouvées dans DimDate"
                + (f" pour le puits {well_code_str}" if well_ref else "")
                + f" — {len(periods)} période(s) identifiée(s)."
            ),
            'periods_title': "### Périodes identifiées",
            'p_header': "| # | Début | Fin | Jours |",
            'p_sep': "|:-:|-------|-----|------:|",
            'excerpts_title': "### Extraits des notes de terrain",
            'e_header': "| Date | Extrait |",
            'e_sep': "|------|---------|",
            'source': f"*Source: EZZAOUIA DWH — DimDate.comments — {today_str}*",
        },
        'ar': {
            'title': f"## 📋 ملاحظات ميدانية — {well_code_str}",
            'found': (
                f"تم العثور على {len(comments_rows)} سجلاً في DimDate"
                + (f" للبئر {well_code_str}" if well_ref else "")
                + f" — {len(periods)} فترة محددة."
            ),
            'periods_title': "### الفترات المحددة",
            'p_header': "| # | البداية | النهاية | الأيام |",
            'p_sep': "|:-:|---------|---------|-------:|",
            'excerpts_title': "### مقتطفات من الملاحظات الميدانية",
            'e_header': "| التاريخ | المقتطف |",
            'e_sep': "|---------|---------|",
            'source': f"*المصدر: EZZAOUIA DWH — DimDate.comments — {today_str}*",
        },
    }.get(lang, {
        'title': f"## 📋 Field Notes — {well_code_str}",
        'found': f"{len(comments_rows)} records found — {len(periods)} period(s).",
        'periods_title': "### Periods identified",
        'p_header': "| # | Start | End | Days |",
        'p_sep': "|:-:|-------|-----|-----:|",
        'excerpts_title': "### Field note excerpts",
        'e_header': "| Date | Excerpt |",
        'e_sep': "|------|---------|",
        'source': f"*Source: EZZAOUIA DWH — DimDate.comments — {today_str}*",
    })

    lines = [L['title'], L['found'], "", L['periods_title'], L['p_header'], L['p_sep']]

    for i, period in enumerate(periods, 1):
        try:
            start = period[0]['date'][:10]
            end = period[-1]['date'][:10]
            d1 = datetime.strptime(start, '%Y-%m-%d')
            d2 = datetime.strptime(end, '%Y-%m-%d')
            days = (d2 - d1).days + 1
            start_fmt = d1.strftime('%d/%m/%Y')
            end_fmt = d2.strftime('%d/%m/%Y')
        except Exception:
            start_fmt, end_fmt, days = start, end, '?'
        lines.append(f"| {i} | {start_fmt} | {end_fmt} | {days} |")

    lines += ["", L['excerpts_title'], L['e_header'], L['e_sep']]

    for row in comments_rows:
        try:
            date_fmt = datetime.strptime(row['date'][:10], '%Y-%m-%d').strftime('%d/%m/%Y')
        except Exception:
            date_fmt = row['date'][:10]
        raw = row['comments'].replace('\n', ' ')
        parts = re.split(r';\*\s*|\.\*\s*', raw)
        well_num_local = re.search(r'\d+', well_code_str).group() if well_ref else None
        relevant_parts = []
        for part in parts:
            part = part.strip()
            if not part:
                continue
            part_lower = part.lower()
            has_keyword = any(w.lower() in part_lower for w in (search_words or []))
            has_well = False
            if well_num_local:
                well_mentions_local = re.findall(r'EZZ\s*#?\s*(\d+)', part, re.IGNORECASE)
                has_well = well_num_local in [m for m in well_mentions_local if m == well_num_local]
            else:
                has_well = True
            if has_keyword or has_well:
                relevant_parts.append(part)
        if relevant_parts:
            excerpt = ' | '.join(relevant_parts)[:400]
        else:
            excerpt = raw[:200]
        excerpt = excerpt.replace('|', '-').replace('\n', ' ')
        flag = ""
        if well_ref:
            num = re.search(r'\d+', well_code_str)
            if num:
                asked_pattern = re.compile(rf'EZZ\s*#?\s*{num.group()}\b', re.IGNORECASE)
                all_wells = re.findall(r'EZZ\s*#?\s*\d+', row['comments'], re.IGNORECASE)
                other_wells = [w for w in all_wells if not asked_pattern.search(w)]
                if other_wells and not asked_pattern.search(row['comments']):
                    flag = f" ⚠️ *refers to {other_wells[0]}*"
        lines.append(f"| {date_fmt} | {excerpt}{flag} |")

    lines += ["", "---", L['source']]
    return "\n".join(lines)


def generate_suggestions(question, well=None, lang='fr'):
    q = question.lower()
    lang = lang if lang in {'fr', 'en', 'ar'} else 'fr'

    def choose(fr_text, en_text, ar_text):
        return {'fr': fr_text, 'en': en_text, 'ar': ar_text}.get(lang, fr_text)

    if well:
        wc = well.well_code
        return [
            choose(
                f"Quelles interventions workover sont recommandées pour {wc} ?",
                f"What workover interventions are recommended for well {wc}?",
                f"ما هي تدخلات الـ workover الموصى بها للبئر {wc}؟",
            ),
            choose(
                f"Comparez {wc} avec la moyenne du champ (BSW, GOR, BOPD)",
                f"Compare well {wc} vs field average (BSW, GOR, BOPD)",
                f"قارن البئر {wc} مع متوسط الحقل (BSW, GOR, BOPD)",
            ),
            choose(
                f"Montrez l'évolution mensuelle de la production de {wc} sur 2024",
                f"Show monthly production trend for well {wc} in 2024",
                f"اعرض الاتجاه الشهري لإنتاج البئر {wc} في 2024",
            ),
        ]

    if any(w in q for w in ['meilleur', 'top', 'classement', 'producer', 'performer']):
        return [
            choose(
                "Analysez le WCT et GOR des 5 puits les moins performants",
                "Analyze WCT and GOR for the 5 lowest-performing wells",
                "حلّل WCT و GOR للآبار الخمسة الأقل أداءً",
            ),
            choose(
                "Quel est l'impact du BSW élevé de EZZ10 sur la production nette ?",
                "What is the impact of EZZ10's high BSW on net oil production?",
                "ما تأثير ارتفاع BSW في EZZ10 على صافي إنتاج النفط؟",
            ),
            choose(
                "Comparez la production annuelle 2023 vs 2024 par puits",
                "Compare annual production 2023 vs 2024 by well",
                "قارن الإنتاج السنوي 2023 مقابل 2024 لكل بئر",
            ),
        ]

    if any(w in q for w in ['bsw', 'gor', 'wct', 'water cut', 'reservoir', 'réservoir']):
        return [
            choose(
                "Quels puits nécessitent une intervention workover en priorité ?",
                "Which wells require priority workover intervention?",
                "ما الآبار التي تحتاج تدخل workover بشكل عاجل؟",
            ),
            choose(
                "Analysez l'évolution du BSW du champ de 2020 à 2025",
                "Analyze field BSW evolution from 2020 to 2025",
                "حلّل تطور BSW للحقل من 2020 إلى 2025",
            ),
            choose(
                "Quel est le potentiel EOR pour le champ EZZAOUIA ?",
                "What is the EOR potential for the EZZAOUIA field?",
                "ما إمكانية EOR لحقل عزاوية؟",
            ),
        ]

    return [
        choose(
            "Analysez la performance globale du champ EZZAOUIA",
            "Analyze the overall performance of the EZZAOUIA field",
            "حلّل الأداء العام لحقل عزاوية",
        ),
        choose(
            "Quels sont les top 5 puits producteurs et leur BSW ?",
            "What are the top 5 producing wells and their BSW?",
            "ما هي أفضل 5 آبار إنتاجاً وما هو BSW لكل منها؟",
        ),
        choose(
            "Analysez le WCT et GOR du champ en 2024 et 2025",
            "Analyze field WCT and GOR for 2024 and 2025",
            "حلّل WCT و GOR للحقل في 2024 و2025",
        ),
    ]


def _detect_task(question, doc_id, doc_ids, needs_comments, well, use_sql=True, use_docs=True):
    if not use_sql or doc_id or doc_ids:
        return 'document_qa'

    q = question.lower()

    if 'from db' in q or 'from database' in q:
        return 'production_kpis'

    if any(w in q for w in [
        'tcm', 'ocm', 'meeting', 'réunion', 'decisions', 'discussed',
        'reported', 'minutes', 'mom', 'agenda', 'presentation',
        'budget', 'forecast', 'hse', 'report'
    ]):
        return 'document_qa'

    has_well = well is not None

    if needs_comments:
        return 'operational_history'

    if has_well and any(w in q for w in [
        'analyse', 'analysis', 'analyser', 'tell me about',
        'give me', 'overview', 'deep dive', 'about ezz',
        'from both', 'combine', 'summary', 'situation',
        'état', 'etat', 'performance', 'status', 'bilan',
        'detail', 'historique', 'history',
    ]):
        return 'well_analysis'

    if any(w in q for w in [
        'field', 'champ', 'global', 'summary', 'résumé',
        'bilan', 'all wells', 'tous les puits', 'overview'
    ]) and not has_well:
        return 'field_summary'

    if has_well and any(w in q for w in [
        'caused', 'why', 'what happened', 'failure', 'failed',
        'history', 'when did', 'how did', 'what was', 'describe',
        'explain', 'detail', 'event', 'issue', 'problem',
        'workover', 'intervention', 'completion', 'performed',
        'abandoned', 'plugged', 'drilled', 'spud', 'design',
        'what caused', 'what is the', 'tell me'
    ]):
        return 'document_qa'

    if has_well or any(w in q for w in [
        'bopd', 'bsw', 'gor', 'production', 'top', 'ranking',
        'meilleur', 'classement', 'trend', 'monthly'
    ]):
        return 'production_kpis'

    return 'document_qa'


def _build_well_confusion_rule(well_ref):
    if not well_ref:
        return ""
    wnum = re.search(r'\d+', well_ref.well_code)
    if not wnum:
        return ""
    n = wnum.group().lstrip('0') or '0'
    similar = []
    if n == '1':
        similar = ['11']
    elif n == '11':
        similar = ['1']
    elif n == '2':
        similar = ['12']
    elif n == '12':
        similar = ['2']
    if len(n) == 1:
        similar.append(f"1{n}")
    elif len(n) == 2 and n.startswith('1'):
        similar.append(n[1])

    similar = list(set(similar))

    if not similar:
        rule = (
            f"- The question is about EZZ{n} ONLY. "
            f"Answer exclusively about EZZ{n}. NEVER mix data from other wells.\n"
        )
    else:
        others = " and ".join(f"EZZ{s}" for s in similar)
        rule = (
            f"- The question asks about EZZ{n} — answer ONLY about EZZ{n}, "
            f"NEVER about {others}\n"
            f"- EZZ{n} and {others} are COMPLETELY DIFFERENT wells — "
            f"never confuse or mix their data\n"
        )
    return rule


def ask(question, history=None, doc_id=None, doc_ids=None, filename=None, user=None):
    if doc_ids:
        doc_id = doc_ids[0] if len(doc_ids) == 1 else None

    try:
        today_str = datetime.date.today().strftime('%d/%m/%Y')
        lang = detect_language(question)
        langue_nom = {'fr': 'français', 'en': 'English', 'ar': 'عربي'}.get(lang, 'français')

        q_lower = question.lower().strip()

        use_docs = True
        use_sql = True

        if 'from docs' in q_lower or 'from documents' in q_lower:
            use_sql = False
            use_docs = True
            question = re.sub(
                r'\s*(from docs|from documents)\s*$',
                '', question, flags=re.IGNORECASE).strip()
            q_lower = question.lower().strip()
            logger.info("Source: DOCUMENTS ONLY")

        elif 'from db' in q_lower or 'from database' in q_lower or 'from sql' in q_lower:
            use_sql = True
            use_docs = False
            question = re.sub(
                r'\s*(from db|from database|from sql)\s*$',
                '', question, flags=re.IGNORECASE).strip()
            q_lower = question.lower().strip()
            logger.info("Source: DATABASE ONLY")

        elif 'from both' in q_lower:
            use_sql = True
            use_docs = True
            question = re.sub(
                r'\s*from both\s*$', '',
                question, flags=re.IGNORECASE).strip()
            q_lower = question.lower().strip()
            logger.info("Source: BOTH SQL + DOCS")

        salutations = ['bonjour', 'bonsoir', 'salut', 'hello', 'hi', 'salam', 'merci',
                       'مرحبا', 'السلام عليكم', 'شكرا']
        if any(q_lower == s or q_lower.startswith(s + ' ') for s in salutations):
            greeting = {
                'fr': "Bonjour ! Je suis Dr. EZZAOUIA, votre expert en ingénierie pétrolière pour le champ EZZAOUIA (MARETAP S.A., CPF Zarzis). Posez-moi une question sur la production, l'analyse des puits, les KPIs de réservoir ou les rapports techniques.",
                'en': "Hello! I am Dr. EZZAOUIA, your petroleum engineering expert for the EZZAOUIA field (MARETAP S.A., CPF Zarzis). Ask me about production performance, well analysis, reservoir KPIs, or technical reports.",
                'ar': "مرحباً! أنا الدكتور عزاوية، خبيرك في هندسة البترول لحقل عزاوية (MARETAP S.A.، CPF جرجيس). اطرح سؤالك حول الإنتاج أو تحليل الآبار أو مؤشرات الخزان أو التقارير التقنية.",
            }.get(lang)
            return {'answer': greeting, 'chart_data': None, 'suggestions': generate_suggestions(question, lang=lang)}

        structured_trend = _build_structured_well_year_trend_answer(question, lang, today_str)
        if structured_trend:
            well = normalize_well_code(question)
            return {
                'answer': structured_trend,
                'chart_data': build_chart_data(question) if detect_chart_request(question) else None,
                'suggestions': generate_suggestions(question, well=well, lang=lang),
            }

        logger.info(f"Question: {question[:120]}")

        search_query = question
        year_match = re.search(r'\b(20\d{2})\b', question)
        well_match = re.search(r'\b(ezz?\s*[-#]?\s*\d+)\b', question, re.IGNORECASE)
        if year_match:
            search_query += f" {year_match.group(1)} production operations"
        if well_match:
            search_query += f" {well_match.group(1)} workover intervention completion tubing failure rejected joints sucker rod wear 2013 2015 2017 sequences of events rig acceptance POOH"

        COMMENT_TRIGGER_KEYWORDS_EARLY = [
            'comment', 'remarque', 'note', 'period', 'période', 'during',
            'pendant', 'quand', 'when', 'monitoring', 'surveillance',
            'consulting', 'intervention', 'activit', 'operat', 'travaux',
            'srp', 'workover', 'shut-in', 'shut in', 'fermeture', 'reprise',
            'depuis', 'depuis quand', 'how long', 'combien de temps',
        ]
        use_comments = not (use_sql == False)
        needs_comments = (
            any(kw in q_lower for kw in COMMENT_TRIGGER_KEYWORDS_EARLY)
            and not doc_id
            and not doc_ids
            and use_comments
        )

        DOC_PRIORITY_KEYWORDS = [
            'tubing integrity', 'intégrité tubing', 'workover history',
            'completion', 'casing', 'packer', 'wellbore', 'perforation',
            'well history', 'historique puits', 'caused', 'cause',
            'failure', 'why', 'what happened', 'rejected', 'worn',
        ]
        is_doc_priority = any(kw in q_lower for kw in DOC_PRIORITY_KEYWORDS)

        PRODUCTION_KEYWORDS_FOR_K = [
            'top', 'meilleur', 'classement', 'performer', 'production', 'bopd',
            'stb', 'total', 'barils', 'huile', 'oil', 'resume', 'résumé',
            'bilan', 'global', 'champ', 'field', 'kpi', 'performance',
            'wct', 'bsw', 'gor', 'water cut', 'reservoir', 'réservoir',
            'analyse', 'analysis', 'analyser', 'deep dive', 'overview', 'give me',
        ]
        is_doc_only_question = (
            not any(w in q_lower for w in PRODUCTION_KEYWORDS_FOR_K)
            or needs_comments
            or is_doc_priority
        )

        if is_doc_priority:
            import re as _re_year
            year_in_q = _re_year.search(r'\b(20\d{2})\b', q_lower)
            retrieval_k = 30 if year_in_q else 20
        elif is_doc_only_question:
            retrieval_k = 15
        else:
            retrieval_k = 6

        if 'from docs' in q_lower and not doc_id and not doc_ids:
            retrieval_k = 20

        logger.info(f"Retrieval k={retrieval_k} ({'doc-priority' if is_doc_priority else 'doc/comments' if is_doc_only_question else 'production'})")

        FIELD_WIDE_DOC_KEYWORDS = [
            'all wells', 'tous les puits', 'chaque puits', 'every well',
            'for each well', 'summary table', 'tableau', 'summarize',
            'résumé de tous', 'current status of all',
        ]
        is_field_wide_doc = any(kw in q_lower for kw in FIELD_WIDE_DOC_KEYWORDS)

        detected_well_num = None
        TCM_KEYWORDS = ['tcm', 'ocm', 'meeting', 'mom', 'minutes', 'decisions',
                        'discussed', 'reported', 'budget', 'forecast', 'hse']
        is_tcm_question = any(kw in q_lower for kw in TCM_KEYWORDS)

        if well_match and not is_tcm_question:
            num = re.search(r'\d+', well_match.group(1))
            if num:
                detected_well_num = num.group()

        effective_doc_id = None if is_field_wide_doc else doc_id
        effective_filename = None if is_field_wide_doc else filename

        if is_field_wide_doc:
            doc_results = []
            logger.info("Field-wide question — skipping initial retrieval")
        else:
            doc_results = retrieve_smart(
                query=search_query, doc_id=effective_doc_id,
                filename=effective_filename,
                k=retrieval_k, well_num=detected_well_num
            )
        logger.info(f"DOC RESULTS: {len(doc_results)} chunks")

        if 'workover' in q_lower and 'from docs' in q_lower and detected_well_num:
            vs = get_global_vectorstore()
            col = vs._collection
            from langchain.schema import Document as LCDoc
            DGH_FILE = f"DGH_EZZ{detected_well_num}.pdf"
            all_dgh = col.get(where={'filename': DGH_FILE}, include=['documents', 'metadatas'])
            if all_dgh and all_dgh.get('documents'):
                forced = [
                    LCDoc(page_content=doc, metadata=meta)
                    for doc, meta in zip(all_dgh['documents'], all_dgh['metadatas'])
                ]
                forced_keys = {_chunk_key(d.page_content) for d in forced}
                doc_results = forced + [
                    r for r in doc_results
                    if _chunk_key(r.page_content) not in forced_keys
                ]
                logger.info(f"Workover forced: all {len(forced)} chunks from {DGH_FILE}")

        tcm_match = re.search(r'\b(?:from\s+)?(tcm|ocm)\s*#?\s*(\d+)\b', q_lower)
        if tcm_match:
            tcm_num = tcm_match.group(2)
            vs = get_global_vectorstore()
            col = vs._collection
            from langchain.schema import Document as LCDoc
            available = get_available_documents()
            tcm_files = [f for f in available if tcm_num in f.replace(' ', '').replace('_', '').replace('#', '').lower()]
            logger.info(f"TCM {tcm_num} matched files: {tcm_files}")
            tcm_chunks = []
            for fname in tcm_files:
                r = col.get(where={'filename': fname}, include=['documents', 'metadatas'])
                for doc, meta in zip(r['documents'], r['metadatas']):
                    tcm_chunks.append(LCDoc(page_content=doc, metadata=meta))
            if tcm_chunks:
                doc_results = tcm_chunks + doc_results
                logger.info(f"TCM {tcm_num} forced: {len(tcm_chunks)} chunks from {tcm_files}")

        if year_match and not detected_well_num and not is_tcm_question:
            target_yr = year_match.group(1)
            vs = get_global_vectorstore()
            col = vs._collection
            from langchain.schema import Document as LCDoc
            year_boosted = []
            existing_keys = {_chunk_key(r.page_content) for r in doc_results}
            all_meta = col.get(include=['metadatas', 'documents'])
            for doc, meta in zip(all_meta['documents'], all_meta['metadatas']):
                if target_yr in doc:
                    if _chunk_key(doc) not in existing_keys:
                        year_boosted.append(LCDoc(page_content=doc, metadata=meta))
                        existing_keys.add(_chunk_key(doc))
            if year_boosted:
                doc_results = year_boosted[:8] + doc_results
                logger.info(f"Year {target_yr} boosted: {len(year_boosted)} chunks added")

        well_ref = normalize_well_code(question)
        task = _detect_task(question, doc_id, doc_ids, needs_comments, well_ref, use_sql=use_sql, use_docs=use_docs)
        logger.info(f"Task detected: {task}")

        for i, r in enumerate(doc_results[:5]):
            logger.info(f"  Chunk {i+1}: [{r.metadata.get('filename','?')}] {r.page_content[:150]}")

        if doc_id and doc_results:
            sample = " ".join(d.page_content for d in doc_results[:10])
            if not is_petroleum_document(sample):
                return {
                    'answer': 'Ce document ne semble pas lié au secteur pétrolier ou à MARETAP. Veuillez joindre un document technique pétrolier (rapport de production, étude réservoir, rapport workover, etc.).',
                    'chart_data': None,
                    'suggestions': [],
                }

        doc_context = ""
        if doc_results:
            import re as _re2
            year_in_q = _re2.search(r'\b(20\d{2}|19\d{2})\b', question)
            target_year = year_in_q.group(1) if year_in_q else None

            # FIX: only inject tail chunks for CURRENT STATUS questions,
            # not for historical year-specific queries (wastes budget)
            _inject_tail_first = _is_current_status_question(question)
            _is_historical_year_query = bool(target_year) and not _inject_tail_first
            logger.info(
                f"Tail-chunk mode: "
                f"{'FRONT (status)' if _inject_tail_first else 'BACK (historical)' if _is_historical_year_query else 'BACK (general)'}"
            )

            PRIORITY_TERMS = [
                'rejected', 'lost thickness', 'sucker rod', 'wash out',
                'failure', 'integrity', 'abandoned', 'plug', 'hydrocarbons',
                'circulation loss', 'cause', 'reason', 'problem', 'issue',
                'workover', 'sequences of events', 'rig accepted', 'pooh',
                'completion', 'packer', 'tubing hanger', 'july', 'april', 'october',
                'up to current', 'produced without interruption', 'stable'
            ]

            def doc_chunk_score(d):
                score = 0
                content = d.page_content.lower()
                if target_year and target_year in d.page_content:
                    score += 50
                if any(t in content for t in PRIORITY_TERMS):
                    score += 5
                return score

            if detected_well_num and not is_field_wide_doc:
                expected_file = f"DGH_EZZ{detected_well_num}.pdf"
                well_chunks = [d for d in doc_results
                               if d.metadata.get('filename') == expected_file]
                other_chunks = [d for d in doc_results
                                if d.metadata.get('filename') != expected_file]

                if well_chunks:
                    HIGH_VALUE_TERMS = [
                        'integrity', 'rejected', 'leak', 'failure', 'workover',
                        'lost thickness', 'sucker rod', 'wash out', 'casing',
                        'closed', 'shut-in', 'shut in', 'abandoned', 'plugged',
                        'fish', 'up to current', 'produced without',
                        'sequences of events', 'well status', 'well resumed',
                        'cross channeling', 'cross channel', 'casing was failure',
                        'tubing test', 'pressure test', 'packer test',
                        'no additional flow', 'ceased production', 'bsw',
                        'water cut', 'disposal', 'injection', 'sidetrack',
                        'p&a', 'plug and abandon', 'cemented', 'perforated',
                        'well shut in', 'well shut-in', 'production stopped',
                        'intervention', 'slickline', 'swabbing', 'logging',
                        'rig released', 'well resumed production',
                        'srp well intervention', 'december 2015',
                        'permanently closed', 'zebbag water', 'jurassic layers',
                        'no flow', 'no returns'
                    ]
                    SKIP_TERMS = [
                        'mail address', 'immeuble monia', 'tél :', 'fax :',
                        '--- page', 'les berges du lac', 'rc : b116521996',
                        'mf : 0437877x', 'contact@maretap'
                    ]

                    high_value = []
                    low_value = []
                    for c in well_chunks:
                        content = c.page_content.lower()
                        non_header_content = content
                        for skip in SKIP_TERMS:
                            non_header_content = non_header_content.replace(skip, '')
                        if len(non_header_content.strip()) < 10:
                            continue
                        if any(term in content for term in HIGH_VALUE_TERMS):
                            high_value.append(c)
                        else:
                            low_value.append(c)

                    all_high_sorted = sorted(
                        high_value,
                        key=lambda d: int(d.metadata.get('chunk_index', 0))
                    )
                    if len(all_high_sorted) > 5:
                        late_chunks = all_high_sorted[-5:]
                        early_chunks = all_high_sorted[:-5]
                        high_value_ordered = late_chunks + early_chunks
                    else:
                        high_value_ordered = all_high_sorted

                    low_value_ordered = sorted(
                        low_value,
                        key=lambda d: int(d.metadata.get('chunk_index', 0))
                    )

                    sorted_results = high_value_ordered + low_value_ordered[:5]

                    # FIX: skip tail injection for historical year queries —
                    # tail chunks (completion schematic, last page) are
                    # irrelevant for e.g. "what happened in 2013 workover"
                    # and waste ~3600 chars of the 18000-char context budget.
                    if not _is_historical_year_query:
                        try:
                            from langchain.schema import Document as LCDoc
                            _vs = get_global_vectorstore()
                            _col = _vs._collection
                            _all_file = _col.get(
                                where={'filename': expected_file},
                                include=['documents', 'metadatas']
                            )
                            if _all_file and _all_file.get('documents'):
                                _all_chunks = sorted(
                                    [LCDoc(page_content=doc, metadata=meta)
                                     for doc, meta in zip(_all_file['documents'], _all_file['metadatas'])],
                                    key=lambda d: int(d.metadata.get('chunk_index', 0))
                                )
                                logger.info(f"ChromaDB direct: {len(_all_chunks)} total chunks in {expected_file}")
                                for _tail_chunk in reversed(_all_chunks[-2:]):
                                    _tail_key = _chunk_key(_tail_chunk.page_content)
                                    sorted_results = [
                                        d for d in sorted_results
                                        if _chunk_key(d.page_content) != _tail_key
                                    ]
                                    if _inject_tail_first:
                                        sorted_results = [_tail_chunk] + sorted_results
                                    else:
                                        sorted_results = sorted_results + [_tail_chunk]
                                    logger.info(
                                        f"Force-injected chunk index "
                                        f"{_tail_chunk.metadata.get('chunk_index')} "
                                        f"at position {'0 (front)' if _inject_tail_first else 'end (back)'}"
                                        f" from {expected_file}"
                                    )
                        except Exception as _e:
                            logger.warning(f"Force-inject failed: {_e}")
                    else:
                        logger.info(
                            f"Tail injection SKIPPED — historical year query "
                            f"(year={target_year}), preserving context budget"
                        )

                    logger.info(
                        f"Single-well filter: {len(high_value)} high-value, "
                        f"{len(low_value)} low-value chunks for {expected_file}"
                    )
                else:
                    sorted_results = sorted(doc_results, key=doc_chunk_score, reverse=True)
            else:
                sorted_results = sorted(doc_results, key=doc_chunk_score, reverse=True)

            # Hard cap on number of chunks
            chunk_cap = MAX_DOC_CHUNKS_FIELD if is_field_wide_doc else MAX_DOC_CHUNKS_NORMAL
            if len(sorted_results) > chunk_cap:
                logger.info(
                    f"Chunk cap applied: {len(sorted_results)} -> {chunk_cap} chunks"
                )
                sorted_results = sorted_results[:chunk_cap]

            # Dense year window for year-specific single-well queries
            if detected_well_num and not is_field_wide_doc and not _inject_tail_first:
                _expected_file_15 = f"DGH_EZZ{detected_well_num}.pdf"
                _well_sr = [d for d in sorted_results
                            if d.metadata.get('filename') == _expected_file_15]
                _non_well_sr = [d for d in sorted_results
                                if d.metadata.get('filename') != _expected_file_15]

                _q_year_m = _re2.search(r'\b(20\d{2}|19\d{2})\b', question)
                if _q_year_m:
                    _target_yr_15 = _q_year_m.group(1)
                    _window_15 = _find_densest_year_window(_well_sr, _target_yr_15)
                    if _window_15:
                        _seen_15 = {_chunk_key(d.page_content) for d in _window_15}
                        _rest_15 = [d for d in sorted_results
                                    if _chunk_key(d.page_content) not in _seen_15]
                        sorted_results = _window_15 + _rest_15
                        logger.info(
                            f"Dense window year={_target_yr_15}: {len(_window_15)} "
                            f"consecutive chunks at front (strict year filter applied)"
                        )
                elif _is_history_overview_question(question):
                    _sorted_well = sorted(
                        _well_sr,
                        key=lambda d: int(d.metadata.get('chunk_index', 0))
                    )
                    sorted_results = _sorted_well + _non_well_sr
                    logger.info("History overview — full chunk_index ordering")
                else:
                    _all_yrs = []
                    for _d in _well_sr:
                        _all_yrs += _re2.findall(r'\b(?:19|20)\d{2}\b', _d.page_content)
                    if _all_yrs:
                        _fallback_yr = Counter(_all_yrs).most_common(1)[0][0]
                        _window_fb = _find_densest_year_window(_well_sr, _fallback_yr)
                        if _window_fb:
                            _seen_fb = {_chunk_key(d.page_content) for d in _window_fb}
                            _rest_fb = [d for d in sorted_results
                                        if _chunk_key(d.page_content) not in _seen_fb]
                            sorted_results = _window_fb + _rest_fb
                            logger.info(
                                f"Dense window fallback year={_fallback_yr}: "
                                f"{len(_window_fb)} consecutive chunks at front"
                            )

            # FIX 19: block anchoring on workover title
            _fix19_year_m = _re2.search(r'\b(20\d{2}|19\d{2})\b', question)
            _fix19_target = _fix19_year_m.group(1) if _fix19_year_m else None
            if (
                _fix19_target
                and not _inject_tail_first
                and not is_field_wide_doc
            ):
                _fix19_block = _select_event_block(sorted_results, _fix19_target)
                if _fix19_block:
                    # FIX: sort the block chronologically so LLM sees events in order
                    _fix19_block = sorted(
                        _fix19_block,
                        key=lambda d: int(d.metadata.get('chunk_index', 0))
                    )
                    _seen_19 = {_chunk_key(d.page_content) for d in _fix19_block}
                    _rest_19 = [d for d in sorted_results
                                if _chunk_key(d.page_content) not in _seen_19]
                    sorted_results = _fix19_block + _rest_19
                    logger.info(
                        f"FIX19 event-block for year {_fix19_target}: "
                        f"{len(_fix19_block)} chunks (title-anchored, chronological)"
                    )
                else:
                    logger.info(
                        f"FIX19 no workover title for {_fix19_target} "
                        f"— fallback to existing logic"
                    )

            for d in sorted_results:
                src = d.metadata.get('filename', 'Document')
                import re as _re3
                _content = d.page_content
                _content = _re3.sub(
                    r'(Mail address|Immeuble Monia|Les Berges|Tél :|Fax :|MF :|RC :|email :)[^\n]*\n?',
                    '', _content, flags=_re3.IGNORECASE
                )
                _content = _re3.sub(r'\n{3,}', '\n', _content)
                _cleaned = ' '.join(_content.split())[:CHUNK_CONTENT_CHARS]
                doc_context += f"\n--- Source: {src} ---\n"
                doc_context += _cleaned + "\n---\n"

        HIGHLIGHT_PATTERNS = [
            (r'N\.B[:\s]+(.{20,200})', 'KEY FINDING'),
            (r'Rejected\s+\d+\s+tubing.{0,150}', 'CAUSE OF FAILURE'),
            (r'Lost thickness.{0,150}', 'ROOT CAUSE'),
            (r'absence of exploitable hydrocarbons.{0,200}', 'ABANDONMENT REASON'),
            (r'circulation loss.{0,150}', 'DRILLING ISSUE'),
        ]
        highlights = []
        well_docs_for_highlight = [d for d in doc_results
                                   if d.metadata.get('filename') == f"DGH_EZZ{detected_well_num}.pdf"] if detected_well_num else doc_results
        for d in well_docs_for_highlight:
            for pattern, label in HIGHLIGHT_PATTERNS:
                matches = re.findall(pattern, d.page_content, re.IGNORECASE | re.DOTALL)
                for match in matches:
                    clean = match.strip().replace('\n', ' ')[:200]
                    if clean not in highlights:
                        highlights.append(f"⚠️ {label}: {clean}")

        if highlights:
            highlight_text = "\n".join(highlights)
            doc_context = f"=== KEY EXTRACTED FINDINGS ===\n{highlight_text}\n=== END KEY FINDINGS ===\n\n" + doc_context
            logger.info(f"Highlighted {len(highlights)} key findings")

        if (doc_id or doc_ids) and not is_field_wide_doc:
            sql_context = ""
            use_sql = False
            needs_comments = False
            logger.info("File attached — SQL and DimDate disabled, answering from attached file only")
        else:
            sql_context = get_sql_context(question) if use_sql else ""
        logger.info(f"SQL CONTEXT ({len(sql_context)} chars): {sql_context[:400] if sql_context else 'EMPTY'}")

        comments_rows = []
        comments_context = ""
        search_words = []
        if needs_comments:
            well_ref_c = normalize_well_code(question)
            well_code_str = well_ref_c.well_code if well_ref_c else None

            stop_words = {
                'the', 'le', 'la', 'les', 'de', 'du', 'des', 'un', 'une',
                'a', 'an', 'in', 'on', 'at', 'for', 'of', 'with', 'and',
                'que', 'qui', 'quoi', 'quel', 'quelle', 'pendant', 'durant',
                'during', 'when', 'give', 'me', 'show', 'tell', 'what',
                'period', 'periode', 'well', 'puits', 'was', 'is', 'were',
                'production', 'ezz', 'which', 'i', 'my', 'how', 'long',
                'depuis', 'quand', 'get', 'did', 'the',
            }
            words = re.findall(r'\b\w{3,}\b', question.lower())
            search_words = [w for w in words if w not in stop_words]
            logger.info(f"Comment search_words: {search_words}")

            if well_code_str and search_words:
                keyword_to_dates = {}
                all_rows_map = {}
                for word in search_words:
                    rows = search_date_comments(keyword=word, well_code=well_code_str)
                    if rows:
                        keyword_to_dates[word] = {r['date'] for r in rows}
                        for r in rows:
                            all_rows_map[r['date']] = r

                logger.info(f"Keywords matched: {list(keyword_to_dates.keys())}")

                if keyword_to_dates:
                    date_scores = {}
                    for word, dates in keyword_to_dates.items():
                        for d in dates:
                            date_scores[d] = date_scores.get(d, 0) + 1
                    max_score = max(date_scores.values())
                    threshold = 2 if max_score >= 2 else 1
                    logger.info(f"max_score={max_score} threshold={threshold}")
                    filtered_dates = {d for d, score in date_scores.items() if score >= threshold}
                    comments_rows = sorted(
                        [r for d, r in all_rows_map.items() if d in filtered_dates],
                        key=lambda x: x['date']
                    )

            elif well_code_str:
                comments_rows = search_date_comments(well_code=well_code_str)

            if len(comments_rows) > 8 and len(search_words) >= 2:
                refined = search_date_comments_multi(
                    keywords=search_words[:3], well_code=well_code_str)
                if refined:
                    comments_rows = refined
                    logger.info(f"Refined with AND logic: {len(comments_rows)} rows")

            if search_words and comments_rows:
                well_num_filter = re.search(r'\d+', well_code_str).group() if well_code_str else None

                def row_is_relevant(r):
                    text = r['comments']
                    text_lower = text.lower()
                    if not well_num_filter:
                        return sum(1 for w in search_words if w in text_lower) >= 2
                    parts = re.split(r';\*\s*|\.\*\s*|;\s*\*\s*', text)
                    relevant_score = 0
                    for part in parts:
                        part_lower = part.lower()
                        well_nums_in_part = re.findall(r'EZZ\s*#?\s*(\d+)(?!\d)', part, re.IGNORECASE)
                        is_our_well = well_num_filter in [m for m in well_nums_in_part if m == well_num_filter]
                        if is_our_well:
                            kw_in_part = sum(1 for w in search_words if w in part_lower)
                            relevant_score += kw_in_part
                    return relevant_score >= 2

                filtered = [r for r in comments_rows if row_is_relevant(r)]
                if filtered:
                    comments_rows = filtered
                    logger.info(f"Post-filtered: {len(comments_rows)} rows")

            if 'workover' in q_lower and comments_rows:
                WO_TERMS = ['rig', 'work over', 'workover', 'w.o', 'wo ',
                            'pooh', 'rih', 'completion', 'packer', 'ulysse', 'ctf']
                comments_rows = [
                    r for r in comments_rows
                    if any(term in r['comments'].lower() for term in WO_TERMS)
                ]
                logger.info(f"Workover filter applied: {len(comments_rows)} rows remaining")

            logger.info(
                f"DimDate comments found: {len(comments_rows)} rows "
                f"for well={well_code_str}, words={search_words}"
            )

            if comments_rows:
                comments_context += "\n=== FIELD OPERATOR COMMENTS ===\n"
                for row in comments_rows:
                    comments_context += f"  {row['date']} : {row['comments']}\n"
                comments_context += "=== END COMMENTS ===\n"
                logger.info(f"DimDate comments injected: {len(comments_rows)} rows")

        if is_field_wide_doc:
            ALL_WELL_NUMS = ['1', '2', '3', '4', '5', '6', '7', '8',
                             '9', '10', '11', '12', '14', '15', '16', '17', '18']

            topic_keywords = question.lower()
            if 'tubing integrity' in topic_keywords or 'tubing' in topic_keywords:
                specific_query_suffix = "tubing integrity failure rejected workover completion packer leak corroded shut closed fish lost disposal abandoned plugged"
            elif 'workover' in topic_keywords:
                specific_query_suffix = "workover intervention rig completion POOH RIH sequences events"
            elif 'production' in topic_keywords or 'bopd' in topic_keywords:
                specific_query_suffix = "production BOPD oil rate shut-in average daily"
            elif 'casing' in topic_keywords:
                specific_query_suffix = "casing integrity test leak failure corrosion"
            elif 'completion' in topic_keywords:
                specific_query_suffix = "completion design packer tubing hanger jet pump sucker rod"
            else:
                specific_query_suffix = question

            per_well_context = "FIELD-WIDE RAG CONTEXT:\n" + "=" * 50 + "\n"
            per_well_context += f"Topic: {question}\n" + "=" * 50 + "\n"

            INTEGRITY_TERMS = [
                'tubing', 'integrity', 'rejected', 'workover', 'completion',
                'packer', 'leak', 'failure', 'closed', 'shut', 'corroded',
                'disposal', 'abandoned', 'plugged', 'fish', 'lost', 'casing',
                'standing valve', 'sucker rod', 'jet pump', 'intervention'
            ]

            for wnum in ALL_WELL_NUMS:
                well_query = f"EZZAOUIA#{wnum} EZZ{wnum} EZZ-{wnum} EZZ #{wnum} {specific_query_suffix}"

                results = retrieve_smart(query=well_query, k=15, well_num=wnum)

                per_well_context += f"\n=== WELL EZZ-{wnum.zfill(2)} START ===\n"

                if results:
                    import re as _re
                    well_pattern = _re.compile(
                        rf'(?:EZZAOUIA|EZZ)\s*#?\s*0*{_re.escape(wnum)}\b(?!\d)',
                        _re.IGNORECASE
                    )

                    SKIP_TERMS = [
                        'mail address', 'immeuble monia', 'tél :', 'fax :',
                        '--- page', 'les berges du lac', 'rc : b116521996',
                        'mf : 0437877x', 'contact@maretap'
                    ]

                    filtered = [
                        r for r in results
                        if not any(skip in r.page_content.lower() for skip in SKIP_TERMS)
                    ]

                    def score_chunk(r):
                        content = r.page_content.lower()
                        score = 0
                        if any(t in content for t in INTEGRITY_TERMS):
                            score += 10
                        if well_pattern.search(r.page_content):
                            score += 5
                        return score

                    filtered_scored = sorted(filtered, key=score_chunk, reverse=True)

                    top_chunks = (filtered_scored[:FIELD_WIDE_CHUNKS_PER_WELL]
                                  if filtered_scored else results[:2])

                    for r in top_chunks:
                        per_well_context += (
                            f"[EZZ-{wnum.zfill(2)} DATA] "
                            + r.page_content[:FIELD_WIDE_CHARS_PER_CHUNK]
                            + "\n---\n"
                        )
                    per_well_context += f"=== WELL EZZ-{wnum.zfill(2)} END ===\n"
                else:
                    per_well_context += f"  No document chunks found.\n=== WELL EZZ-{wnum.zfill(2)} END ===\n"

            doc_context = per_well_context
            logger.info(f"Field-wide RAG done: {len(ALL_WELL_NUMS)} wells processed")

        sql_has_data = bool(sql_context and len(sql_context.strip()) > 50)
        production_keywords = [
            'top', 'meilleur', 'classement', 'performer', 'production', 'bopd',
            'stb', 'total', 'puits', 'well', 'barils', 'huile', 'oil', 'resume',
            'résumé', 'bilan', 'global', 'champ', 'field', 'kpi', 'performance',
            'wct', 'bsw', 'gor', 'water cut', 'reservoir', 'réservoir',
            'analyse', 'analysis', 'analyser', 'overview',
        ]
        has_production_question = any(w in q_lower for w in production_keywords)
        if not use_docs:
            doc_context = ""
            logger.info("Documents excluded by user request")
        elif sql_has_data and has_production_question and not needs_comments and not is_doc_priority and len(sql_context.strip()) > 200 and not doc_id and not doc_ids and task != 'well_analysis':
            doc_context = ""
            logger.info("SQL data authoritative — documents excluded")

        # FIX: suppress failed/error answers from being injected as prior context.
        # A prior traceback or "Not specified" answer confuses the LLM and causes
        # it to output template placeholders instead of real data.
        history_text = ""
        if history and len(history) > 0:
            last = history[-1]
            last_q = last.get('question', '').lower()
            current_q = question.lower()
            last_answer = last.get('answer', '')

            # Only inject if the wells match AND the prior answer is not a failure
            well_in_last = re.search(r'ezz\s*#?\s*(\d+)', last_q)
            well_in_current = re.search(r'ezz\s*#?\s*(\d+)', current_q)
            if (
                well_in_last and well_in_current
                and well_in_last.group(1) == well_in_current.group(1)
                and not _is_failed_answer(last_answer)
            ):
                history_text = (
                    f"\n=== PREVIOUS EXCHANGE ===\n"
                    f"Q: {last['question']}\n"
                    f"A: {last_answer[:200]}...\n"
                )

        from .memory import get_user_memory, update_user_memory
        memory_context = get_user_memory(user) if user else ""

        available_docs = get_available_documents()
        docs_list = "\n".join(f"  - {d}" for d in available_docs) if available_docs else "  No documents indexed"

        top_n_match = re.search(r'\btop\s+(\d+)\b', question, re.IGNORECASE)
        top_n = int(top_n_match.group(1)) if top_n_match else None
        top_n_rule = (
            f"\nCRITICAL: The question asks for exactly TOP {top_n} — you MUST list "
            f"exactly {top_n} items, no more, no less."
            if top_n else ""
        )

        source_line = f"*Source: EZZAOUIA DWH — {today_str} — historical data 1994–2025*"

        if lang == 'ar':
            lang_instruction = (
                "CRITICAL: The user wrote in Arabic. "
                "You MUST respond entirely in Arabic. "
                "Use Arabic month names and Arabic numerals where appropriate. "
                "Never switch to French or English."
            )
        elif lang == 'en':
            lang_instruction = (
                "CRITICAL: The user wrote in English. "
                "You MUST respond entirely in English. "
                "Never switch to French or Arabic."
            )
        else:
            lang_instruction = (
                "CRITICAL: L'utilisateur a écrit en français. "
                "Vous DEVEZ répondre entièrement en français. "
                "Ne jamais basculer vers l'anglais ou l'arabe."
            )

        MAX_DOC_CONTEXT_CHARS = (
            MAX_DOC_CONTEXT_CHARS_FIELD if is_field_wide_doc
            else MAX_DOC_CONTEXT_CHARS_NORMAL
        )
        doc_context_len_before = len(doc_context)
        if len(doc_context) > MAX_DOC_CONTEXT_CHARS:
            doc_context = doc_context[:MAX_DOC_CONTEXT_CHARS] + "\n[... context truncated for length ...]"
            logger.warning(
                f"Doc context truncated: {doc_context_len_before} -> "
                f"{MAX_DOC_CONTEXT_CHARS} chars. Some retrieved content was "
                f"dropped — answer may be partial."
            )

        sql_context_len_before = len(sql_context)
        if len(sql_context) > MAX_SQL_CONTEXT_CHARS:
            sql_context = sql_context[:MAX_SQL_CONTEXT_CHARS] + "\n[... sql context truncated ...]"
            logger.warning(
                f"SQL context truncated: {sql_context_len_before} -> "
                f"{MAX_SQL_CONTEXT_CHARS} chars."
            )

        logger.info(
            f"FINAL CONTEXT IN PROMPT — DOC: {len(doc_context)} chars "
            f"(before trunc: {doc_context_len_before}), "
            f"SQL: {len(sql_context)} chars "
            f"(before trunc: {sql_context_len_before}), "
            f"COMMENTS: {len(comments_context)} chars"
        )

        well_confusion_rule = _build_well_confusion_rule(well_ref)

        task_prompts = {
            'well_analysis': PROMPT_WELL_ANALYSIS,
            'production_kpis': PROMPT_PRODUCTION_KPIS,
            'document_qa': PROMPT_DOCUMENT_QA.format(well_confusion_rule=well_confusion_rule),
            'operational_history': PROMPT_OPERATIONAL_HISTORY,
            'field_summary': PROMPT_FIELD_SUMMARY,
        }
        selected_prompt = task_prompts.get(task, PROMPT_DOCUMENT_QA.format(well_confusion_rule=well_confusion_rule))

        if well_ref:
            selected_prompt = selected_prompt.replace('{well_code}', well_ref.well_code)

        prompt = f"""{lang_instruction}

{selected_prompt}

════════════════════════════════════════════════════
DATE: {today_str} | LANGUAGE: {langue_nom}
{top_n_rule}
════════════════════════════════════════════════════

=== OPERATOR COMMENTS ===
{comments_context if comments_context else "None."}

=== SQL DATABASE ===
{sql_context if sql_context else "None."}

=== DOCUMENT CONTEXT ===
{doc_context if doc_context else "No documents attached."}
=== END DOCUMENT CONTEXT ===

{history_text}

QUESTION: {question}
ANSWER:"""

        if comments_rows:
            structured = _build_structured_comments_answer(
                question, comments_rows, lang, today_str,
                search_words=search_words if needs_comments else None
            )
            if structured:
                well = normalize_well_code(question)
                if user:
                    update_user_memory(user, question, structured, well=well)
                return {
                    'answer': structured,
                    'chart_data': None,
                    'suggestions': generate_suggestions(question, well=well, lang=lang),
                }

        logger.info(f"PROMPT TOTAL LENGTH: {len(prompt)} chars")
        logger.info(f"PROMPT FIRST 500: {prompt[:500]}")
        logger.info(f"DOC CONTEXT SAMPLE: {doc_context[:300]}")
        logger.info(f"PROMPT LAST 500: {prompt[-500:]}")
        try:
            response = get_llm().invoke(prompt)
            answer = response.strip()
        except Exception as llm_error:
            logger.error(f"LLM invoke error: {llm_error}")
            if 'context' in str(llm_error).lower() or len(prompt) > 45000:
                logger.warning(
                    "Prompt too large — retrying with REDUCED context. "
                    "The answer for this question will be PARTIAL."
                )
                doc_context_short = (
                    doc_context[:RETRY_DOC_CONTEXT_CHARS]
                    + "\n[... context reduced due to size — answer may be incomplete ...]"
                )
                prompt_short = prompt.replace(doc_context, doc_context_short)
                response = get_llm().invoke(prompt_short)
                answer = response.strip()
            else:
                raise
        if lang == 'en':
            answer = _force_english_month_names(answer)
        answer = _sanitize_answer_language(answer, lang)
        logger.info(f"Response generated: {len(answer)} chars")

        if answer and len(answer) > 50:
            last_char = answer.rstrip()[-1]
            if last_char not in '.!?:|)】»"\'`' and not answer.rstrip().endswith('---'):
                logger.warning(
                    f"Answer may be TRUNCATED — ends with '{last_char}' "
                    f"(no sentence terminator). Length: {len(answer)} chars."
                )

        well = normalize_well_code(question)
        chart_data = build_chart_data(question) if detect_chart_request(question) else None
        suggestions = generate_suggestions(question, well=well, lang=lang)

        if user:
            try:
                update_user_memory(user, question, answer, well=well)
            except Exception as mem_err:
                logger.warning(f"Memory update skipped — DB connection: {mem_err}")

        return {'answer': answer, 'chart_data': chart_data, 'suggestions': suggestions}

    except Exception as e:
        logger.error(f"ask() error: {e}")
        return {
            'answer': f"Technical error: {str(e)}",
            'chart_data': None,
            'suggestions': [],
        }