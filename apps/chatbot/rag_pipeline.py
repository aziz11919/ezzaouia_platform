import logging
import re
import hashlib
import datetime
import calendar
from django.conf import settings
from langchain_ollama import OllamaLLM
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

logger = logging.getLogger('apps')

TODAY = datetime.date.today().strftime('%d/%m/%Y')

PROMPT_WELL_ANALYSIS = """You are Dr. EZZAOUIA, Senior Petroleum Engineer at MARETAP S.A.
Your task: Write a complete well analysis combining SQL production data AND document history.

STRUCTURE YOUR ANSWER EXACTLY LIKE THIS:

## 🔬 Well {well_code} — Technical Analysis

### Production Performance (from SQL)
Extract ALL numbers from SQL DATABASE section: BOPD, cumulative oil, BSW, GOR, peak BOPD.
Present them in a clean table. If a value is 0 or unavailable say so.

### Operational History (from Documents)
Extract key events from DOCUMENT CONTEXT: workovers, interventions, completions, failures, dates.
List them chronologically. Quote the source document.

### Assessment
2-3 sentences summarizing well health based on the data above.

RULES:
- Use ONLY numbers from SQL DATABASE section
- Use ONLY events from DOCUMENT CONTEXT section
- NEVER invent data
- If SQL is empty say "No production data available"
- If documents are empty say "No document history available"
"""

PROMPT_PRODUCTION_KPIS = """You are Dr. EZZAOUIA, Senior Petroleum Engineer at MARETAP S.A.
Your task: Answer production KPI questions using ONLY the SQL data provided.

RULES:
- Use ONLY numbers from SQL DATABASE section — copy them exactly as-is
- NEVER invent well names, BOPD values, or rankings not present in the SQL section
- Present rankings in EXACT order as they appear in the SQL DATABASE section
- Do NOT reorder or modify the ranking
- Present data in markdown tables
- Flag BSW > 80% as 🔴 CRITICAL
- Flag GOR = 0 as DATA UNAVAILABLE
- Respond in same language as the question
"""

PROMPT_DOCUMENT_QA = """You are Dr. EZZAOUIA, Senior Petroleum Engineer at MARETAP S.A.
Your task: Answer questions by extracting information from the provided documents.

RULES:
- Answer ONLY from DOCUMENT CONTEXT section — ignore SQL DATABASE section entirely
- Extract facts directly: dates, causes, actions, results
- Write 3-6 sentences maximum
- Always cite which document the answer comes from
- If you find ANY relevant information in the context, USE IT to answer — even partial information is valuable
- Only say "The indexed documents do not contain specific information about this query." if the context has ZERO relevant content
- NEVER say "no clear cause" if a cause IS mentioned in the context — extract it directly
- When a chunk starts with a well code like "EZZ#9:", the content that follows is ABOUT that well — extract it directly
- "as EZZ#1" means "similar to EZZ#1", not "this is about EZZ#1"
- NEVER add information not present in the documents
"""

PROMPT_OPERATIONAL_HISTORY = """You are Dr. EZZAOUIA, Senior Petroleum Engineer at MARETAP S.A.
Your task: Answer questions about field operations, workovers, interventions using operator logs.

RULES:
- Use ONLY data from OPERATOR COMMENTS section
- Present events chronologically with dates
- If no comments found say:
  "No operator log entries found for this activity in the database."
- NEVER invent dates or events
"""

PROMPT_FIELD_SUMMARY = """You are Dr. EZZAOUIA, Senior Petroleum Engineer at MARETAP S.A.
Your task: Provide a field-level summary using SQL KPI data.

STRUCTURE:
## 📊 EZZAOUIA Field — Summary

### Key Performance Indicators
Present all available KPIs in a table: BOPD, BSW, GOR, cumulative oil, active wells.

### Critical Alerts
List any wells with BSW > 80% or other critical issues.

### Recommendations
2-3 field-level engineering recommendations.

RULES:
- Use ONLY numbers from SQL DATABASE section
- NEVER invent field statistics
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
            # ✅ FIX 1: Increased from 3000 to 8192.
            # With 3000 the prompt was silently truncated — Ollama never
            # saw the retrieved document chunks, causing hallucinations.
            num_ctx=8192,
            num_predict=1200,
            top_p=0.85,
            repeat_penalty=1.15,
            timeout=180,
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


def index_document(text, metadata=None, doc_id=None):
    if not text or not text.strip():
        return 0
    metadata = metadata or {}
    if doc_id:
        metadata['doc_id'] = str(doc_id)

    import re as _re

    try:
        splitter = RecursiveCharacterTextSplitter(
    chunk_size=1200,
    chunk_overlap=500,
    separators=["\n\n", "\n", ".", " "],
)
        chunks = splitter.split_text(text)
        docs = []
        for i, chunk in enumerate(chunks):
            chunk_meta = {
                **metadata,
                'chunk_index': i,
                'chunk_total': len(chunks)
            }
            well_match = _re.search(
                r'(?:EZZ|EZZAOUIA)\s*#?\s*(\d{1,2})\b(?!\d)', chunk, _re.IGNORECASE)
            if not well_match:
                well_match = _re.search(
                    r'(?:EZZ|EZZAOUIA)\s*[-#]?\s*0*(\d{1,2})\b', chunk, _re.IGNORECASE)
            if well_match:
                chunk_meta['well_num'] = well_match.group(1)
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


def retrieve_smart(query, doc_id=None, filename=None, k=6, well_num=None):
    try:
        results = []

        if doc_id:
            vs = get_vectorstore_for_doc(doc_id)
            # When a specific file is attached, return ALL its chunks
            # so no relevant chunk is missed due to semantic ranking
            try:
                col = vs._collection
                all_chunks = col.get(include=['documents', 'metadatas'])
                if all_chunks and all_chunks.get('documents'):
                    from langchain.schema import Document as LCDoc
                    all_docs = [
                        LCDoc(page_content=doc, metadata=meta)
                        for doc, meta in zip(all_chunks['documents'], all_chunks['metadatas'])
                    ]
                    logger.info(f"File attached — returning ALL {len(all_docs)} chunks")
                    return all_docs
            except Exception as e:
                logger.warning(f"Full file retrieval error: {e}")
            # Fallback to MMR
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

        # Boost well-specific chunks to the top when a well number is specified
        if well_num:
            well_results = []
            dgh_results = []
            other_results = []
            # Try to find the specific DGH split file for this well
            if well_num:
                DGH_FILENAME = f"DGH_EZZ{well_num}.pdf"
            else:
                DGH_FILENAME = "DGH_INTRO.pdf"
            for r in main_results:
                chunk_well = r.metadata.get('well_num', '')
                chunk_file = r.metadata.get('filename', '')
                if chunk_well == well_num:
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
                existing_keys = {r.page_content[:80] for r in dgh_results}
                from langchain.schema import Document as LCDoc
                import re as _re
                well_pattern = _re.compile(
                    rf'(?:EZZAOUIA|EZZ)\s*#?\s*0*{well_num}\b', _re.IGNORECASE)
                for doc, meta in zip(all_dgh['documents'], all_dgh['metadatas']):
                    if doc[:80] in existing_keys:
                        continue
                    if well_pattern.search(doc):
                        dgh_results.append(LCDoc(page_content=doc, metadata=meta))
                        existing_keys.add(doc[:80])
                dgh_extra = None  # skip the old query block
                logger.info(f"DGH keyword fetch: {len(dgh_results)} total DGH chunks")
            except Exception as e:
                logger.warning(f"DGH extra fetch error: {e}")

            # For small single-page files, include ALL chunks (not just top matches)
            if len(dgh_results) < 10:
                try:
                    all_dgh = col.get(
                        where={"filename": DGH_FILENAME},
                        include=['documents', 'metadatas']
                    )
                    existing_keys = {r.page_content[:80] for r in dgh_results}
                    for doc, meta in zip(all_dgh['documents'], all_dgh['metadatas']):
                        if doc[:80] not in existing_keys:
                            dgh_results.append(LCDoc(page_content=doc, metadata=meta))
                            existing_keys.add(doc[:80])
                    logger.info(f"Small file — all {len(dgh_results)} DGH chunks included")
                except Exception as e:
                    logger.warning(f"Small file fetch error: {e}")

            # Keyword fallback — search for exact technical terms when semantic fails
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
                    existing_keys = {r.page_content[:80] for r in dgh_results}
                    for doc, meta in zip(all_well_chunks['documents'], all_well_chunks['metadatas']):
                        doc_lower = doc.lower()
                        if any(kw in doc_lower for kw in TECHNICAL_KEYWORDS):
                            if doc[:80] not in existing_keys:
                                dgh_results.append(LCDoc(page_content=doc, metadata=meta))
                                existing_keys.add(doc[:80])
                    logger.info(f"Keyword fallback added chunks, total DGH: {len(dgh_results)}")
                except Exception as e:
                    logger.warning(f"Keyword fallback error: {e}")

            main_results = well_results + dgh_results + other_results

            # Sort chunks: prioritize by year mentioned in query, then by keywords
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
                    content = r.page_content.lower()
                    if target_year and target_year in r.page_content:
                        score += 10
                    if any(kw in content for kw in PRIORITY_KEYWORDS):
                        score += 5
                    return score

                main_results = sorted(main_results, key=chunk_score, reverse=True)
                logger.info(f"Chunks re-sorted by year={target_year} and keywords")

            logger.info(
                f"Well {well_num} filtering: {len(well_results)} tagged, "
                f"{len(dgh_results)} DGH, {len(other_results)} others"
            )

        # Try to find the specific DGH split file for this well
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
                        key = r.page_content[:100]
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
                    params.append(f"%EZZ#{n}")
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
                    params.append(f"%EZZ#{n}")
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

    if any(w in q for w in ['production', 'total', 'champ', 'bopd', 'huile',
                             'résumé', 'resume', 'situation', 'global',
                             'bilan', 'analyse', 'performance', 'kpi',
                             'field', 'summary', 'overview']):
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
            bsw_flag = " ⚠️ CRITICAL HIGH BSW" if float(w.get('avg_bsw', 0) or 0) > 80 else ""
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
        'tendance', 'historique', 'evolution',
        '\u0627\u062a\u062c\u0627\u0647', '\u062a\u0637\u0648\u0631', '\u0634\u0647\u0631\u064a',
    ]
    metric_words = ['bopd', 'production', 'huile', 'oil', '\u0627\u0646\u062a\u0627\u062c']
    has_trend_word = any(w in q for w in trend_words)
    has_metric_word = any(w in q for w in metric_words)
    return has_well and has_year and has_trend_word and has_metric_word


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
    total_days = sum(calendar.monthrange(int(r.get('year', year)), int(r.get('month', 1)))[1] for r in rows)
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


def _detect_task(question, doc_id, doc_ids, needs_comments, well):
    """Detect question type and return the appropriate prompt key."""
    q = question.lower()

    # TCM/meeting/report questions → always document_qa
    if any(w in q for w in [
        'tcm', 'ocm', 'meeting', 'réunion', 'decisions', 'discussed',
        'reported', 'minutes', 'mom', 'agenda', 'presentation',
        'budget', 'forecast', 'hse', 'report'
    ]):
        return 'document_qa'

    # Explicit overrides take priority over all other routing
    if 'from docs' in q or 'from documents' in q or doc_id or doc_ids:
        return 'document_qa'

    if 'from db' in q or 'from database' in q:
        return 'production_kpis'

    has_well = well is not None
    has_file = False  # already handled above

    # Operational history — DimDate comments
    if needs_comments:
        return 'operational_history'

    # Well analysis — combines SQL + docs
    if has_well and any(w in q for w in [
        'analyse', 'analysis', 'analyser', 'tell me about',
        'give me', 'overview', 'deep dive', 'about ezz',
        'from both', 'combine'
    ]):
        return 'well_analysis'

    # Document Q&A — explicit keyword
    if 'from docs' in q or 'from documents' in q:
        return 'document_qa'

    # Field summary
    if any(w in q for w in [
        'field', 'champ', 'global', 'summary', 'résumé',
        'bilan', 'all wells', 'tous les puits', 'overview'
    ]) and not has_well:
        return 'field_summary'

    # Well-specific investigative questions → document_qa
    if has_well and any(w in q for w in [
        'caused', 'why', 'what happened', 'failure', 'failed',
        'history', 'when did', 'how did', 'what was', 'describe',
        'explain', 'detail', 'event', 'issue', 'problem'
    ]):
        return 'document_qa'

    # Production KPIs — default for well questions with SQL
    if has_well or any(w in q for w in [
        'bopd', 'bsw', 'gor', 'production', 'top', 'ranking',
        'meilleur', 'classement', 'trend', 'monthly'
    ]):
        return 'production_kpis'

    # Default — document Q&A
    return 'document_qa'


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
            search_query += f" {well_match.group(1)} workover intervention completion tubing failure rejected joints sucker rod wear"

        COMMENT_TRIGGER_KEYWORDS_EARLY = [
            'comment', 'remarque', 'note', 'period', 'période', 'during',
            'pendant', 'quand', 'when', 'monitoring', 'surveillance',
            'consulting', 'intervention', 'activit', 'operat', 'travaux',
            'srp', 'workover', 'shut-in', 'shut in', 'fermeture', 'reprise',
            'depuis', 'depuis quand', 'how long', 'combien de temps',
        ]
        # "from docs" explicitly disables DimDate comments
        use_comments = not (use_sql == False)  # use_sql is False when "from docs" is set
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

        # ✅ FIX 2: Reduced k for doc-priority questions from 20 to 8.
        # Fewer, more targeted chunks fit better within the 8192 context window
        # and reduce noise that confuses the LLM.
        if is_doc_priority:
            retrieval_k = 8
        elif is_doc_only_question:
            retrieval_k = 10
        else:
            retrieval_k = 6

        logger.info(f"Retrieval k={retrieval_k} ({'doc-priority' if is_doc_priority else 'doc/comments' if is_doc_only_question else 'production'})")

        # Extract well number for targeted retrieval
        detected_well_num = None
        # Don't boost DGH for TCM/meeting/report questions
        TCM_KEYWORDS = ['tcm', 'ocm', 'meeting', 'mom', 'minutes', 'decisions',
                        'discussed', 'reported', 'budget', 'forecast', 'hse']
        is_tcm_question = any(kw in q_lower for kw in TCM_KEYWORDS)

        if well_match and not is_tcm_question:
            num = re.search(r'\d+', well_match.group(1))
            if num:
                detected_well_num = num.group()

        doc_results = retrieve_smart(
            query=search_query, doc_id=doc_id, filename=filename,
            k=retrieval_k, well_num=detected_well_num
        )
        logger.info(f"DOC RESULTS: {len(doc_results)} chunks")

        # Detect task type early so later logic (SQL exclusion, prompt) can use it
        well_ref = normalize_well_code(question)
        task = _detect_task(question, doc_id, doc_ids, needs_comments, well_ref)
        logger.info(f"Task detected: {task}")

        for i, r in enumerate(doc_results[:5]):
            logger.info(f"  Chunk {i+1}: [{r.metadata.get('filename','?')}] {r.page_content[:150]}")

        if doc_id and doc_results:
            combined = " ".join(d.page_content for d in doc_results[:3])
            if not is_petroleum_document(combined):
                return {
                    'answer': 'Ce document ne semble pas lié au secteur pétrolier ou à MARETAP. Veuillez joindre un document technique pétrolier (rapport de production, étude réservoir, rapport workover, etc.).',
                    'chart_data': None,
                    'suggestions': [],
                }

        doc_context = ""
        if doc_results:
            # Sort chunks: prioritize those matching year/keywords from question
            import re as _re
            year_in_q = _re.search(r'\b(20\d{2}|19\d{2})\b', question)
            target_year = year_in_q.group(1) if year_in_q else None

            PRIORITY_TERMS = [
                'rejected', 'lost thickness', 'sucker rod', 'wash out',
                'failure', 'integrity', 'abandoned', 'plug', 'hydrocarbons',
                'circulation loss', 'cause', 'reason', 'problem', 'issue',
                'workover', 'sequences of events', 'rig accepted', 'pooh',
                'completion', 'packer', 'tubing hanger', 'july', 'april', 'october'
            ]

            def doc_chunk_score(d):
                score = 0
                content = d.page_content.lower()
                if target_year and target_year in d.page_content:
                    score += 10
                if any(t in content for t in PRIORITY_TERMS):
                    score += 5
                return score

            sorted_results = sorted(doc_results, key=doc_chunk_score, reverse=True)

            sources = {}
            for d in sorted_results:
                src = d.metadata.get('filename', 'Document')
                sources.setdefault(src, []).append(d.page_content[:600])

            for src, chunks in sources.items():
                doc_context += f"\n--- Source: {src} ---\n"
                for chunk in chunks:
                    doc_context += chunk + "\n---\n"

        # If a specific technical finding is found in chunks, highlight it explicitly
        HIGHLIGHT_PATTERNS = [
            (r'N\.B[:\s]+(.{20,200})', 'KEY FINDING'),
            (r'Rejected\s+\d+\s+tubing.{0,150}', 'CAUSE OF FAILURE'),
            (r'Lost thickness.{0,150}', 'ROOT CAUSE'),
            (r'absence of exploitable hydrocarbons.{0,200}', 'ABANDONMENT REASON'),
            (r'circulation loss.{0,150}', 'DRILLING ISSUE'),
        ]
        highlights = []
        for d in doc_results:
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

        # If user attached a specific file, skip SQL and DimDate entirely
        if doc_id or doc_ids:
            sql_context = ""
            use_sql = False
            needs_comments = False
            logger.info("File attached — SQL and DimDate disabled, answering from attached file only")
        else:
            sql_context = get_sql_context(question) if use_sql else ""
        logger.info(f"SQL CONTEXT ({len(sql_context)} chars): {sql_context[:400] if sql_context else 'EMPTY'}")

        comments_rows = []
        comments_context = ""
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

        FIELD_WIDE_DOC_KEYWORDS = [
            'all wells', 'tous les puits', 'chaque puits', 'every well',
            'for each well', 'summary table', 'tableau', 'summarize',
            'résumé de tous', 'current status of all',
        ]
        is_field_wide_doc = any(kw in q_lower for kw in FIELD_WIDE_DOC_KEYWORDS)

        if is_field_wide_doc:
            ALL_WELL_NUMS = ['1', '2', '3', '4', '5', '6', '7', '8',
                             '9', '10', '11', '12', '14', '15', '16', '17', '18']
            per_well_context = "FIELD-WIDE RAG CONTEXT:\n" + "=" * 50 + "\n"
            for wnum in ALL_WELL_NUMS:
                well_query = f"EZZ{wnum} {question}"
                results = retrieve_smart(query=well_query, k=5, well_num=wnum)
                per_well_context += f"\n[EZZ-{wnum.zfill(2)}]\n"
                if results:
                    for r in results[:2]:
                        per_well_context += r.page_content[:300] + "\n"
                else:
                    per_well_context += "  No chunks found.\n"
            doc_context = per_well_context
            logger.info("Field-wide RAG: done")

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

        history_text = ""
        # Only include history if it's about the same well to avoid cross-contamination
        if history and len(history) > 0:
            last = history[-1]
            last_q = last.get('question', '').lower()
            current_q = question.lower()
            # Only include if same well is mentioned in both questions
            well_in_last = re.search(r'ezz\s*#?\s*(\d+)', last_q)
            well_in_current = re.search(r'ezz\s*#?\s*(\d+)', current_q)
            if well_in_last and well_in_current and well_in_last.group(1) == well_in_current.group(1):
                history_text = f"\n=== PREVIOUS EXCHANGE ===\nQ: {last['question']}\nA: {last['answer'][:200]}...\n"

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

        # ✅ FIX 3: Truncate doc_context to avoid exceeding num_ctx.
        # Keep the most relevant chunks (first 4000 chars) so the LLM
        # always sees real context rather than a truncated/empty prompt.
        MAX_DOC_CONTEXT_CHARS = 10000
        if len(doc_context) > MAX_DOC_CONTEXT_CHARS:
            doc_context = doc_context[:MAX_DOC_CONTEXT_CHARS] + "\n[... context truncated for length ...]"
            logger.info(f"Doc context truncated to {MAX_DOC_CONTEXT_CHARS} chars")

        MAX_SQL_CONTEXT_CHARS = 1000
        if len(sql_context) > MAX_SQL_CONTEXT_CHARS:
            sql_context = sql_context[:MAX_SQL_CONTEXT_CHARS] + "\n[... sql context truncated ...]"

        logger.info(f"FINAL CONTEXT IN PROMPT - DOC: {len(doc_context)} chars, SQL: {len(sql_context)} chars")

        # Select specialized prompt based on task detected earlier
        task_prompts = {
            'well_analysis': PROMPT_WELL_ANALYSIS,
            'production_kpis': PROMPT_PRODUCTION_KPIS,
            'document_qa': PROMPT_DOCUMENT_QA,
            'operational_history': PROMPT_OPERATIONAL_HISTORY,
            'field_summary': PROMPT_FIELD_SUMMARY,
        }
        selected_prompt = task_prompts.get(task, PROMPT_DOCUMENT_QA)

        # Replace well_code placeholder if present
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

        logger.info(f"PROMPT FIRST 500: {prompt[:500]}")
        logger.info(f"DOC CONTEXT SAMPLE: {doc_context[:300]}")
        logger.info(f"PROMPT LAST 500: {prompt[-500:]}")
        response = get_llm().invoke(prompt)
        answer = response.strip()
        if lang == 'en':
            answer = _force_english_month_names(answer)
        answer = _sanitize_answer_language(answer, lang)
        logger.info(f"Response generated: {len(answer)} chars")

        well = normalize_well_code(question)
        chart_data = build_chart_data(question) if detect_chart_request(question) else None
        suggestions = generate_suggestions(question, well=well, lang=lang)

        if user:
            update_user_memory(user, question, answer, well=well)

        return {'answer': answer, 'chart_data': chart_data, 'suggestions': suggestions}

    except Exception as e:
        logger.error(f"ask() error: {e}")
        return {
            'answer': f"Technical error: {str(e)}",
            'chart_data': None,
            'suggestions': [],
        }