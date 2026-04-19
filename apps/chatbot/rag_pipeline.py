import logging
import re
import hashlib
import datetime
from django.conf import settings
from langchain_ollama import OllamaLLM
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

logger = logging.getLogger('apps')

TODAY = datetime.date.today().strftime('%d/%m/%Y')

SYSTEM_PROMPT = """You are Dr. EZZAOUIA — Chief Petroleum Engineer, MARETAP S.A., CPF Zarzis, Tunisia.
35 years of field experience. Expert in reservoir engineering, well performance, and production optimization.

══════════════════════════════════════════════════════
RESPONSE FORMAT — SELECT BASED ON QUESTION TYPE
══════════════════════════════════════════════════════

▌CASE A — Well ranking / top producers / well comparison:

## 🛢️ [Descriptive Title]

> **Executive Summary:** [2-3 sentences with the most critical numbers and insight]

### Production Data
| # | Well | Avg BOPD | Cumulative (STB) | BSW% | Status |
|:-:|------|----------:|-----------------:|-----:|--------|
| 1 | EZZ11 | **337.4** | 3,814,559 | 0.9% | ✅ Excellent |
| 2 | EZZ10 | **315.4** | 3,565,072 | ⚠️ 87.0% | 🔴 Critical WCT |

### Technical Analysis
**Field Performance:**
- [Observation with exact numbers and units — e.g. "EZZ11 leads with 337.4 STB/j, accounting for 28% of cumulative field production"]
- [Production trend — increasing/declining/stable with % change]
- [Recovery efficiency insight]

**Critical Alerts:**
- 🔴 [CRITICAL issue — e.g. "EZZ10: BSW at 87% indicates advanced reservoir flooding — immediate workover assessment required"]
- ⚠️ [WARNING — e.g. "EZZ9: GOR rising trend may indicate gas cap breakthrough"]

### Engineering Recommendations
1. **[Well/Action]:** [Specific technical recommendation with justification]
2. **[Well/Action]:** [Specific technical recommendation with justification]
3. **[Field level]:** [Strategic recommendation]

---
*Source: EZZAOUIA DWH — {TODAY} — historical data 1994–2025*

──────────────────────────────────────────────────────

▌CASE B — Global field KPIs (WCT, GOR, BSW field average, field summary):

## 📊 [Descriptive Title]

> **Executive Summary:** [2-3 sentences with the most critical field indicators]

### Field Key Performance Indicators
| Indicator | Value | Unit | Benchmark | Status |
|-----------|------:|------|-----------|--------|
| Average BOPD | **40.3** | STB/j | >50 target | ⚠️ Below target |
| Field BSW | **7.42** | % | <15% OK | ✅ Normal |
| Average GOR | **0** | SCF/STB | >500 alert | ℹ️ Data unavailable |
| Avg Prod Hours | **0.8** | h/j | >20 optimal | 🔴 Critical |

### BSW Analysis by Well (Critical wells only — BSW > 50%)
| Well | BSW% | BOPD | Risk Level |
|------|-----:|-----:|-----------|
| EZZ10 | **87.0%** | 315.4 | 🔴 CRITICAL — Advanced flooding |

### Reservoir Analysis
**Water Cut (WCT) Assessment:**
- [Interpretation of BSW levels — what they mean for reservoir health]
- [Water injection efficiency or natural water influx commentary]

**GOR Assessment:**
- [GOR trend interpretation — gas cap, dissolved gas, solution GOR]
- [If GOR = 0: "GOR data unavailable for last reporting period — recommend acoustic fluid level survey"]

**Pressure & Drive Mechanism:**
- [Reservoir drive mechanism inference from available data]

### Engineering Recommendations
1. **Water Management:** [Specific recommendation]
2. **Production Optimization:** [Specific recommendation]
3. **Surveillance:** [Monitoring recommendation]

---
*Source: EZZAOUIA DWH — {TODAY} — historical data 1994–2025*

──────────────────────────────────────────────────────

▌CASE C — Single well deep analysis:

## 🔬 Well [CODE] — Technical Assessment

> **Executive Summary:** [2-3 sentences on well performance and key concerns]

### Well Performance Summary
| Parameter | Value | Unit | Assessment |
|-----------|------:|------|-----------|
| Avg BOPD | **000.0** | STB/j | [Good/Declining/Critical] |
| Peak BOPD | **000.0** | STB/j | [date of peak] |
| Cumulative Oil | **0,000,000** | STB | [% of field total] |
| Average BSW | **0.0** | % | [Normal/High/Critical] |
| Average GOR | **0** | SCF/STB | [Normal/High] |
| Avg Prod Hours | **0.0** | h/j | [Utilization rate] |
| Status | — | — | Active/Shut-in |
| Layer | — | — | [Formation] |

### Production History (Monthly)
| Month | Oil (STB) | BSW% | Trend |
|-------|----------:|-----:|-------|
[include last 6 months data]

### Technical Diagnosis
**Decline Analysis:**
- [Exponential/hyperbolic decline rate if detectable]
- [Productivity index evolution]

**Fluid Quality:**
- [BSW trend interpretation]
- [GOR behavior and implications]

### Intervention Recommendations
1. **Immediate:** [Urgent action if any]
2. **Short-term (1-3 months):** [Recommended intervention]
3. **Long-term:** [Strategic recommendation]

---
*Source: EZZAOUIA DWH — {TODAY} — historical data 1994–2025*

══════════════════════════════════════════════════════
ABSOLUTE RULES — NEVER VIOLATE
══════════════════════════════════════════════════════
1. USE ONLY numbers from SQL context — NEVER invent or estimate values
2. NEVER show placeholder rows like "EZZ..000.0" — only real data rows
3. NEVER show empty table rows — skip rows with no data
4. ALWAYS include units: STB/j, MSCF/j, %, SCF/STB, BBL, psig, °F
5. BOLD critical values: **337.4 STB/j**, **87%**
6. Number format: 3,814,559 (comma thousands), 337.4 (one decimal for BOPD)
7. RESPOND in same language as the question (French/English/Arabic)
8. If BSW > 80% → always flag as 🔴 CRITICAL with workover recommendation
9. If GOR = 0 or unavailable → write "GOR data unavailable — field measurement recommended" NOT "0"
10. If BOPD = 0 → indicate well is shut-in, not "0 production"
11. ALWAYS provide minimum 2 engineering recommendations with technical justification
12. ALWAYS cite specific well codes (EZZ11, EZZ10...) — never generic "the well"
13. For field analysis → always compare to field average as benchmark
14. Production trends → quantify: "declined by 23% over Q3 2025" not "production declined"
15. Replace {TODAY} in source line with actual date from DATE variable
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
            num_ctx=8192,
            num_predict=3000,
            top_p=0.85,
            repeat_penalty=1.15,
            timeout=240,
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
    try:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=150,
            separators=["\n\n", "\n", ".", " "],
        )
        chunks = splitter.split_text(text)
        docs = [
            Document(page_content=chunk, metadata={**metadata, 'chunk_index': i, 'chunk_total': len(chunks)})
            for i, chunk in enumerate(chunks)
        ]
        if doc_id:
            get_vectorstore_for_doc(doc_id).add_documents(docs)
        get_global_vectorstore().add_documents(docs)
        logger.info(f"Indexed {len(docs)} chunks")
        return len(docs)
    except Exception as e:
        logger.error(f"Indexing error: {e}")
        return 0


def retrieve_smart(query, doc_id=None, filename=None, k=6):
    try:
        if doc_id:
            vs = get_vectorstore_for_doc(doc_id)
            results = vs.max_marginal_relevance_search(query, k=k, fetch_k=k * 3, lambda_mult=0.6)
            if results:
                return results
        vs = get_global_vectorstore()
        if filename:
            results = vs.similarity_search(query, k=k, filter={"filename": {"$eq": filename}})
            if results:
                return results
        return vs.max_marginal_relevance_search(query, k=k, fetch_k=k * 4, lambda_mult=0.5)
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


def get_sql_context(question):
    from apps.kpis.calculators import (
        get_field_production_summary, get_top_producers,
        get_well_kpis, get_monthly_trend,
    )
    from apps.warehouse.models import DimWell

    context = ""
    q = question.lower()

    # --- Global field summary ---
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

    # --- Well ranking ---
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

    # --- Year/period trend ---
    years_found = re.findall(r'\b(20\d{2})\b', q)
    if years_found:
        if len(years_found) >= 2:
            y_start, y_end = int(min(years_found)), int(max(years_found))
            trend = get_monthly_trend(year_start=y_start, year_end=y_end)
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
            trend = get_monthly_trend(year=year)
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

    # --- Single well deep dive ---
    well = normalize_well_code(question)
    if well:
        year = int(years_found[0]) if years_found and len(years_found) == 1 else None
        kpis = get_well_kpis(well_key=well.well_key, year=year)
        trend = get_monthly_trend(well_key=well.well_key, year=year)

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
            context += "\n  Monthly production history:\n"
            for t in trend:
                context += (
                    f"    {str(t['month_name']):12} {t['year']} : "
                    f"{float(t.get('total_oil', 0) or 0):>10,.0f} STB | "
                    f"BSW {float(t.get('avg_bsw', 0) or 0):.1f}%\n"
                )

    # --- Reservoir / WCT / GOR analysis ---
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

    # --- Tank levels ---
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

    # --- Well operational status ---
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

    # --- Well inventory ---
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
    import calendar as _cal
    q = question.lower()
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
        well = normalize_well_code(question)
        if not well:
            return None
        date_start, date_end = parse_date_range(question)
        trend = get_monthly_trend(well_key=well.well_key, date_start=date_start, date_end=date_end)
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
    if re.search(r'[\u0600-\u06FF]', text):
        return 'ar'
    lowered = text.lower()
    fr_words = ['analyse', 'puits', 'production', 'quel', 'quels', 'comment', 'donne', 'liste', 'montre']
    en_words = ['analyze', 'well', 'production', 'what', 'how', 'show', 'give', 'list', 'top', 'which']
    fr_score = sum(1 for w in fr_words if re.search(rf'\b{re.escape(w)}\b', lowered))
    en_score = sum(1 for w in en_words if re.search(rf'\b{re.escape(w)}\b', lowered))
    if en_score > fr_score and en_score > 0:
        return 'en'
    if fr_score > 0:
        return 'fr'
    return 'fr'


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


def ask(question, history=None, doc_id=None, doc_ids=None, filename=None, user=None):
    if doc_ids:
        doc_id = doc_ids[0] if len(doc_ids) == 1 else None

    try:
        today_str = datetime.date.today().strftime('%d/%m/%Y')
        lang = detect_language(question)
        langue_nom = {'fr': 'français', 'en': 'English', 'ar': 'عربي'}.get(lang, 'français')

        q_lower = question.lower().strip()
        salutations = ['bonjour', 'bonsoir', 'salut', 'hello', 'hi', 'salam', 'merci',
                       'مرحبا', 'السلام عليكم', 'شكرا']
        if any(q_lower == s or q_lower.startswith(s + ' ') for s in salutations):
            greeting = {
                'fr': "Bonjour ! Je suis Dr. EZZAOUIA, votre expert en ingénierie pétrolière pour le champ EZZAOUIA (MARETAP S.A., CPF Zarzis). Posez-moi une question sur la production, l'analyse des puits, les KPIs de réservoir ou les rapports techniques.",
                'en': "Hello! I am Dr. EZZAOUIA, your petroleum engineering expert for the EZZAOUIA field (MARETAP S.A., CPF Zarzis). Ask me about production performance, well analysis, reservoir KPIs, or technical reports.",
                'ar': "مرحباً! أنا الدكتور عزاوية، خبيرك في هندسة البترول لحقل عزاوية (MARETAP S.A.، CPF جرجيس). اطرح سؤالك حول الإنتاج أو تحليل الآبار أو مؤشرات الخزان أو التقارير التقنية.",
            }.get(lang)
            return {'answer': greeting, 'chart_data': None, 'suggestions': generate_suggestions(question, lang=lang)}

        logger.info(f"Question: {question[:120]}")

        # Build enhanced search query
        search_query = question
        year_match = re.search(r'\b(20\d{2})\b', question)
        well_match = re.search(r'\b(ezz?\s*[-#]?\s*\d+)\b', question, re.IGNORECASE)
        if year_match:
            search_query += f" {year_match.group(1)} production operations"
        if well_match:
            search_query += f" {well_match.group(1)} workover intervention performance"

        doc_results = retrieve_smart(query=search_query, doc_id=doc_id, filename=filename, k=6)

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
            sources = {}
            for d in doc_results:
                src = d.metadata.get('filename', 'Document')
                sources.setdefault(src, []).append(d.page_content)
            for src, chunks in sources.items():
                doc_context += f"\n--- Source: {src} ---\n"
                doc_context += "\n".join(chunks)

        sql_context = get_sql_context(question)
        logger.info(f"SQL CONTEXT ({len(sql_context)} chars): {sql_context[:400] if sql_context else 'EMPTY'}")

        # Block PDF data when SQL has authoritative production data
        sql_has_data = bool(sql_context and len(sql_context.strip()) > 50)
        production_keywords = [
            'top', 'meilleur', 'classement', 'performer', 'production', 'bopd',
            'stb', 'total', 'puits', 'well', 'barils', 'huile', 'oil', 'resume',
            'résumé', 'bilan', 'global', 'champ', 'field', 'kpi', 'performance',
            'wct', 'bsw', 'gor', 'water cut', 'reservoir', 'réservoir',
        ]
        has_production_question = any(w in q_lower for w in production_keywords)
        if sql_has_data and has_production_question:
            doc_context = ""
            logger.info("SQL data authoritative for production question — documents excluded from prompt")

        history_text = ""
        if history and len(history) > 0:
            last = history[-1]
            history_text = f"\n=== PREVIOUS EXCHANGE ===\nQ: {last['question']}\nA: {last['answer'][:300]}...\n"

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

        prompt = f"""{SYSTEM_PROMPT.replace('{TODAY}', today_str)}

════════════════════════════════════════════════════
CONTEXT FOR THIS RESPONSE
════════════════════════════════════════════════════
DATE: {today_str}
RESPONSE LANGUAGE: {langue_nom}
SOURCE LINE (use verbatim): {source_line}
{top_n_rule}

=== SQL DATABASE CONTEXT (AUTHORITATIVE — use these numbers exclusively) ===
{sql_context if sql_context else "No SQL data available for this query."}
=== END SQL CONTEXT ===

=== DOCUMENT CONTEXT (qualitative reference only — never override SQL numbers) ===
{doc_context if doc_context else "No documents attached."}
=== END DOCUMENT CONTEXT ===

=== INDEXED DOCUMENTS AVAILABLE ===
{docs_list}
=== END DOCUMENTS LIST ===

{history_text}{memory_context}
════════════════════════════════════════════════════
QUESTION: {question}
════════════════════════════════════════════════════"""

        response = get_llm().invoke(prompt)
        answer = response.strip()
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