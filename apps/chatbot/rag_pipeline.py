import logging
import re
import hashlib
from django.conf import settings
from langchain_ollama import OllamaLLM
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

logger = logging.getLogger('apps')

_llm          = None
_embeddings   = None
_vectorstores = {}
_global_vectorstore = None


def get_llm():
    global _llm
    if _llm is None:
        _llm = OllamaLLM(
            model=settings.OLLAMA_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=0.05,
            num_ctx=4096,
            timeout=120,
        )
    return _llm


def get_embeddings():
    global _embeddings
    if _embeddings is None:
        _embeddings = SentenceTransformerEmbeddings(
            model_name="all-MiniLM-L6-v2"
        )
    return _embeddings


def _get_doc_collection_name(doc_id):
    safe = hashlib.md5(str(doc_id).encode()).hexdigest()[:12]
    return f"doc_{safe}"


def get_vectorstore_for_doc(doc_id):
    global _vectorstores
    if doc_id not in _vectorstores:
        import os
        persist_dir = os.path.join(
            settings.CHROMA_PERSIST_DIR,
            f"doc_{doc_id}"
        )
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

        docs = []
        for i, chunk in enumerate(chunks):
            docs.append(Document(
                page_content=chunk,
                metadata={**metadata, 'chunk_index': i, 'chunk_total': len(chunks)},
            ))

        if doc_id:
            get_vectorstore_for_doc(doc_id).add_documents(docs)

        get_global_vectorstore().add_documents(docs)
        logger.info(f"Indexé {len(docs)} chunks")
        return len(docs)

    except Exception as e:
        logger.error(f"Erreur indexation : {e}")
        return 0


def retrieve_smart(query, doc_id=None, filename=None, k=6):
    try:
        if doc_id:
            vs = get_vectorstore_for_doc(doc_id)
            results = vs.max_marginal_relevance_search(
                query, k=k, fetch_k=k*3, lambda_mult=0.6
            )
            if results:
                return results

        vs = get_global_vectorstore()

        if filename:
            results = vs.similarity_search(
                query, k=k,
                filter={"filename": {"$eq": filename}}
            )
            if results:
                return results

        return vs.max_marginal_relevance_search(
            query, k=k, fetch_k=k*4, lambda_mult=0.5
        )

    except Exception as e:
        logger.error(f"Erreur retrieval : {e}")
        return []


def get_available_documents():
    try:
        collection = get_global_vectorstore()._collection
        results    = collection.get(include=['metadatas'])
        filenames  = set()
        for meta in results.get('metadatas', []):
            if meta and meta.get('filename'):
                filenames.add(meta['filename'])
        return list(filenames)
    except Exception as e:
        logger.error(f"Erreur liste docs : {e}")
        return []


def normalize_well_code(text):
    from apps.warehouse.models import DimWell
    for pattern in [r'\b(ezz\s*[-#]?\s*\d+)\b', r'\b(ez\s*[-#]?\s*\d+)\b']:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            raw  = match.group(1).upper().replace(' ', '').replace('#', '')
            well = DimWell.objects.filter(wellcode__icontains=raw.replace('-', '')).first()
            if not well:
                well = DimWell.objects.filter(wellcode__icontains=raw).first()
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

    if any(w in q for w in ['production', 'total', 'champ', 'bopd', 'huile',
                             'résumé', 'resume', 'situation', 'global',
                             'bilan', 'analyse', 'performance', 'kpi']):
        s = get_field_production_summary()
        context += f"""
=== PRODUCTION GLOBALE CHAMP EZZAOUIA ===
- BOPD moyen       : {s['avg_bopd']:,.1f} barils/jour
- Huile totale     : {s['total_oil_stbd']:,.0f} STB
- Eau totale       : {s['total_water_blsd']:,.0f} BLS
- Gaz total        : {s['total_gas_mscf']:,.0f} MSCF
- BSW moyen        : {s['avg_bsw']:.2f}%
- GOR moyen        : {s['avg_gor']:,.0f} SCF/STB
- Heures prod moy  : {s['avg_prodhours']:.1f} h/j
- Ventes totales   : {s['total_sales']:,.0f}
"""

    if any(w in q for w in ['meilleur', 'top', 'performer', 'classement',
                             'faible', 'low', 'analyse', 'performance']):
        top = get_top_producers(limit=20)
        context += f"\n=== CLASSEMENT PUITS ({len(top)} puits) ===\n"
        for i, w in enumerate(top, 1):
            context += (f"{i:2}. {w['well_code']:8} — "
                        f"BOPD: {w['avg_bopd']:>8,.1f} — "
                        f"Total: {w['total_oil']:>12,.0f} STB — "
                        f"BSW: {w['avg_bsw']:>5.1f}%\n")

    year_match = re.search(r'\b(20\d{2})\b', q)
    if year_match:
        year    = int(year_match.group(1))
        summary = get_field_production_summary(year=year)
        trend   = get_monthly_trend(year=year)
        if summary and summary.get('total_oil_stbd', 0) > 0:
            context += f"\n=== PRODUCTION {year} ===\n"
            context += f"- BOPD moyen : {summary['avg_bopd']:,.1f}\n"
            context += f"- Huile      : {summary['total_oil_stbd']:,.0f} STB\n"
            context += f"- BSW        : {summary['avg_bsw']:.2f}%\n"
            context += f"- GOR        : {summary['avg_gor']:,.0f}\n"
            if trend:
                context += f"\nMensuel {year} :\n"
                for t in trend:
                    context += (f"  {str(t['month_name']):12} : "
                                f"{t['total_oil']:>10,.0f} STB — "
                                f"BSW {t['avg_bsw']:.1f}%\n")
        else:
            context += f"\n[SQL] Pas de données pour {year}.\n"

    well = normalize_well_code(question)
    if well:
        year  = int(year_match.group(1)) if year_match else None
        kpis  = get_well_kpis(well_key=well.wellkey, year=year)
        trend = get_monthly_trend(well_key=well.wellkey, year=year)
        context += f"\n=== PUITS {well.wellcode} — {well.libelle} ===\n"
        context += f"- Statut : {'Fermé' if well.closed == 'Y' else 'Actif'}\n"
        context += f"- Layer  : {well.layer}\n"
        if kpis:
            k = kpis[0]
            context += f"- BOPD moy : {k['avg_bopd']:,.1f}\n"
            context += f"- BOPD max : {k['max_bopd']:,.0f}\n"
            context += f"- BSW moy  : {k['avg_bsw']:.2f}%\n"
            context += f"- GOR moy  : {k['avg_gor']:,.0f}\n"
            context += f"- Huile tot: {k['total_oil']:,.0f} STB\n"
        if trend:
            context += "\nHistorique mensuel :\n"
            for t in trend:
                context += (f"  {str(t['month_name']):12} {t['year']} : "
                            f"{t['total_oil']:>10,.0f} STB — "
                            f"BSW {t['avg_bsw']:.1f}%\n")

    if any(w in q for w in ['wct', 'water cut', 'bsw', 'gor', 'réservoir',
                             'reservoir', 'forecast', 'pression']):
        s   = get_field_production_summary()
        top = get_top_producers(limit=20)
        context += f"\n=== ANALYSE RÉSERVOIR ===\n"
        context += f"- WCT/BSW global : {s['avg_bsw']:.2f}%\n"
        context += f"- GOR global     : {s['avg_gor']:,.0f} SCF/STB\n"
        context += "\nBSW par puits :\n"
        for w in top:
            context += f"  {w['well_code']:8} — BSW: {w['avg_bsw']:>5.1f}% — BOPD: {w['avg_bopd']:>8,.1f}\n"

    if any(w in q for w in ['liste', 'tous les puits', 'combien', 'inventaire']):
        wells = DimWell.objects.all().order_by('wellcode')
        context += f"\n=== INVENTAIRE ({wells.count()} puits) ===\n"
        for w in wells:
            context += (f"- {w.wellcode:8} ({w.libelle[:25]:25}) "
                        f"— {'Fermé' if w.closed == 'Y' else 'Actif':6} "
                        f"— Layer: {w.layer}\n")

    return context


def detect_chart_request(question):
    chart_kw = ['évolution', 'evolution', 'historique', 'tendance', 'trend',
                 'montrez', 'graphique', 'chart', 'courbe', 'progression',
                 'mensuel', 'annuel', 'affiche', 'montre', 'visualis']
    q = question.lower()
    return any(kw in q for kw in chart_kw) and normalize_well_code(question) is not None


def build_chart_data(question):
    """Return Chart.js-compatible data dict for a well's monthly production trend."""
    try:
        from apps.kpis.calculators import get_monthly_trend
        well = normalize_well_code(question)
        if not well:
            return None

        year_match = re.search(r'\b(20\d{2})\b', question)
        year = int(year_match.group(1)) if year_match else None

        trend = get_monthly_trend(well_key=well.wellkey, year=year)
        if not trend:
            return None

        labels   = [f"{t['month_name']} {t['year']}" for t in trend]
        oil_data = [round(float(t['total_oil'] or 0), 1) for t in trend]
        bsw_data = [round(float(t['avg_bsw'] or 0), 2) for t in trend]

        return {
            'well_code': well.wellcode,
            'well_name': well.libelle or '',
            'labels':    labels,
            'datasets': [
                {
                    'label':           f'Production Huile (STB)',
                    'data':            oil_data,
                    'type':            'bar',
                    'yAxisID':         'y',
                    'backgroundColor': 'rgba(201,168,76,0.55)',
                    'borderColor':     '#C9A84C',
                    'borderWidth':     1,
                },
                {
                    'label':           'BSW (%)',
                    'data':            bsw_data,
                    'type':            'line',
                    'yAxisID':         'y1',
                    'borderColor':     '#E05555',
                    'backgroundColor': 'rgba(224,85,85,0.08)',
                    'borderWidth':     2,
                    'pointRadius':     3,
                    'fill':            False,
                },
            ],
        }
    except Exception as e:
        logger.error(f"Erreur build_chart_data : {e}")
        return None


def generate_suggestions(question, well=None):
    """Return 3 context-aware follow-up question strings."""
    q = question.lower()

    if well:
        wc = well.wellcode
        return [
            f"Quelles interventions workover ont été réalisées sur le puits {wc} ?",
            f"Comparez le BSW et GOR du puits {wc} avec la moyenne du champ",
            f"Quel est le potentiel de récupération estimé pour le puits {wc} ?",
        ]
    if any(w in q for w in ['meilleur', 'top', 'classement', 'performer']):
        return [
            "Analysez le WCT et GOR des puits les moins performants",
            "Quelles actions correctrices recommandez-vous pour les puits faibles ?",
            "Comparez la production annuelle 2023 vs 2024 du champ",
        ]
    if any(w in q for w in ['bsw', 'gor', 'wct', 'water cut', 'réservoir', 'reservoir']):
        return [
            "Quels puits ont le BSW le plus élevé et quelle est la tendance ?",
            "Analysez l'impact du water cut sur la production nette d'huile",
            "Quelles recommandations G&G pour réduire le water cut ?",
        ]
    if any(w in q for w in ['liste', 'inventaire', 'tous les puits', 'combien']):
        return [
            "Quel est le taux d'utilisation des puits actifs ?",
            "Analysez la production globale du champ EZZAOUIA",
            "Quels puits fermés ont le meilleur potentiel de réactivation ?",
        ]
    if re.search(r'\b20\d{2}\b', q):
        return [
            "Comparez cette période avec l'année précédente",
            "Quels événements opérationnels ont impacté la production cette année ?",
            "Analysez la tendance mensuelle de la production sur cette période",
        ]
    return [
        "Analysez la performance globale du champ EZZAOUIA",
        "Quels sont les top 5 puits producteurs actuellement ?",
        "Montrez l'évolution mensuelle de la production du champ",
    ]


def ask(question, history=None, doc_id=None, filename=None):
    try:
        q_lower = question.lower().strip()
        salutations = ['bonjour', 'bonsoir', 'salut', 'hello', 'hi', 'salam', 'merci']
        if any(q_lower == s or q_lower.startswith(s + ' ') for s in salutations):
            return {
                'answer': "Bonjour ! Je suis votre assistant expert pour le champ EZZAOUIA. Posez-moi une question sur la production, les puits ou les rapports techniques.",
                'chart_data':  None,
                'suggestions': [
                    "Analyse la performance du champ EZZAOUIA",
                    "Quels sont les top 5 puits producteurs ?",
                    "Liste tous les puits actifs avec leur statut",
                ],
            }
        logger.info(f"Question : {question[:100]}")

        search_query = question
        year_match   = re.search(r'\b(20\d{2})\b', question)
        well_match   = re.search(r'\b(ezz?\s*[-#]?\s*\d+)\b', question, re.IGNORECASE)

        if year_match:
            search_query += f" {year_match.group(1)} activités opérations"
        if well_match:
            search_query += f" {well_match.group(1)} intervention workover"

        doc_results = retrieve_smart(
            query=search_query, doc_id=doc_id, filename=filename, k=6
        )

        doc_context = ""
        if doc_results:
            sources = {}
            for d in doc_results:
                src = d.metadata.get('filename', 'Document')
                sources.setdefault(src, []).append(d.page_content)
            for src, chunks in sources.items():
                doc_context += f"\n--- Source : {src} ---\n"
                doc_context += "\n".join(chunks)

        sql_context = get_sql_context(question)

        history_text = ""
        if history and len(history) > 0:
            # Seulement le dernier échange pour éviter la confusion
            last = history[-1]
            history_text = f"\n=== ÉCHANGE PRÉCÉDENT ===\nQ: {last['question']}\nR: {last['answer'][:200]}...\n"

        available_docs = get_available_documents()
        docs_list = "\n".join(f"- {d}" for d in available_docs) if available_docs else "Aucun document indexé"

        prompt = f"""Tu es un Expert Senior en Ingénierie de Production Pétrolière et Asset Management pour le champ EZZAOUIA (MARETAP, Tunisie – CPF Zarzis).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RÈGLES ABSOLUES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Français uniquement. Terminologie pétrolière internationale.
2. Utilise UNIQUEMENT les données ci-dessous. Zéro hallucination.
3. Info manquante → "Information non disponible dans les données actuelles."
4. Ne jamais mélanger les informations de sources différentes.
5. Hors sujet EZZAOUIA → "Hors périmètre."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DOCUMENTS DISPONIBLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{docs_list}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FORMAT DE RÉPONSE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
▌ ANALYSE PERFORMANCE :
  📊 SYNTHÈSE EXECUTIVE
     ✅ Succès | ⚠️ Risques | 🎯 Actions prioritaires
  📋 Indicateur | Valeur | Référence | Écart | Commentaire
  🚨 ALERTES MANAGÉRIALES

▌ RÉSERVOIR (WCT/GOR/pression) :
  📈 Tendance | 🔴 Risques | 💡 Recommandations G&G

▌ BUDGÉTAIRE (CAPEX/OPEX/AFE) :
  💰 Écarts | 🔧 Leviers OPEX | 📈 Impact ROI

▌ HISTORIQUE (année/événement) :
  📅 Chronologie | 📊 Données période | 💥 Impact production

▌ QUESTION SIMPLE :
  → Réponse directe : valeur + unité + source

{history_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DONNÉES SQL SERVER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{sql_context if sql_context else "Aucune donnée SQL pertinente."}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DOCUMENTS TECHNIQUES INDEXÉS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{doc_context if doc_context else "Aucun extrait pertinent trouvé."}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
QUESTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{question}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ANALYSE EXPERTE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

        response = get_llm().invoke(prompt)
        answer   = response.strip()
        logger.info(f"Réponse : {len(answer)} chars")

        well       = normalize_well_code(question)
        chart_data = build_chart_data(question) if detect_chart_request(question) else None
        suggestions = generate_suggestions(question, well=well)

        return {
            'answer':      answer,
            'chart_data':  chart_data,
            'suggestions': suggestions,
        }

    except Exception as e:
        logger.error(f"Erreur ask() : {e}")
        return {
            'answer':      f"Erreur technique : {str(e)}",
            'chart_data':  None,
            'suggestions': [],
        }