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
    if _llm is None: #garantit que l'objet LLM n'est créé qu'une seule fois pendant toute la durée de vie du serveur Django.
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
                filter={"filename": {"$eq": filename}} #Cherche seulement dans CE fichier
            )
            if results:
                return results

        return vs.max_marginal_relevance_search(
            query, k=k, fetch_k=k*4, lambda_mult=0.5  #k*4 pour explore plus  large , trouver des infos meme loin  dans la base
        )

    except Exception as e:
        logger.error(f"Erreur retrieval : {e}")
        return []


def get_available_documents():  #la liste des fichiers qui existent dans ton vector store dans la  base (Chroma)
    try:
        collection = get_global_vectorstore()._collection #_collection = base de données Chroma (bas niveau)
        results    = collection.get(include=['metadatas'])  #donne-moi uniquement les metadata
        filenames  = set()   #éviter les doublons
        for meta in results.get('metadatas', []):
            if meta and meta.get('filename'):
                filenames.add(meta['filename'])  #Ajoute le nom du fichier sans  duplication
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
            well = DimWell.objects.filter(well_code__icontains=raw.replace('-', '')).first()  #icontains = recherche flexible
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

    if any(w in q for w in ['production', 'total', 'champ', 'bopd', 'huile',
                             'résumé', 'resume', 'situation', 'global',
                             'bilan', 'analyse', 'performance', 'kpi']):
        s = get_field_production_summary()
        context += f"""
=== PRODUCTION GLOBALE CHAMP EZZAOUIA ===
- BOPD moyen       : {s['avg_bopd']:,.1f} barils/jour
- Huile totale     : {s['total_oil_stbd']:,.0f} STB
- Eau totale (BWPD): {s['total_water_bwpd']:,.0f} BWPD
- Gaz total        : {s['total_gas_mscf']:,.0f} MSCF
- BSW moyen        : {s['avg_bsw']:.2f}%
- GOR moyen        : {s['avg_gor']:,.0f} SCF/STB
- Heures prod moy  : {s['avg_prodhours']:.1f} h/j
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

    years_found = re.findall(r'\b(20\d{2})\b', q)
    year_match = re.search(r'\b(20\d{2})\b', q)
    if years_found:
        if len(years_found) >= 2:
            y_start, y_end = int(min(years_found)), int(max(years_found))
            trend = get_monthly_trend(year_start=y_start, year_end=y_end)
            context += f"\n=== PRODUCTION {y_start}–{y_end} (mensuel) ===\n"
            if trend:
                for t in trend:
                    context += (f"  {str(t['month_name']):12} {t['year']} : "
                                f"{t['total_oil']:>10,.0f} STB — "
                                f"BSW {t['avg_bsw']:.1f}%\n")
            else:
                context += f"[SQL] Pas de données pour {y_start}–{y_end}.\n"
        else:
            year    = int(years_found[0])
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
        if len(years_found) >= 2:
            y_start, y_end = int(min(years_found)), int(max(years_found))
            kpis  = get_well_kpis(well_key=well.well_key, year=None)
            trend = get_monthly_trend(well_key=well.well_key, year_start=y_start, year_end=y_end)
        else:
            year  = int(years_found[0]) if years_found else None
            kpis  = get_well_kpis(well_key=well.well_key, year=year)
            trend = get_monthly_trend(well_key=well.well_key, year=year)
        context += f"\n=== PUITS {well.well_code} — {well.libelle} ===\n"
        context += f"- Statut : {'Fermé' if well.closed == 'Y' else 'Actif'}\n"
        context += f"- Layer  : {well.layer}\n"
        if kpis:
            k = kpis[0]
            context += f"- BOPD moy      : {k['avg_bopd']:,.1f} STB/j\n"
            context += f"- BOPD max      : {k['max_bopd']:,.0f} STB/j\n"
            context += f"- Gaz (MSCF)    : {k['total_gas'] or 0:,.0f} MSCF\n"
            context += f"- Eau (BWPD)    : {k['total_water'] or 0:,.0f} BWPD\n"
            context += f"- BSW moy       : {k['avg_bsw'] or 0:.2f}%\n"
            context += f"- GOR moy       : {k['avg_gor'] or 0:,.0f} SCF/STB\n"
            context += f"- Heures prod   : {k['avg_prodhours'] or 0:.1f} h/j\n"
            context += f"- Huile totale  : {k['total_oil']:,.0f} STB\n"
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

    if any(w in q for w in ['tank', 'bac', 'stockage', 'volumebbls', 'niveau', 'bbls']):
        from apps.kpis.calculators import get_tank_levels
        tanks = get_tank_levels()
        if tanks:
            context += f"\n=== NIVEAUX TANKS (dernières données) ===\n"
            seen = {}
            for t in tanks:
                code = t.get('tank_code', '-')
                seen[code] = t
            for code, t in seen.items():
                context += (f"- {code:10} ({t.get('tank_name',''):20}) "
                            f"— {t.get('date','')} : {t.get('volume') or 0:,} BBL\n")

    if any(w in q for w in ['statut', 'status', 'heures', 'prodhours',
                             'pression', 'choke', 'tubing', 'casing']):
        from apps.kpis.calculators import get_well_status_kpis
        well_ref = normalize_well_code(question)
        if well_ref:
            status_data = get_well_status_kpis(well_key=well_ref.well_key)
            if status_data:
                latest = status_data[0]
                context += f"\n=== STATUT OPÉRATIONNEL {well_ref.well_code} (dernière entrée) ===\n"
                context += f"- ProdHours  : {latest.get('prodhours_val') or '-'} h\n"
                context += f"- BSW        : {latest.get('bsw_val') or '-'} %\n"
                context += f"- GOR        : {latest.get('gor_val') or '-'} SCF/STB\n"
                context += f"- FlowTemp   : {latest.get('flowtemp_val') or '-'} °F\n"
                context += f"- Choke 16\"  : {latest.get('choke_val') or '-'}\n"
                context += f"- Tubing     : {latest.get('tubing_val') or '-'} psig\n"
                context += f"- Casing     : {latest.get('casing_val') or '-'} psig\n"

    if any(w in q for w in ['liste', 'tous les puits', 'combien', 'inventaire']):
        wells = DimWell.objects.all().order_by('well_code')
        context += f"\n=== INVENTAIRE ({wells.count()} puits) ===\n"
        for w in wells:
            context += (f"- {w.well_code:8} ({w.libelle[:25]:25}) "
                        f"— {'Fermé' if w.closed == 'Y' else 'Actif':6} "
                        f"— Layer: {w.layer}\n")

    return context


_MONTHS_FR = {
    'janvier': 1, 'février': 2, 'fevrier': 2, 'mars': 3, 'avril': 4,
    'mai': 5, 'juin': 6, 'juillet': 7, 'août': 8, 'aout': 8,
    'septembre': 9, 'octobre': 10, 'novembre': 11, 'décembre': 12, 'decembre': 12,
}


def parse_date_range(question):
    """
    Extrait (date_start, date_end) depuis une question en français.
    Exemples :
      "de janvier 2017 à décembre 2020"  → (2017-01-01, 2020-12-31)
      "de mars 2018 à août 2019"         → (2018-03-01, 2019-08-31)
      "2017 à 2020"                      → (2017-01-01, 2020-12-31)
      "2019"                             → (2019-01-01, 2019-12-31)
    """
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

        date_start, date_end = parse_date_range(question)
        trend = get_monthly_trend(well_key=well.well_key, date_start=date_start, date_end=date_end)
        if not trend:
            return None

        labels   = [f"{t['month_name']} {t['year']}" for t in trend]
        oil_data = [round(float(t['total_oil'] or 0), 1) for t in trend]
        bsw_data = [round(float(t['avg_bsw'] or 0), 2) for t in trend]

        return {
            'well_code': well.well_code,
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


def detect_language(text):
    if not text:
        return 'fr'

    if re.search(r'[\u0600-\u06FF]', text):
        return 'ar'

    lowered = text.lower()
    fr_words = ['analyse', 'puits', 'production', 'quel', 'quels', 'comment', 'donne', 'liste', 'montre']
    en_words = ['analyze', 'well', 'production', 'what', 'how', 'show', 'give', 'list']

    fr_score = sum(1 for w in fr_words if re.search(rf'\b{re.escape(w)}\b', lowered))
    en_score = sum(1 for w in en_words if re.search(rf'\b{re.escape(w)}\b', lowered))

    if en_score > fr_score and en_score > 0:
        return 'en'
    if fr_score > 0:
        return 'fr'
    return 'fr'


def generate_suggestions(question, well=None, lang='fr'):
    """Return 3 context-aware follow-up question strings."""
    q = question.lower()
    lang = lang if lang in {'fr', 'en', 'ar'} else 'fr'

    def choose(fr_text, en_text, ar_text):
        if lang == 'en':
            return en_text
        if lang == 'ar':
            return ar_text
        return fr_text

    if well:
        wc = well.well_code
        return [
            choose(
                f"Quelles interventions workover ont ete realisees sur le puits {wc} ?",
                f"What workover interventions were performed on well {wc}?",
                f"ما هي تدخلات الـ workover التي تم تنفيذها على البئر {wc}؟",
            ),
            choose(
                f"Comparez le BSW et GOR du puits {wc} avec la moyenne du champ",
                f"Compare the BSW and GOR of well {wc} with the field average.",
                f"قارن BSW و GOR للبئر {wc} مع متوسط الحقل.",
            ),
            choose(
                f"Quel est le potentiel de recuperation estime pour le puits {wc} ?",
                f"What is the estimated recovery potential for well {wc}?",
                f"ما هو تقدير إمكانية الاسترجاع للبئر {wc}؟",
            ),
        ]

    if any(w in q for w in ['meilleur', 'top', 'classement', 'performer']):
        return [
            choose(
                "Analysez le WCT et GOR des puits les moins performants",
                "Analyze WCT and GOR for the lowest-performing wells.",
                "حلّل WCT و GOR للآبار الأقل أداءً.",
            ),
            choose(
                "Quelles actions correctrices recommandez-vous pour les puits faibles ?",
                "What corrective actions do you recommend for weak wells?",
                "ما الإجراءات التصحيحية التي توصي بها للآبار الضعيفة؟",
            ),
            choose(
                "Comparez la production annuelle 2023 vs 2024 du champ",
                "Compare field annual production for 2023 vs 2024.",
                "قارن الإنتاج السنوي للحقل بين 2023 و2024.",
            ),
        ]

    if any(w in q for w in ['bsw', 'gor', 'wct', 'water cut', 'reservoir', 'réservoir']):
        return [
            choose(
                "Quels puits ont le BSW le plus eleve et quelle est la tendance ?",
                "Which wells have the highest BSW and what is the trend?",
                "ما الآبار ذات أعلى BSW وما هو اتجاهه؟",
            ),
            choose(
                "Analysez l'impact du water cut sur la production nette d'huile",
                "Analyze the impact of water cut on net oil production.",
                "حلّل تأثير الـ water cut على صافي إنتاج النفط.",
            ),
            choose(
                "Quelles recommandations G&G pour reduire le water cut ?",
                "What G&G recommendations can reduce water cut?",
                "ما توصيات G&G لتقليل الـ water cut؟",
            ),
        ]

    if any(w in q for w in ['liste', 'inventaire', 'tous les puits', 'combien']):
        return [
            choose(
                "Quel est le taux d'utilisation des puits actifs ?",
                "What is the utilization rate of active wells?",
                "ما معدل استغلال الآبار النشطة؟",
            ),
            choose(
                "Analysez la production globale du champ EZZAOUIA",
                "Analyze the overall production of the EZZAOUIA field.",
                "حلّل الإنتاج الإجمالي لحقل عزاوية.",
            ),
            choose(
                "Quels puits fermes ont le meilleur potentiel de reactivation ?",
                "Which shut-in wells have the best reactivation potential?",
                "ما الآبار المغلقة ذات أفضل قابلية لإعادة التشغيل؟",
            ),
        ]

    if re.search(r'\b20\d{2}\b', q):
        return [
            choose(
                "Comparez cette periode avec l'annee precedente",
                "Compare this period with the previous year.",
                "قارن هذه الفترة بالسنة السابقة.",
            ),
            choose(
                "Quels evenements operationnels ont impacte la production cette annee ?",
                "Which operational events impacted production this year?",
                "ما الأحداث التشغيلية التي أثرت على الإنتاج هذه السنة؟",
            ),
            choose(
                "Analysez la tendance mensuelle de la production sur cette periode",
                "Analyze the monthly production trend over this period.",
                "حلّل الاتجاه الشهري للإنتاج خلال هذه الفترة.",
            ),
        ]

    return [
        choose(
            "Analysez la performance globale du champ EZZAOUIA",
            "Analyze the overall performance of the EZZAOUIA field.",
            "حلّل الأداء العام لحقل عزاوية.",
        ),
        choose(
            "Quels sont les top 5 puits producteurs actuellement ?",
            "What are the top 5 producing wells currently?",
            "ما هي أفضل 5 آبار إنتاجاً حالياً؟",
        ),
        choose(
            "Montrez l'evolution mensuelle de la production du champ",
            "Show the monthly evolution of field production.",
            "اعرض التطور الشهري لإنتاج الحقل.",
        ),
    ]


def ask(question, history=None, doc_id=None, doc_ids=None, filename=None, user=None):
    # Compatibilite : doc_ids (liste) prend priorite sur doc_id (singulier)
    if doc_ids:
        doc_id = doc_ids[0] if len(doc_ids) == 1 else None

    try:
        lang = detect_language(question)
        langue_nom = {
            'fr': 'francais',
            'en': 'anglais',
            'ar': 'arabe',
        }.get(lang, 'francais')

        q_lower = question.lower().strip()
        salutations = [
            'bonjour', 'bonsoir', 'salut', 'hello', 'hi', 'salam', 'merci',
            'مرحبا', 'السلام عليكم', 'شكرا',
        ]

        if any(q_lower == s or q_lower.startswith(s + ' ') for s in salutations):
            greeting = {
                'fr': "Bonjour ! Je suis votre assistant expert pour le champ EZZAOUIA. Posez-moi une question sur la production, les puits ou les rapports techniques.",
                'en': "Hello! I am your expert assistant for the EZZAOUIA field. Ask me about production, wells, or technical reports.",
                'ar': "مرحباً! أنا مساعدك الخبير لحقل عزاوية. اطرح سؤالك حول الإنتاج أو الآبار أو التقارير التقنية.",
            }.get(lang)
            return {
                'answer': greeting,
                'chart_data': None,
                'suggestions': generate_suggestions(question, well=None, lang=lang),
            }

        logger.info(f"Question : {question[:100]}")

        search_query = question
        year_match = re.search(r'\b(20\d{2})\b', question)
        well_match = re.search(r'\b(ezz?\s*[-#]?\s*\d+)\b', question, re.IGNORECASE)

        if year_match:
            search_query += f" {year_match.group(1)} activites operations"
        if well_match:
            search_query += f" {well_match.group(1)} intervention workover"

        doc_results = retrieve_smart(query=search_query, doc_id=doc_id, filename=filename, k=6)

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
        logger.info(f"SQL CONTEXT: {sql_context[:500] if sql_context else 'VIDE'}")

        # Si le SQL répond à une question de production/classement, bloquer les documents
        # pour éviter que Llama3 ancre sur des chiffres PDF contradictoires
        sql_has_data = bool(sql_context and len(sql_context.strip()) > 50)
        production_keywords = [
            'top', 'meilleur', 'classement', 'performer', 'production', 'bopd',
            'stb', 'total', 'puits', 'well', 'barils', 'huile', 'oil', 'resume',
            'résumé', 'bilan', 'global', 'champ', 'field', 'kpi', 'performance',
        ]
        has_production_question = any(w in q_lower for w in production_keywords)

        if sql_has_data and has_production_question:
            doc_context = ""
            logger.info("SQL data present pour question production -> documents supprimes du prompt")

        history_text = ""
        if history and len(history) > 0:
            last = history[-1]
            history_text = f"\n=== ECHANGE PRECEDENT ===\nQ: {last['question']}\nR: {last['answer'][:200]}...\n"

        from .memory import get_user_memory, update_user_memory
        memory_context = get_user_memory(user) if user else ""

        available_docs = get_available_documents()
        docs_list = "\n".join(f"- {d}" for d in available_docs) if available_docs else "Aucun document indexe"

        top_n_match = re.search(r'\btop\s+(\d+)\b', question, re.IGNORECASE)
        top_n = int(top_n_match.group(1)) if top_n_match else None
        top_n_rule = (
            f"\n9. La question demande exactement TOP {top_n} - tu DOIS lister "
            f"exactement {top_n} elements, ni plus ni moins, dans TOUTES les sections de ta reponse."
            if top_n else ""
        )

        docs_section = (
            f"=== DOCUMENTS DE REFERENCE (texte qualitatif uniquement — JAMAIS utiliser pour des chiffres de production) ===\n"
            f"{doc_context}\n"
            f"=== FIN DOCUMENTS ==="
            if doc_context else
            "(Aucun document : repondre exclusivement avec les donnees base de donnees ci-dessus.)"
        )

        prompt = f"""=== DONNÉES OFFICIELLES BASE DE DONNÉES EZZAOUIA (SOURCE UNIQUE ET DÉFINITIVE) ===
{sql_context if sql_context else "Aucune donnee SQL pertinente pour cette question."}
=== FIN DONNÉES BASE ===

INSTRUCTION CRITIQUE : Les chiffres ci-dessus sont les SEULES données numériques autorisées.
Toute valeur issue des documents ci-dessous qui contredit ces chiffres DOIT être ignorée.
Si la section DONNÉES OFFICIELLES contient un classement de puits, répondre UNIQUEMENT avec ces données.

---

Tu es un Expert Senior en Ingenierie de Production Petroliere et Asset Management pour le champ EZZAOUIA (MARETAP, Tunisie - CPF Zarzis).

=== SCHEMA DATA WAREHOUSE (SQL SERVER) ===
TABLES DISPONIBLES — utilise UNIQUEMENT ces noms exacts :

1. FactProduction   : FactProdKey, DateKey(FK), WellKey(FK), WellStatusKey(FK),
                      DailyOilPerWellSTBD, DailyGasPerWellMSCF, WellStatusWaterBWPD
2. FactTankLevel    : FactTankKey, TankKey(FK), DateKey(FK), VolumeBBLS
3. DimDate          : DateKey, FullDate, Day, Month, Year, Quarter, MonthName
4. DimWell          : WellKey, WellCode, Libelle, Layer, Closed, PowerTypeKey(FK),
                      ProdMethodKey(FK), TypeWellKey(FK)
5. DimWellStatus    : WellStatusKey, WellKey(FK), DateKey(FK), ProdHours, BSW, GOR,
                      FlowTempDegF, TubingPsig, CasingPsig, Remarque
6. DimTank          : TankKey, TankCode, TankName

TABLES SUPPRIMEES (ne jamais utiliser) : FactDailyProduction, FactWellTest

=== REGLES ABSOLUES ===
1. LANGUE DETECTEE : {lang}
   Reponds OBLIGATOIREMENT en {langue_nom}.
2. Utilise UNIQUEMENT les donnees de la section DONNÉES OFFICIELLES ci-dessus. Zero hallucination.
3. Info manquante -> "Information non disponible dans les donnees actuelles."
4. Hors sujet EZZAOUIA -> "Hors perimetre."
5. SQL INTERDIT : Ne jamais citer FactDailyProduction ni FactWellTest (tables supprimees).
6. CHIFFRES DE PRODUCTION : Utiliser exclusivement les valeurs de la section DONNÉES OFFICIELLES.
   INTERDIT d'utiliser des chiffres de production issus des documents si la base de donnees contient deja ces informations.
7. CLASSEMENT DE PUITS : Si DONNÉES OFFICIELLES contient un classement (BOPD, Total STB),
   utiliser UNIQUEMENT ce classement. Ne jamais le remplacer par des donnees de documents PDF.
8. DOCUMENTS : Autorises uniquement pour contexte qualitatif (workover, geologie, historique evenements).
   JAMAIS pour des chiffres de production, BOPD, STB, BSW, GOR si la DB en contient.{top_n_rule}

=== LANGUE DE REPONSE ===
Langue detectee : {lang} — Reponds UNIQUEMENT dans cette langue.

=== FORMAT DE REPONSE ===
- CLASSEMENT / TOP N : tableau avec rang, code puits, BOPD moyen, total STB, BSW%.
- ANALYSE PERFORMANCE : synthese executive + indicateurs + alertes manageriales.
- RESERVOIR (WCT/GOR/pression) : tendances, risques, recommandations G&G.
- QUESTION SIMPLE : reponse directe (valeur + unite).

{history_text}
{memory_context}

=== DOCUMENTS DISPONIBLES ===
{docs_list}

{docs_section}

=== QUESTION ===
{question}

=== ANALYSE EXPERTE ==="""

        response = get_llm().invoke(prompt)
        answer = response.strip()
        logger.info(f"Reponse : {len(answer)} chars")

        well = normalize_well_code(question)
        chart_data = build_chart_data(question) if detect_chart_request(question) else None
        suggestions = generate_suggestions(question, well=well, lang=lang)

        if user:
            update_user_memory(user, question, answer, well=well)

        return {
            'answer': answer,
            'chart_data': chart_data,
            'suggestions': suggestions,
        }

    except Exception as e:
        logger.error(f"Erreur ask() : {e}")
        return {
            'answer': f"Erreur technique : {str(e)}",
            'chart_data': None,
            'suggestions': [],
        }
