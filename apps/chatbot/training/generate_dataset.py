"""
EZZAOUIA Chatbot — Training Dataset Generator
Queries real SQL Server DWH and produces JSONL Q&A pairs.
Run inside Docker: python apps/chatbot/training/generate_dataset.py
"""
import os
import sys
import json
import datetime

# ── Django bootstrap ──────────────────────────────────────────────
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from apps.kpis.calculators import (
    get_field_production_summary,
    get_top_producers,
    get_well_kpis,
    get_monthly_trend,
    get_well_status_kpis,
)
from apps.warehouse.models import DimWell

TODAY = datetime.date.today().strftime('%d/%m/%Y')
SOURCE = f"*Source: EZZAOUIA DWH — {TODAY} — historical data 1994–2025*"

dataset = []
seen_prompts = set()


def add(prompt, response):
    if not prompt or not response:
        return
    prompt_clean = prompt.strip()
    response_clean = response.strip()
    if len(response_clean) <= 50:
        return
    key = prompt_clean.lower()
    if key in seen_prompts:
        return
    seen_prompts.add(key)
    dataset.append({'prompt': prompt_clean, 'response': response_clean})


def sf(val, decimals=1):
    """Safe float format."""
    try:
        return round(float(val or 0), decimals)
    except (TypeError, ValueError):
        return 0.0


def si(val):
    """Safe int format."""
    try:
        return int(val or 0)
    except (TypeError, ValueError):
        return 0


def bsw_flag(bsw):
    v = sf(bsw, 1)
    if v > 80:
        return "🔴 CRITICAL — Advanced flooding"
    if v > 50:
        return "⚠️ Elevated"
    return "✅ Normal"


def bsw_emoji(bsw):
    v = sf(bsw, 1)
    if v > 80:
        return "🔴"
    if v > 50:
        return "⚠️"
    return "✅"


def status_label(well, en=True):
    if well.closed == 'Y':
        return "Shut-in" if en else "Fermé"
    return "Active" if en else "Actif"


def gor_note(gor):
    if sf(gor, 0) == 0:
        return "GOR data unavailable — field measurement recommended"
    return f"{sf(gor, 0):,.0f} SCF/STB"


def float_or_none(val):
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


# ═══════════════════════════════════════════════════════════════════
# STEP 1 — Fetch all real data upfront
# ═══════════════════════════════════════════════════════════════════

print("Fetching data from DWH...")
wells = list(DimWell.objects.order_by('ordre', 'well_code'))
summary = get_field_production_summary()
top_all = get_top_producers(limit=50)

print(f"  Wells: {len(wells)}")
print(f"  Field avg BOPD: {summary.get('avg_bopd', 0)}")
print(f"  Top producers fetched: {len(top_all)}")

# Build per-well KPI cache
well_kpis = {}
well_trend_cache = {}
for w in wells:
    kpis = get_well_kpis(well_key=w.well_key)
    if kpis:
        well_kpis[w.well_key] = kpis[0]

print(f"  KPIs cached for {len(well_kpis)} wells")


# ═══════════════════════════════════════════════════════════════════
# CATEGORY 1 — Per-well Q&A (English + French + Arabic)
# ═══════════════════════════════════════════════════════════════════

for well in wells:
    k = well_kpis.get(well.well_key)
    if not k:
        continue

    wc = well.well_code
    lib = well.libelle or wc
    layer = well.layer or "N/A"
    avg_bopd = sf(k.get('avg_bopd'), 1)
    max_bopd = sf(k.get('max_bopd'), 0)
    total_oil = si(k.get('total_oil'))
    avg_bsw = sf(k.get('avg_bsw'), 1)
    avg_gor = sf(k.get('avg_gor'), 0)
    avg_ph = sf(k.get('avg_prodhours'), 1)
    total_gas = sf(k.get('total_gas'), 0)
    total_water = sf(k.get('total_water'), 0)
    field_total = si(summary.get('total_oil_stbd'))
    pct_field = (total_oil / field_total * 100) if field_total > 0 else 0
    is_shut = well.closed == 'Y'

    # ── 1a. Average daily production (EN) ────────────────────────
    add(
        f"What is the average daily production of well {wc}?",
        f"## 🔬 Well {wc} — Technical Assessment\n\n"
        f"> **Executive Summary:** Well **{wc}** ({lib}) averages **{avg_bopd:,.1f} STB/j** of oil, "
        f"representing approximately **{pct_field:.1f}%** of total field cumulative production. "
        f"BSW is {avg_bsw:.1f}% — {bsw_flag(avg_bsw).split('—')[0].strip()}. "
        f"{'Well is currently **shut-in**.' if is_shut else 'Well is currently **active**.'}\n\n"
        f"### Well Performance Summary\n"
        f"| Parameter | Value | Unit | Assessment |\n"
        f"|-----------|------:|------|------------|\n"
        f"| Avg BOPD | **{avg_bopd:,.1f}** | STB/j | {'Shut-in' if is_shut else 'Active production'} |\n"
        f"| Peak BOPD | **{max_bopd:,.0f}** | STB/j | Historical maximum |\n"
        f"| Cumulative Oil | **{total_oil:,.0f}** | STB | {pct_field:.1f}% of field total |\n"
        f"| Average BSW | **{avg_bsw:.1f}** | % | {bsw_flag(avg_bsw)} |\n"
        f"| Average GOR | **{gor_note(avg_gor)}** | — | {'Normal' if avg_gor == 0 or avg_gor < 500 else 'Elevated'} |\n"
        f"| Avg Prod Hours | **{avg_ph:.1f}** | h/j | {'🔴 Critical' if avg_ph < 10 else '✅ Acceptable'} |\n"
        f"| Status | — | — | {'🔴 Shut-in' if is_shut else '✅ Active'} |\n"
        f"| Layer | — | — | {layer} |\n\n"
        f"### Intervention Recommendations\n"
        f"1. **Production monitoring:** {'Investigate cause of shut-in and evaluate reactivation potential.' if is_shut else f'Continue routine surveillance; optimize choke setting to maximize oil rate while controlling BSW.'}\n"
        f"2. **{'Reactivation study' if is_shut else 'BSW management'}:** "
        f"{'Evaluate workover options to restore production.' if is_shut else 'Monitor BSW trend — ' + ('workover intervention recommended if BSW > 80%.' if avg_bsw > 60 else 'current WCT within acceptable range.')}\n"
        f"3. **Long-term:** Integrate {wc} data into field decline analysis and reserve estimation.\n\n"
        f"{SOURCE}"
    )

    # ── 1b. Average daily production (FR) ────────────────────────
    add(
        f"Quelle est la production journalière moyenne du puits {wc}?",
        f"## 🔬 Puits {wc} — Évaluation Technique\n\n"
        f"> **Résumé exécutif:** Le puits **{wc}** ({lib}) produit en moyenne **{avg_bopd:,.1f} STB/j** d'huile, "
        f"représentant environ **{pct_field:.1f}%** de la production cumulée totale du champ. "
        f"Le BSW est de {avg_bsw:.1f}% — {bsw_flag(avg_bsw).split('—')[0].strip()}. "
        f"{'Le puits est actuellement **fermé**.' if is_shut else 'Le puits est actuellement **actif**.'}\n\n"
        f"### Résumé de Performance du Puits\n"
        f"| Paramètre | Valeur | Unité | Évaluation |\n"
        f"|-----------|-------:|-------|------------|\n"
        f"| BOPD moyen | **{avg_bopd:,.1f}** | STB/j | {'Puits fermé' if is_shut else 'Production active'} |\n"
        f"| BOPD max | **{max_bopd:,.0f}** | STB/j | Maximum historique |\n"
        f"| Huile cumulée | **{total_oil:,.0f}** | STB | {pct_field:.1f}% du total champ |\n"
        f"| BSW moyen | **{avg_bsw:.1f}** | % | {bsw_flag(avg_bsw)} |\n"
        f"| GOR moyen | **{gor_note(avg_gor)}** | — | {'Normal' if avg_gor == 0 or avg_gor < 500 else 'Élevé'} |\n"
        f"| Heures prod | **{avg_ph:.1f}** | h/j | {'🔴 Critique' if avg_ph < 10 else '✅ Acceptable'} |\n"
        f"| Statut | — | — | {'🔴 Fermé' if is_shut else '✅ Actif'} |\n"
        f"| Couche | — | — | {layer} |\n\n"
        f"### Recommandations d'Intervention\n"
        f"1. **Surveillance production:** {'Analyser la cause de fermeture et évaluer le potentiel de remise en production.' if is_shut else f'Poursuivre la surveillance routine; optimiser le choke pour maximiser le débit huile tout en contrôlant le BSW.'}\n"
        f"2. **{'Étude de réactivation' if is_shut else 'Gestion du BSW'}:** "
        f"{'Évaluer les options workover pour rétablir la production.' if is_shut else 'Surveiller la tendance BSW — ' + ('intervention workover recommandée si BSW > 80%.' if avg_bsw > 60 else 'le WCT actuel reste dans les limites acceptables.')}\n"
        f"3. **Long terme:** Intégrer les données de {wc} dans l'analyse de déclin du champ et l'estimation des réserves.\n\n"
        f"{SOURCE}"
    )

    # ── 1c. Arabic ───────────────────────────────────────────────
    add(
        f"ما هو متوسط الإنتاج اليومي للبئر {wc}؟",
        f"## 🔬 البئر {wc} — التقييم التقني\n\n"
        f"> **الملخص التنفيذي:** ينتج البئر **{wc}** ({lib}) بمعدل **{avg_bopd:,.1f} STB/j** من النفط، "
        f"ما يمثل **{pct_field:.1f}%** من الإنتاج التراكمي الإجمالي للحقل. "
        f"نسبة الماء BSW هي {avg_bsw:.1f}%. "
        f"{'البئر مغلق حالياً.' if is_shut else 'البئر نشط حالياً.'}\n\n"
        f"### ملخص أداء البئر\n"
        f"| المعامل | القيمة | الوحدة |\n"
        f"|---------|-------:|--------|\n"
        f"| متوسط BOPD | **{avg_bopd:,.1f}** | STB/j |\n"
        f"| أقصى BOPD | **{max_bopd:,.0f}** | STB/j |\n"
        f"| النفط التراكمي | **{total_oil:,.0f}** | STB |\n"
        f"| متوسط BSW | **{avg_bsw:.1f}** | % |\n"
        f"| الحالة | — | {'🔴 مغلق' if is_shut else '✅ نشط'} |\n\n"
        f"### التوصيات الهندسية\n"
        f"1. **المراقبة:** {'تحليل سبب الإغلاق وتقييم إمكانية إعادة التشغيل.' if is_shut else 'متابعة مراقبة الإنتاج وتحسين إعدادات الخانق.'}\n"
        f"2. **إدارة BSW:** {'تقييم خيارات التدخل workover.' if is_shut else ('تدخل workover موصى به إذا تجاوز BSW 80%.' if avg_bsw > 60 else 'BSW ضمن الحدود المقبولة.')}\n\n"
        f"{SOURCE}"
    )

    # ── 1d. BSW question ─────────────────────────────────────────
    add(
        f"What is the BSW of well {wc}?",
        f"## 📊 Well {wc} — Water Cut (BSW) Analysis\n\n"
        f"> **Executive Summary:** Well **{wc}** has an average BSW of **{avg_bsw:.1f}%** — {bsw_flag(avg_bsw)}. "
        f"{'Immediate workover assessment is required.' if avg_bsw > 80 else 'Water cut remains within manageable range.' if avg_bsw < 50 else 'BSW is elevated and should be closely monitored.'}\n\n"
        f"### BSW Assessment\n"
        f"| Parameter | Value | Unit | Status |\n"
        f"|-----------|------:|------|--------|\n"
        f"| Average BSW | **{avg_bsw:.1f}** | % | {bsw_emoji(avg_bsw)} {bsw_flag(avg_bsw)} |\n"
        f"| Avg BOPD | **{avg_bopd:,.1f}** | STB/j | Net oil after deducting water |\n"
        f"| Cumulative water | **{total_water:,.0f}** | BWPD | Total water produced |\n"
        f"| Layer | {layer} | — | Production formation |\n\n"
        f"### Reservoir Analysis\n"
        f"**Water Cut (WCT) Assessment:**\n"
        f"- {'🔴 BSW > 80% indicates **advanced reservoir flooding**. The well may have reached economic limit — workover (water shutoff, plug and perforation) should be evaluated immediately.' if avg_bsw > 80 else '⚠️ BSW is elevated (' + str(avg_bsw) + '%) — monitor monthly trend for acceleration.' if avg_bsw > 50 else '✅ BSW at ' + str(avg_bsw) + '% is within normal operating range for this field.'}\n\n"
        f"### Engineering Recommendations\n"
        f"1. **{'Immediate workover' if avg_bsw > 80 else 'BSW monitoring' if avg_bsw > 50 else 'Routine surveillance'}:** "
        f"{'Conduct cement squeeze or perforation plugback to reduce water entry.' if avg_bsw > 80 else 'Increase BSW measurement frequency to weekly for trend detection.' if avg_bsw > 50 else 'Maintain current production regime; quarterly BSW verification.'}\n"
        f"2. **Water management:** Ensure produced water disposal capacity is adequate for current WCT levels.\n"
        f"3. **Field benchmarking:** {wc} BSW of {avg_bsw:.1f}% vs field average of {sf(summary.get('avg_bsw'), 1):.1f}% — {'above' if avg_bsw > sf(summary.get('avg_bsw'), 1) else 'below'} field average.\n\n"
        f"{SOURCE}"
    )

    # ── 1e. GOR question ─────────────────────────────────────────
    add(
        f"What is the GOR of well {wc}?",
        f"## 📊 Well {wc} — Gas-Oil Ratio (GOR) Analysis\n\n"
        f"> **Executive Summary:** Well **{wc}** ({lib}) has an average GOR of **{gor_note(avg_gor)}**. "
        f"{'GOR data is currently unavailable — acoustic fluid level survey or separator test recommended.' if avg_gor == 0 else 'GOR data is within normal solution GOR range.' if avg_gor < 500 else 'Elevated GOR may indicate gas cap breakthrough or free gas production.'}\n\n"
        f"### GOR Assessment\n"
        f"| Parameter | Value | Unit | Status |\n"
        f"|-----------|------:|------|--------|\n"
        f"| Average GOR | **{gor_note(avg_gor)}** | SCF/STB | {'⚠️ Data unavailable' if avg_gor == 0 else '✅ Normal' if avg_gor < 500 else '🔴 Elevated'} |\n"
        f"| Avg BOPD | **{avg_bopd:,.1f}** | STB/j | Current production rate |\n"
        f"| Total gas | **{total_gas:,.0f}** | MSCF | Cumulative gas produced |\n\n"
        f"### Engineering Recommendations\n"
        f"1. **GOR measurement:** {'Schedule acoustic fluid level and separator test to establish baseline GOR.' if avg_gor == 0 else 'Continue monthly GOR monitoring.' if avg_gor < 500 else 'Investigate gas source — perforation review and pressure build-up test recommended.'}\n"
        f"2. **Reservoir drive:** Integrate GOR data with reservoir pressure to confirm drive mechanism.\n"
        f"3. **Long-term:** GOR trend is a critical indicator — rising GOR signals reservoir depletion or gas cap encroachment.\n\n"
        f"{SOURCE}"
    )

    # ── 1f. Status question ───────────────────────────────────────
    add(
        f"Is well {wc} active or shut-in?",
        f"## 🔬 Well {wc} — Operational Status\n\n"
        f"> **Executive Summary:** Well **{wc}** ({lib}) is currently **{'🔴 SHUT-IN' if is_shut else '✅ ACTIVE'}**. "
        f"{'No oil production is currently recorded for this well.' if is_shut else f'The well is producing at an average of {avg_bopd:,.1f} STB/j.'}\n\n"
        f"### Well Status Summary\n"
        f"| Parameter | Value |\n"
        f"|-----------|-------|\n"
        f"| Well Code | **{wc}** |\n"
        f"| Name | {lib} |\n"
        f"| Status | {'🔴 **Shut-in**' if is_shut else '✅ **Active**'} |\n"
        f"| Layer | {layer} |\n"
        f"| Avg BOPD (historical) | {avg_bopd:,.1f} STB/j |\n"
        f"| Cumulative production | {total_oil:,.0f} STB |\n"
        f"| Average BSW | {avg_bsw:.1f}% |\n\n"
        f"### Engineering Recommendations\n"
        f"1. **{'Reactivation analysis' if is_shut else 'Production optimization'}:** "
        f"{'Evaluate technical and economic feasibility of reactivating {wc} — review last workover report and current reservoir pressure.' if is_shut else f'Optimize {wc} production parameters — choke, tubing size, and artificial lift settings.'}\n"
        f"2. **Surveillance:** {'Include {wc} in next pressure survey program to assess current reservoir conditions.' if is_shut else f'Schedule quarterly well test for {wc} to validate production allocation.'}\n\n"
        f"{SOURCE}"
    )

    # ── 1g. Cumulative production ─────────────────────────────────
    add(
        f"What is the total cumulative oil production of well {wc}?",
        f"## 📊 Well {wc} — Cumulative Production\n\n"
        f"> **Executive Summary:** Well **{wc}** ({lib}) has produced a total of **{total_oil:,.0f} STB** "
        f"of oil over its production life, representing **{pct_field:.1f}%** of the total EZZAOUIA field cumulative production.\n\n"
        f"### Cumulative Production Summary\n"
        f"| Parameter | Value | Unit |\n"
        f"|-----------|------:|------|\n"
        f"| Cumulative oil | **{total_oil:,.0f}** | STB |\n"
        f"| % of field total | **{pct_field:.1f}** | % |\n"
        f"| Cumulative gas | **{total_gas:,.0f}** | MSCF |\n"
        f"| Cumulative water | **{total_water:,.0f}** | BWPD |\n"
        f"| Average BOPD | **{avg_bopd:,.1f}** | STB/j |\n"
        f"| Peak BOPD | **{max_bopd:,.0f}** | STB/j |\n"
        f"| Layer | {layer} | — |\n\n"
        f"### Technical Analysis\n"
        f"- Well **{wc}** contributes **{pct_field:.1f}%** of total field cumulative production of {field_total:,.0f} STB\n"
        f"- Current average rate of {avg_bopd:,.1f} STB/j vs peak of {max_bopd:,.0f} STB/j indicates "
        f"{'significant decline from peak production' if max_bopd > 0 and avg_bopd < max_bopd * 0.5 else 'production near peak capacity'}\n"
        f"- BSW of {avg_bsw:.1f}% — {bsw_flag(avg_bsw)}\n\n"
        f"{SOURCE}"
    )

    # ── 1h. Production hours ──────────────────────────────────────
    add(
        f"How many production hours does well {wc} average per day?",
        f"## 📊 Well {wc} — Production Hours Analysis\n\n"
        f"> **Executive Summary:** Well **{wc}** averages **{avg_ph:.1f} hours/day** of production. "
        f"{'🔴 CRITICAL — well is operating far below optimal capacity (20 h/j target).' if avg_ph < 10 else '⚠️ Below optimal 20 h/j target — investigate downtime causes.' if avg_ph < 18 else '✅ Acceptable utilization rate.'}\n\n"
        f"### Production Hours Summary\n"
        f"| Parameter | Value | Benchmark | Status |\n"
        f"|-----------|------:|-----------|--------|\n"
        f"| Avg prod hours | **{avg_ph:.1f}** | h/j | >20 h/j optimal | {'🔴 Critical' if avg_ph < 10 else '⚠️ Below target' if avg_ph < 18 else '✅ OK'} |\n"
        f"| Utilization rate | **{min(avg_ph/24*100, 100):.0f}** | % | >83% | {'🔴 Low' if avg_ph < 10 else '⚠️ Medium' if avg_ph < 18 else '✅ Good'} |\n"
        f"| Avg BOPD | **{avg_bopd:,.1f}** | STB/j | — | Current rate |\n\n"
        f"### Engineering Recommendations\n"
        f"1. **{'Downtime investigation' if avg_ph < 18 else 'Maintenance optimization'}:** "
        f"{'Conduct root cause analysis of production downtime — review intervention history, mechanical failures, and planned shutdowns.' if avg_ph < 18 else 'Maintain current high utilization; schedule preventive maintenance during planned shutdowns.'}\n"
        f"2. **Uplift potential:** At {avg_ph:.1f} h/j, increasing to 22 h/j could improve production by ~{max(0, (22/avg_ph - 1)*100) if avg_ph > 0 else 0:.0f}%.\n\n"
        f"{SOURCE}"
    )

    # ── 1i. Layer question ────────────────────────────────────────
    add(
        f"What layer does well {wc} produce from?",
        f"## 🔬 Well {wc} — Reservoir Layer Information\n\n"
        f"> **Executive Summary:** Well **{wc}** ({lib}) produces from the **{layer}** formation. "
        f"Production averages {avg_bopd:,.1f} STB/j with a BSW of {avg_bsw:.1f}%.\n\n"
        f"### Well & Reservoir Summary\n"
        f"| Parameter | Value |\n"
        f"|-----------|-------|\n"
        f"| Well code | **{wc}** |\n"
        f"| Well name | {lib} |\n"
        f"| **Production layer** | **{layer}** |\n"
        f"| Status | {'🔴 Shut-in' if is_shut else '✅ Active'} |\n"
        f"| Avg BOPD | {avg_bopd:,.1f} STB/j |\n"
        f"| Avg BSW | {avg_bsw:.1f}% |\n"
        f"| Cumulative oil | {total_oil:,.0f} STB |\n\n"
        f"### Engineering Recommendations\n"
        f"1. **Layer management:** Monitor production performance per formation to optimize recovery from the {layer} reservoir.\n"
        f"2. **Perforation review:** Periodically evaluate perforation intervals in {layer} to maximize sweep efficiency.\n\n"
        f"{SOURCE}"
    )

    # ── 1j. Compare to field average ─────────────────────────────
    field_avg_bopd = sf(summary.get('avg_bopd'), 1)
    field_avg_bsw = sf(summary.get('avg_bsw'), 1)
    add(
        f"Compare well {wc} performance with field average.",
        f"## 📊 Well {wc} vs EZZAOUIA Field Average\n\n"
        f"> **Executive Summary:** Well **{wc}** averages **{avg_bopd:,.1f} STB/j** vs field average of **{field_avg_bopd:,.1f} STB/j** — "
        f"**{'above' if avg_bopd > field_avg_bopd else 'below'} field average by {abs(avg_bopd - field_avg_bopd):,.1f} STB/j**. "
        f"BSW of {avg_bsw:.1f}% vs field average {field_avg_bsw:.1f}% — "
        f"{'higher' if avg_bsw > field_avg_bsw else 'lower'} WCT than average.\n\n"
        f"### Production Comparison\n"
        f"| Indicator | Well {wc} | Field Average | Delta |\n"
        f"|-----------|----------:|---------------:|-------|\n"
        f"| Avg BOPD | **{avg_bopd:,.1f}** STB/j | {field_avg_bopd:,.1f} STB/j | "
        f"{'▲' if avg_bopd > field_avg_bopd else '▼'} {abs(avg_bopd - field_avg_bopd):,.1f} STB/j |\n"
        f"| BSW | **{avg_bsw:.1f}%** | {field_avg_bsw:.1f}% | "
        f"{'▲' if avg_bsw > field_avg_bsw else '▼'} {abs(avg_bsw - field_avg_bsw):.1f}% |\n"
        f"| GOR | **{gor_note(avg_gor)}** | {gor_note(summary.get('avg_gor', 0))} | — |\n"
        f"| Cum. oil | **{total_oil:,.0f}** STB | — | {pct_field:.1f}% of total |\n\n"
        f"### Technical Analysis\n"
        f"- **BOPD:** {wc} is {'a **above-average performer**' if avg_bopd > field_avg_bopd else 'a **below-average producer**'} — "
        f"{'contributing more than typical well share to field production' if avg_bopd > field_avg_bopd else 'optimization measures could improve contribution to field total'}\n"
        f"- **BSW:** {wc} water cut of {avg_bsw:.1f}% is {'higher' if avg_bsw > field_avg_bsw else 'lower'} than field average {field_avg_bsw:.1f}% — "
        f"{'monitor for further increase' if avg_bsw > field_avg_bsw else 'currently in good relative condition'}\n\n"
        f"### Engineering Recommendations\n"
        f"1. **Optimization:** {'Continue current operating regime — this well is performing above average.' if avg_bopd > field_avg_bopd else 'Investigate uplift opportunities — stimulation, artificial lift optimization, or workover.'}\n"
        f"2. **BSW action:** {'Prioritize water management workover.' if avg_bsw > 80 else 'Increase BSW surveillance frequency.' if avg_bsw > field_avg_bsw else 'Maintain current WCT management.'}\n\n"
        f"{SOURCE}"
    )

print(f"  Per-well Q&A generated: {len(dataset)} pairs so far")


# ═══════════════════════════════════════════════════════════════════
# CATEGORY 2 — Global Field KPIs
# ═══════════════════════════════════════════════════════════════════

s = summary
avg_bopd_f = sf(s.get('avg_bopd'), 1)
avg_bsw_f = sf(s.get('avg_bsw'), 2)
avg_gor_f = sf(s.get('avg_gor'), 0)
total_oil_f = si(s.get('total_oil_stbd'))
total_gas_f = sf(s.get('total_gas_mscf'), 0)
total_water_f = sf(s.get('total_water_bwpd'), 0)
avg_ph_f = sf(s.get('avg_prodhours'), 1)
last_date_f = s.get('last_date') or 'N/A'
active_wells = len([w for w in wells if w.closed != 'Y'])
shut_wells = len([w for w in wells if w.closed == 'Y'])

FIELD_KPI_TABLE = (
    f"| Indicator | Value | Unit | Benchmark | Status |\n"
    f"|-----------|------:|------|-----------|--------|\n"
    f"| Average BOPD | **{avg_bopd_f:,.1f}** | STB/j | >50 target | {'✅ Above target' if avg_bopd_f > 50 else '⚠️ Below target'} |\n"
    f"| Field BSW | **{avg_bsw_f:.2f}** | % | <15% OK | {'✅ Normal' if avg_bsw_f < 15 else '⚠️ Elevated' if avg_bsw_f < 80 else '🔴 CRITICAL'} |\n"
    f"| Average GOR | **{gor_note(avg_gor_f)}** | — | >500 alert | {'ℹ️ Data unavailable' if avg_gor_f == 0 else '✅ Normal' if avg_gor_f < 500 else '🔴 Elevated'} |\n"
    f"| Avg Prod Hours | **{avg_ph_f:.1f}** | h/j | >20 optimal | {'✅ Good' if avg_ph_f >= 18 else '⚠️ Below target' if avg_ph_f >= 10 else '🔴 Critical'} |\n"
    f"| Total oil (cumul) | **{total_oil_f:,.0f}** | STB | — | Historical total |\n"
    f"| Total gas | **{total_gas_f:,.0f}** | MSCF | — | Current period |\n"
    f"| Total water | **{total_water_f:,.0f}** | BWPD | — | Current period |\n"
    f"| Active wells | **{active_wells}** | — | — | ✅ Producing |\n"
    f"| Shut-in wells | **{shut_wells}** | — | — | {'🔴' if shut_wells > 0 else '✅'} |\n"
    f"| Last report date | **{last_date_f}** | — | — | ℹ️ |\n"
)

# EN field summary
add(
    "What is the field average BOPD of EZZAOUIA?",
    f"## 📊 EZZAOUIA Field — Global Production KPIs\n\n"
    f"> **Executive Summary:** The EZZAOUIA field (MARETAP S.A., CPF Zarzis) averages **{avg_bopd_f:,.1f} STB/j** of oil. "
    f"Field BSW is **{avg_bsw_f:.2f}%** — {'✅ normal range' if avg_bsw_f < 15 else '⚠️ elevated'}. "
    f"Total cumulative production stands at **{total_oil_f:,.0f} STB**. "
    f"Last reporting date: **{last_date_f}**.\n\n"
    f"### Field Key Performance Indicators\n"
    f"{FIELD_KPI_TABLE}\n"
    f"### Engineering Recommendations\n"
    f"1. **Production target:** {'Field is below 50 STB/j target — evaluate artificial lift optimization and workover candidates.' if avg_bopd_f < 50 else 'Field is meeting production target — focus on sustaining current rates.'}\n"
    f"2. **Water management:** {'BSW is within normal range — maintain current water disposal capacity.' if avg_bsw_f < 15 else 'Elevated BSW — prioritize water shutoff workovers on high-WCT wells.'}\n"
    f"3. **Production hours:** {'Critical low production hours — investigate systematic downtime causes across all wells.' if avg_ph_f < 10 else 'Optimize scheduled maintenance windows to maximize uptime.'}\n\n"
    f"{SOURCE}"
)

# FR field summary
add(
    "Quelle est la production moyenne du champ EZZAOUIA en BOPD?",
    f"## 📊 Champ EZZAOUIA — KPIs de Production Globaux\n\n"
    f"> **Résumé exécutif:** Le champ EZZAOUIA (MARETAP S.A., CPF Zarzis) produit en moyenne **{avg_bopd_f:,.1f} STB/j** d'huile. "
    f"Le BSW du champ est de **{avg_bsw_f:.2f}%** — {'✅ dans la plage normale' if avg_bsw_f < 15 else '⚠️ élevé'}. "
    f"La production cumulée totale s'élève à **{total_oil_f:,.0f} STB**. "
    f"Dernière date de rapport: **{last_date_f}**.\n\n"
    f"### Indicateurs Clés de Performance du Champ\n"
    f"{FIELD_KPI_TABLE}\n"
    f"### Recommandations\n"
    f"1. **Objectif de production:** {'Le champ est en dessous de l objectif de 50 STB/j — évaluer l optimisation de la pompe et les candidats workover.' if avg_bopd_f < 50 else 'Le champ atteint son objectif de production — se concentrer sur la durabilité.'}\n"
    f"2. **Gestion des eaux:** {'Le BSW est dans la plage normale — maintenir la capacité actuelle d élimination des eaux.' if avg_bsw_f < 15 else 'BSW élevé — prioriser les workovers d isolation d eau sur les puits à fort WCT.'}\n\n"
    f"{SOURCE}"
)

# Arabic field summary
add(
    "ما هو متوسط إنتاج حقل عزاوية؟",
    f"## 📊 حقل عزاوية — مؤشرات الإنتاج الرئيسية\n\n"
    f"> **الملخص التنفيذي:** ينتج حقل عزاوية (MARETAP S.A.، CPF جرجيس) بمعدل **{avg_bopd_f:,.1f} STB/j**. "
    f"نسبة الماء BSW هي **{avg_bsw_f:.2f}%**. "
    f"الإنتاج التراكمي الكلي: **{total_oil_f:,.0f} STB**.\n\n"
    f"### مؤشرات الأداء الرئيسية\n"
    f"| المؤشر | القيمة | الوحدة |\n"
    f"|--------|-------:|--------|\n"
    f"| متوسط BOPD | **{avg_bopd_f:,.1f}** | STB/j |\n"
    f"| BSW الحقل | **{avg_bsw_f:.2f}** | % |\n"
    f"| إجمالي النفط التراكمي | **{total_oil_f:,.0f}** | STB |\n"
    f"| الآبار النشطة | **{active_wells}** | — |\n"
    f"| الآبار المغلقة | **{shut_wells}** | — |\n"
    f"| آخر تاريخ تقرير | **{last_date_f}** | — |\n\n"
    f"### التوصيات الهندسية\n"
    f"1. **تحسين الإنتاج:** تقييم فرص تحسين الرفع الاصطناعي وبرنامج workover.\n"
    f"2. **إدارة المياه:** {'معدل BSW طبيعي — الحفاظ على الطاقة الحالية.' if avg_bsw_f < 15 else 'BSW مرتفع — أولوية لعمليات عزل المياه.'}\n\n"
    f"{SOURCE}"
)

# More field KPI Q&A
add(
    "What is the total cumulative oil production of EZZAOUIA field?",
    f"## 📊 EZZAOUIA Field — Cumulative Production\n\n"
    f"> **Executive Summary:** The EZZAOUIA field has produced a total of **{total_oil_f:,.0f} STB** of oil over its operational history (1994–2025). "
    f"Current field average is **{avg_bopd_f:,.1f} STB/j** with **{active_wells}** active wells.\n\n"
    f"### Cumulative Production Summary\n"
    f"| Parameter | Value | Unit |\n"
    f"|-----------|------:|------|\n"
    f"| Cumulative oil | **{total_oil_f:,.0f}** | STB |\n"
    f"| Cumulative gas | **{total_gas_f:,.0f}** | MSCF |\n"
    f"| Cumulative water | **{total_water_f:,.0f}** | BWPD |\n"
    f"| Active wells | **{active_wells}** | — |\n"
    f"| Last report date | **{last_date_f}** | — |\n\n"
    f"### Engineering Recommendations\n"
    f"1. **Reserve estimation:** Update reservoir simulation model with latest cumulative production data to refine remaining reserve estimates.\n"
    f"2. **Recovery factor:** Benchmark cumulative production against STOIIP to calculate current recovery factor and identify EOR potential.\n\n"
    f"{SOURCE}"
)

well_list_md = ""
if len(wells) <= 20:
    well_lines = []
    for w in wells:
        well_state = "Shut-in" if w.closed == 'Y' else "Active"
        well_lines.append(f"- **{w.well_code}** ({w.libelle}) - {well_state}")
    well_list_md = "### Well List\n" + "\n".join(well_lines) + "\n"

add(
    "How many active wells does EZZAOUIA field have?",
    f"## 📊 EZZAOUIA Field — Well Inventory\n\n"
    f"> **Executive Summary:** The EZZAOUIA field has **{len(wells)} total wells** — "
    f"**{active_wells} active** and **{shut_wells} shut-in**. "
    f"Active wells average **{avg_bopd_f:,.1f} STB/j** collectively.\n\n"
    f"### Well Inventory\n"
    f"| Category | Count | Notes |\n"
    f"|----------|------:|-------|\n"
    f"| Total wells | **{len(wells)}** | All drilled wells |\n"
    f"| Active wells | **{active_wells}** | Currently producing |\n"
    f"| Shut-in wells | **{shut_wells}** | Not producing |\n"
    f"| Field avg BOPD | **{avg_bopd_f:,.1f} STB/j** | Current production rate |\n"
    f"| Last report date | **{last_date_f}** | — |\n\n"
    f"{well_list_md}"
    f"\n### Engineering Recommendations\n"
    f"1. **Shut-in well evaluation:** {'Review all ' + str(shut_wells) + ' shut-in wells for reactivation potential — prioritize by estimated remaining reserves.' if shut_wells > 0 else 'All wells are active — excellent field utilization.'}\n"
    f"2. **Well spacing:** Evaluate infill drilling potential based on current drainage area analysis.\n\n"
    f"{SOURCE}"
)

add(
    "Combien de puits actifs le champ EZZAOUIA possède-t-il?",
    f"## 📊 Champ EZZAOUIA — Inventaire des Puits\n\n"
    f"> **Résumé exécutif:** Le champ EZZAOUIA compte **{len(wells)} puits au total** — "
    f"**{active_wells} actifs** et **{shut_wells} fermés**.\n\n"
    f"### Inventaire des Puits\n"
    f"| Catégorie | Nombre |\n"
    f"|-----------|-------:|\n"
    f"| Total puits | **{len(wells)}** |\n"
    f"| Puits actifs | **{active_wells}** |\n"
    f"| Puits fermés | **{shut_wells}** |\n"
    f"| BOPD moyen champ | **{avg_bopd_f:,.1f} STB/j** |\n\n"
    f"### Recommandations\n"
    f"1. **Puits fermés:** {'Analyser les ' + str(shut_wells) + ' puits fermés pour identifier ceux pouvant être remis en production.' if shut_wells > 0 else 'Tous les puits sont actifs — excellente utilisation du champ.'}\n\n"
    f"{SOURCE}"
)

add(
    "What is the last production date for EZZAOUIA field?",
    f"## 📊 EZZAOUIA Field — Latest Production Data\n\n"
    f"> **Executive Summary:** The most recent production data in the EZZAOUIA DWH is dated **{last_date_f}**. "
    f"Field average BOPD on last reporting date: **{avg_bopd_f:,.1f} STB/j**.\n\n"
    f"### Latest Production Summary\n"
    f"| Parameter | Value |\n"
    f"|-----------|-------|\n"
    f"| **Last report date** | **{last_date_f}** |\n"
    f"| Field avg BOPD | {avg_bopd_f:,.1f} STB/j |\n"
    f"| Field BSW | {avg_bsw_f:.2f}% |\n"
    f"| Active wells | {active_wells} |\n\n"
    f"{SOURCE}"
)

add(
    "What is the total water production BWPD of the EZZAOUIA field?",
    f"## 📊 EZZAOUIA Field — Water Production Analysis\n\n"
    f"> **Executive Summary:** The EZZAOUIA field is currently producing **{total_water_f:,.0f} BWPD** of water. "
    f"Field BSW stands at **{avg_bsw_f:.2f}%** — {'✅ normal' if avg_bsw_f < 15 else '⚠️ elevated — water management action required'}.\n\n"
    f"### Water Production Summary\n"
    f"| Parameter | Value | Unit | Status |\n"
    f"|-----------|------:|------|--------|\n"
    f"| Total water (BWPD) | **{total_water_f:,.0f}** | BWPD | Current period |\n"
    f"| Field BSW | **{avg_bsw_f:.2f}** | % | {'✅ Normal' if avg_bsw_f < 15 else '⚠️ Elevated'} |\n"
    f"| Avg oil BOPD | **{avg_bopd_f:,.1f}** | STB/j | Net oil |\n\n"
    f"### Engineering Recommendations\n"
    f"1. **Water disposal:** Ensure produced water treatment and disposal system capacity is adequate for {total_water_f:,.0f} BWPD.\n"
    f"2. **WCT management:** Identify highest BSW wells and prioritize for water shutoff workover.\n\n"
    f"{SOURCE}"
)

add(
    "What is the total gas production MSCF of the EZZAOUIA field?",
    f"## 📊 EZZAOUIA Field — Gas Production\n\n"
    f"> **Executive Summary:** The EZZAOUIA field is currently producing **{total_gas_f:,.0f} MSCF** of gas. "
    f"Average GOR is {gor_note(avg_gor_f)}.\n\n"
    f"### Gas Production Summary\n"
    f"| Parameter | Value | Unit |\n"
    f"|-----------|------:|------|\n"
    f"| Total gas | **{total_gas_f:,.0f}** | MSCF |\n"
    f"| Average GOR | **{gor_note(avg_gor_f)}** | SCF/STB |\n"
    f"| Average BOPD | **{avg_bopd_f:,.1f}** | STB/j |\n\n"
    f"### Engineering Recommendations\n"
    f"1. **Gas utilization:** Evaluate gas monetization options — fuel use, compression, or flare minimization.\n"
    f"2. **GOR monitoring:** {'Establish GOR measurement program across all wells.' if avg_gor_f == 0 else 'Monitor GOR trend for signs of gas cap breakthrough.'}\n\n"
    f"{SOURCE}"
)

print(f"  After field KPIs: {len(dataset)} pairs")


# ═══════════════════════════════════════════════════════════════════
# CATEGORY 3 — Well Rankings
# ═══════════════════════════════════════════════════════════════════

def make_ranking_table(producers, limit=None):
    rows = producers[:limit] if limit else producers
    header = "| # | Well | Avg BOPD | Cumulative (STB) | BSW% | Status |\n|:-:|------|----------:|-----------------:|-----:|--------|\n"
    body = ""
    for i, w in enumerate(rows, 1):
        bsw_v = sf(w.get('avg_bsw'), 1)
        bopd_v = sf(w.get('avg_bopd'), 1)
        tot_v = si(w.get('total_oil'))
        status_icon = "🔴 Critical WCT" if bsw_v > 80 else "⚠️ High WCT" if bsw_v > 50 else "✅ Good"
        body += f"| {i} | **{w['well_code']}** | **{bopd_v:,.1f}** | {tot_v:,.0f} | {bsw_v:.1f}% | {status_icon} |\n"
    return header + body


# Top 5
top5 = top_all[:5]
add(
    "What are the top 5 producing wells by BOPD?",
    f"## 🛢️ Top 5 Producing Wells — EZZAOUIA Field\n\n"
    f"> **Executive Summary:** The top 5 wells account for the majority of field production. "
    f"Leading producer is **{top5[0]['well_code']}** with **{sf(top5[0].get('avg_bopd'), 1):,.1f} STB/j**. "
    f"{'Critical BSW alert on ' + ', '.join(w['well_code'] for w in top5 if sf(w.get('avg_bsw'), 1) > 80) + '.' if any(sf(w.get('avg_bsw'), 1) > 80 for w in top5) else 'All top producers have acceptable water cut.'}\n\n"
    f"### Production Data\n"
    f"{make_ranking_table(top5)}\n"
    f"### Technical Analysis\n"
    f"**Field Performance:**\n"
    + "\n".join(
        f"- **{w['well_code']}** averages {sf(w.get('avg_bopd'), 1):,.1f} STB/j, cumulative {si(w.get('total_oil')):,.0f} STB"
        for w in top5
    ) + "\n\n"
    f"**Critical Alerts:**\n"
    + (
        "\n".join(
            f"- 🔴 **{w['well_code']}**: BSW at {sf(w.get('avg_bsw'), 1):.1f}% — immediate workover assessment required"
            for w in top5 if sf(w.get('avg_bsw'), 1) > 80
        ) or "- ✅ No critical BSW alerts for top 5 producers"
    ) + "\n\n"
    f"### Engineering Recommendations\n"
    f"1. **Protect top producers:** Prioritize maintenance and surveillance on {top5[0]['well_code']} and {top5[1]['well_code'] if len(top5) > 1 else top5[0]['well_code']} to sustain production.\n"
    f"2. **BSW management:** Focus water shutoff workover on high-WCT top producers to improve net oil rate.\n"
    f"3. **Field optimization:** Optimize artificial lift on top producers to maximize utilization.\n\n"
    f"{SOURCE}"
)

add(
    "Quels sont les 5 meilleurs puits producteurs par BOPD?",
    f"## 🛢️ Top 5 Puits Producteurs — Champ EZZAOUIA\n\n"
    f"> **Résumé exécutif:** Les 5 meilleurs puits représentent la majorité de la production du champ. "
    f"Le puits leader est **{top5[0]['well_code']}** avec **{sf(top5[0].get('avg_bopd'), 1):,.1f} STB/j**.\n\n"
    f"### Données de Production\n"
    f"{make_ranking_table(top5)}\n"
    f"### Recommandations\n"
    f"1. **Protéger les top producteurs:** Prioriser la maintenance et la surveillance sur {top5[0]['well_code']}.\n"
    f"2. **Gestion BSW:** Cibler les workovers d isolation d eau sur les puits à fort WCT.\n\n"
    f"{SOURCE}"
)

# Top 3 by cumulative
top3_cum = sorted(top_all, key=lambda x: si(x.get('total_oil')), reverse=True)[:3]
add(
    "What are the top 3 wells by cumulative production?",
    f"## 🛢️ Top 3 Wells by Cumulative Production — EZZAOUIA Field\n\n"
    f"> **Executive Summary:** The three highest cumulative producers are "
    f"**{top3_cum[0]['well_code']}** ({si(top3_cum[0].get('total_oil')):,.0f} STB), "
    f"**{top3_cum[1]['well_code'] if len(top3_cum) > 1 else 'N/A'}** "
    f"({si(top3_cum[1].get('total_oil') if len(top3_cum) > 1 else 0):,.0f} STB), and "
    f"**{top3_cum[2]['well_code'] if len(top3_cum) > 2 else 'N/A'}** "
    f"({si(top3_cum[2].get('total_oil') if len(top3_cum) > 2 else 0):,.0f} STB).\n\n"
    f"### Cumulative Production Ranking\n"
    f"| # | Well | Cumulative (STB) | % of Field | Avg BOPD | BSW% |\n"
    f"|:-:|------|----------------:|----------:|----------:|-----:|\n"
    + "\n".join(
        f"| {i+1} | **{w['well_code']}** | **{si(w.get('total_oil')):,.0f}** | "
        f"{(si(w.get('total_oil')) / total_oil_f * 100) if total_oil_f > 0 else 0:.1f}% | "
        f"{sf(w.get('avg_bopd'), 1):,.1f} | {sf(w.get('avg_bsw'), 1):.1f}% |"
        for i, w in enumerate(top3_cum)
    ) + "\n\n"
    f"### Engineering Recommendations\n"
    f"1. **Reserve management:** Top 3 producers have contributed disproportionately to field reserves — assess depletion rates.\n"
    f"2. **Infill drilling:** High cumulative producers may be surrounded by undrained areas — evaluate infill well locations.\n\n"
    f"{SOURCE}"
)

# Highest BSW well
if top_all:
    sorted_by_bsw = sorted(top_all, key=lambda x: sf(x.get('avg_bsw'), 1), reverse=True)
    worst_bsw = sorted_by_bsw[0]
    add(
        "Which well has the highest BSW?",
        f"## 📊 Highest BSW Well — EZZAOUIA Field Water Cut Analysis\n\n"
        f"> **Executive Summary:** Well **{worst_bsw['well_code']}** has the highest BSW in the field at "
        f"**{sf(worst_bsw.get('avg_bsw'), 1):.1f}%** — {bsw_flag(worst_bsw.get('avg_bsw'))}. "
        f"Immediate workover evaluation is {'**required**' if sf(worst_bsw.get('avg_bsw'), 1) > 80 else 'recommended'}.\n\n"
        f"### BSW Ranking (Top 5 Highest)\n"
        f"| # | Well | BSW% | Avg BOPD | Risk |\n"
        f"|:-:|------|-----:|----------:|------|\n"
        + "\n".join(
            f"| {i+1} | **{w['well_code']}** | **{sf(w.get('avg_bsw'), 1):.1f}%** | {sf(w.get('avg_bopd'), 1):,.1f} STB/j | {bsw_flag(w.get('avg_bsw'))} |"
            for i, w in enumerate(sorted_by_bsw[:5])
        ) + "\n\n"
        f"### Engineering Recommendations\n"
        f"1. **{worst_bsw['well_code']} — {'Immediate workover' if sf(worst_bsw.get('avg_bsw'), 1) > 80 else 'Monitoring'}:** "
        f"{'Conduct cement squeeze or perforation plugback to reduce water influx.' if sf(worst_bsw.get('avg_bsw'), 1) > 80 else 'Increase BSW measurement frequency and monitor trend.'}\n"
        f"2. **Field-wide:** Review water injection program (if applicable) — high BSW may indicate sweep inefficiency.\n"
        f"3. **Economic limit:** Evaluate whether high-BSW wells have reached economic water cut limit.\n\n"
        f"{SOURCE}"
    )

    # Shut-in wells
    shut_list = [w for w in wells if w.closed == 'Y']
    if shut_list:
        add(
            "Which wells are shut-in?",
            f"## 📊 Shut-in Wells — EZZAOUIA Field\n\n"
            f"> **Executive Summary:** **{len(shut_list)} wells** are currently shut-in out of {len(wells)} total. "
            f"Reactivating these wells could significantly increase field production.\n\n"
            f"### Shut-in Well List\n"
            f"| Well | Name | Layer | Historical Avg BOPD | Cum. Oil |\n"
            f"|------|------|-------|--------------------:|---------:|\n"
            + "\n".join(
                f"| **{w.well_code}** | {w.libelle} | {w.layer} | "
                f"{sf(well_kpis.get(w.well_key, {}).get('avg_bopd'), 1):,.1f} STB/j | "
                f"{si(well_kpis.get(w.well_key, {}).get('total_oil')):,.0f} STB |"
                for w in shut_list
            ) + "\n\n"
            f"### Engineering Recommendations\n"
            f"1. **Reactivation study:** Prioritize shut-in well evaluation by historical production rate — highest producers first.\n"
            f"2. **Reservoir pressure:** Conduct pressure surveys on shut-in wells to assess current reservoir energy.\n"
            f"3. **Workover planning:** Budget workover program for most promising shut-in wells in next 12 months.\n\n"
            f"{SOURCE}"
        )

    # Worst performer
    active_producers = [w for w in top_all if sf(w.get('avg_bopd'), 1) > 0]
    if active_producers:
        worst = active_producers[-1]
        add(
            "What is the worst performing well?",
            f"## 📊 Lowest Performing Well — EZZAOUIA Field\n\n"
            f"> **Executive Summary:** The lowest-producing active well is **{worst['well_code']}** with only "
            f"**{sf(worst.get('avg_bopd'), 1):,.1f} STB/j** average production and BSW of {sf(worst.get('avg_bsw'), 1):.1f}%.\n\n"
            f"### Bottom 5 Performers\n"
            f"| # | Well | Avg BOPD | Cumulative (STB) | BSW% |\n"
            f"|:-:|------|----------:|-----------------:|-----:|\n"
            + "\n".join(
                f"| {i+1} | **{w['well_code']}** | **{sf(w.get('avg_bopd'), 1):,.1f}** | {si(w.get('total_oil')):,.0f} | {sf(w.get('avg_bsw'), 1):.1f}% |"
                for i, w in enumerate(reversed(active_producers[-5:]))
            ) + "\n\n"
            f"### Engineering Recommendations\n"
            f"1. **{worst['well_code']} — diagnostic:** Run production log and pressure build-up test to identify cause of low productivity.\n"
            f"2. **Stimulation:** Evaluate matrix acidization or hydraulic fracturing to improve productivity index.\n"
            f"3. **Economic evaluation:** Assess if low producers are above economic threshold — consider shut-in if below.\n\n"
            f"{SOURCE}"
        )

print(f"  After rankings: {len(dataset)} pairs")


# ═══════════════════════════════════════════════════════════════════
# CATEGORY 4 — Yearly Production (2015–2025)
# ═══════════════════════════════════════════════════════════════════

years = list(range(2015, 2026))
year_summaries = {}
for yr in years:
    ys = get_field_production_summary(year=yr)
    if ys and ys.get('total_oil_stbd', 0) > 0:
        year_summaries[yr] = ys

for yr, ys in year_summaries.items():
    bopd_yr = sf(ys.get('avg_bopd'), 1)
    total_yr = si(ys.get('total_oil_stbd'))
    bsw_yr = sf(ys.get('avg_bsw'), 2)
    gor_yr = sf(ys.get('avg_gor'), 0)

    # EN
    add(
        f"What was the total oil production in {yr}?",
        f"## 📊 EZZAOUIA Field — {yr} Annual Production\n\n"
        f"> **Executive Summary:** In **{yr}**, the EZZAOUIA field produced a total of **{total_yr:,.0f} STB** of oil, "
        f"averaging **{bopd_yr:,.1f} STB/j**. Field BSW was **{bsw_yr:.2f}%**.\n\n"
        f"### {yr} Production Summary\n"
        f"| Parameter | Value | Unit |\n"
        f"|-----------|------:|------|\n"
        f"| Total oil | **{total_yr:,.0f}** | STB |\n"
        f"| Average BOPD | **{bopd_yr:,.1f}** | STB/j |\n"
        f"| Field BSW | **{bsw_yr:.2f}** | % |\n"
        f"| Average GOR | **{gor_note(gor_yr)}** | — |\n\n"
        f"### Engineering Recommendations\n"
        f"1. **Year performance:** {yr} production of {total_yr:,.0f} STB vs current cumulative of {total_oil_f:,.0f} STB — update decline curve analysis.\n"
        f"2. **BSW trend:** {yr} BSW of {bsw_yr:.2f}% — {'below current level, indicating increasing water production trend.' if bsw_yr < avg_bsw_f else 'above current level, indicating improvement since then.'}\n\n"
        f"{SOURCE}"
    )

    # FR
    add(
        f"Quelle était la production totale du champ en {yr}?",
        f"## 📊 Champ EZZAOUIA — Production Annuelle {yr}\n\n"
        f"> **Résumé exécutif:** En **{yr}**, le champ EZZAOUIA a produit **{total_yr:,.0f} STB** d'huile, "
        f"soit une moyenne de **{bopd_yr:,.1f} STB/j**. Le BSW du champ était de **{bsw_yr:.2f}%**.\n\n"
        f"### Résumé de Production {yr}\n"
        f"| Paramètre | Valeur | Unité |\n"
        f"|-----------|-------:|-------|\n"
        f"| Total huile | **{total_yr:,.0f}** | STB |\n"
        f"| BOPD moyen | **{bopd_yr:,.1f}** | STB/j |\n"
        f"| BSW champ | **{bsw_yr:.2f}** | % |\n\n"
        f"{SOURCE}"
    )

# Year comparison pairs
year_list = list(year_summaries.keys())
for i in range(len(year_list) - 1):
    y1, y2 = year_list[i], year_list[i + 1]
    ys1, ys2 = year_summaries[y1], year_summaries[y2]
    bopd1, bopd2 = sf(ys1.get('avg_bopd'), 1), sf(ys2.get('avg_bopd'), 1)
    tot1, tot2 = si(ys1.get('total_oil_stbd')), si(ys2.get('total_oil_stbd'))
    delta_bopd = bopd2 - bopd1
    delta_pct = (delta_bopd / bopd1 * 100) if bopd1 > 0 else 0

    add(
        f"Compare production between {y1} and {y2}.",
        f"## 📊 Production Comparison: {y1} vs {y2} — EZZAOUIA Field\n\n"
        f"> **Executive Summary:** Field average BOPD {'increased' if delta_bopd > 0 else 'decreased'} from "
        f"**{bopd1:,.1f} STB/j** ({y1}) to **{bopd2:,.1f} STB/j** ({y2}), a "
        f"**{'▲' if delta_bopd > 0 else '▼'} {abs(delta_pct):.1f}% {'increase' if delta_bopd > 0 else 'decrease'}**.\n\n"
        f"### Year-over-Year Comparison\n"
        f"| Parameter | {y1} | {y2} | Delta |\n"
        f"|-----------|-----:|-----:|-------|\n"
        f"| Avg BOPD | **{bopd1:,.1f}** | **{bopd2:,.1f}** | {'▲' if delta_bopd > 0 else '▼'} {abs(delta_pct):.1f}% |\n"
        f"| Total oil | **{tot1:,.0f}** | **{tot2:,.0f}** | {'▲' if tot2 > tot1 else '▼'} {abs(tot2 - tot1):,.0f} STB |\n"
        f"| BSW | **{sf(ys1.get('avg_bsw'), 2):.2f}%** | **{sf(ys2.get('avg_bsw'), 2):.2f}%** | {'▲' if sf(ys2.get('avg_bsw'), 2) > sf(ys1.get('avg_bsw'), 2) else '▼'} |\n\n"
        f"### Technical Analysis\n"
        f"- Production {'growth' if delta_bopd > 0 else 'decline'} of {abs(delta_pct):.1f}% from {y1} to {y2}\n"
        f"- {'Positive trend — field optimization or new well contributions.' if delta_bopd > 0 else 'Decline — natural reservoir depletion, investigate with decline curve analysis.'}\n"
        f"- BSW {'increased' if sf(ys2.get('avg_bsw'), 2) > sf(ys1.get('avg_bsw'), 2) else 'decreased'} indicating {'advancing water production — water management priority.' if sf(ys2.get('avg_bsw'), 2) > sf(ys1.get('avg_bsw'), 2) else 'improving water control.'}\n\n"
        f"### Engineering Recommendations\n"
        f"1. **Decline analysis:** {'Investigate and reverse production decline with workover program.' if delta_bopd < 0 else 'Sustain production growth through continued optimization.'}\n"
        f"2. **BSW trend:** {'Accelerating water cut requires immediate intervention.' if sf(ys2.get('avg_bsw'), 2) > sf(ys1.get('avg_bsw'), 2) + 5 else 'Monitor BSW trend and plan accordingly.'}\n\n"
        f"{SOURCE}"
    )

print(f"  After yearly analysis: {len(dataset)} pairs")


# ═══════════════════════════════════════════════════════════════════
# CATEGORY 5 — Reservoir Analysis
# ═══════════════════════════════════════════════════════════════════

critical_bsw_wells = [w for w in top_all if sf(w.get('avg_bsw'), 1) > 80]
high_bsw_wells = [w for w in top_all if sf(w.get('avg_bsw'), 1) > 50]
sorted_bsw = sorted(top_all, key=lambda x: sf(x.get('avg_bsw'), 1), reverse=True)

add(
    "Analyze the water cut trend of EZZAOUIA field.",
    f"## 📊 EZZAOUIA Field — Water Cut (WCT/BSW) Analysis\n\n"
    f"> **Executive Summary:** Field average BSW is **{avg_bsw_f:.2f}%** — {'✅ within normal operating range' if avg_bsw_f < 15 else '⚠️ elevated — water management action required' if avg_bsw_f < 80 else '🔴 CRITICAL — advanced reservoir flooding'}. "
    f"**{len(critical_bsw_wells)}** wells have critical BSW (>80%) and **{len(high_bsw_wells)}** have elevated BSW (>50%).\n\n"
    f"### Field Key Performance Indicators\n"
    f"| Indicator | Value | Unit | Benchmark | Status |\n"
    f"|-----------|------:|------|-----------|--------|\n"
    f"| Field average BSW | **{avg_bsw_f:.2f}** | % | <15% normal | {'✅ Normal' if avg_bsw_f < 15 else '⚠️ Elevated' if avg_bsw_f < 80 else '🔴 CRITICAL'} |\n"
    f"| Critical BSW wells (>80%) | **{len(critical_bsw_wells)}** | wells | 0 target | {'✅ None' if len(critical_bsw_wells) == 0 else '🔴 ' + str(len(critical_bsw_wells)) + ' wells'} |\n"
    f"| High BSW wells (>50%) | **{len(high_bsw_wells)}** | wells | 0 target | {'✅ None' if len(high_bsw_wells) == 0 else '⚠️ ' + str(len(high_bsw_wells)) + ' wells'} |\n\n"
    f"### BSW Analysis by Well (sorted highest to lowest)\n"
    f"| Well | BSW% | BOPD | Risk Level |\n"
    f"|------|-----:|-----:|------------|\n"
    + "\n".join(
        f"| **{w['well_code']}** | **{sf(w.get('avg_bsw'), 1):.1f}%** | {sf(w.get('avg_bopd'), 1):,.1f} | {bsw_flag(w.get('avg_bsw'))} |"
        for w in sorted_bsw[:10]
    ) + "\n\n"
    f"### Reservoir Analysis\n"
    f"**Water Cut (WCT) Assessment:**\n"
    f"- {'🔴 CRITICAL: ' + str(len(critical_bsw_wells)) + ' wells have BSW > 80% indicating advanced reservoir flooding. Immediate workover assessment required.' if critical_bsw_wells else '✅ No wells with critical BSW > 80%'}\n"
    f"- Field average BSW of {avg_bsw_f:.2f}% {'is within normal range — natural water influx manageable' if avg_bsw_f < 15 else 'indicates significant water production — review water injection or aquifer support'}\n\n"
    f"**GOR Assessment:**\n"
    f"- {gor_note(avg_gor_f)} — {'GOR data unavailable for last reporting period — recommend acoustic fluid level survey' if avg_gor_f == 0 else 'GOR data within expected range'}\n\n"
    f"### Engineering Recommendations\n"
    f"1. **Water Management:** {'Priority workover for ' + ', '.join(w['well_code'] for w in critical_bsw_wells) + ' — cement squeeze or plugback required.' if critical_bsw_wells else 'Continue current water management strategy — BSW within acceptable range.'}\n"
    f"2. **Production Optimization:** Maximize oil rate on low-BSW wells to offset high-WCT production.\n"
    f"3. **Surveillance:** Monthly BSW measurement mandatory for all wells; weekly for BSW > 50% wells.\n\n"
    f"{SOURCE}"
)

add(
    "Analyze GOR evolution in EZZAOUIA field.",
    f"## 📊 EZZAOUIA Field — GOR (Gas-Oil Ratio) Analysis\n\n"
    f"> **Executive Summary:** Field average GOR is **{gor_note(avg_gor_f)}**. "
    f"{'GOR data is currently unavailable for the last reporting period — this is a critical data gap requiring immediate field measurement.' if avg_gor_f == 0 else 'GOR is within normal solution GOR range for this reservoir type.' if avg_gor_f < 500 else 'Elevated GOR indicates potential gas cap breakthrough or free gas production.'}\n\n"
    f"### Field GOR Assessment\n"
    f"| Parameter | Value | Benchmark | Status |\n"
    f"|-----------|------:|-----------|--------|\n"
    f"| Field avg GOR | **{gor_note(avg_gor_f)}** | <500 normal | {'ℹ️ Data unavailable' if avg_gor_f == 0 else '✅ Normal' if avg_gor_f < 500 else '🔴 Elevated'} |\n"
    f"| Field avg BOPD | **{avg_bopd_f:,.1f}** | STB/j | — | Current rate |\n"
    f"| Total gas | **{total_gas_f:,.0f}** | MSCF | — | Current period |\n\n"
    f"### GOR Assessment\n"
    f"- {'GOR = 0 or data unavailable: This likely indicates missing measurements rather than zero gas production. Schedule separator test and acoustic fluid level measurement for all wells.' if avg_gor_f == 0 else 'GOR trend analysis: rising GOR indicates gas cap expansion or solution gas liberation as reservoir pressure declines below bubble point.'}\n\n"
    f"### Engineering Recommendations\n"
    f"1. **GOR measurement:** {'Implement routine GOR measurement program — at minimum monthly separator tests.' if avg_gor_f == 0 else 'Continue monthly GOR monitoring — track trend for early detection of gas breakthrough.'}\n"
    f"2. **Reservoir pressure:** Conduct pressure build-up tests to correlate GOR with reservoir pressure depletion.\n"
    f"3. **Gas management:** Evaluate gas handling capacity at CPF Zarzis for expected gas volumes.\n\n"
    f"{SOURCE}"
)

add(
    "Which wells show signs of water breakthrough?",
    f"## 📊 EZZAOUIA Field — Water Breakthrough Analysis\n\n"
    f"> **Executive Summary:** **{len(high_bsw_wells)} wells** show signs of water breakthrough (BSW > 50%). "
    f"{'🔴 ' + str(len(critical_bsw_wells)) + ' wells have critical water breakthrough (BSW > 80%).' if critical_bsw_wells else 'No wells have reached critical BSW > 80%.'}\n\n"
    f"### Wells with Water Breakthrough Signs\n"
    f"| Well | BSW% | BOPD | Breakthrough Severity |\n"
    f"|------|-----:|-----:|------------------------|\n"
    + (
        "\n".join(
            f"| **{w['well_code']}** | **{sf(w.get('avg_bsw'), 1):.1f}%** | {sf(w.get('avg_bopd'), 1):,.1f} | {bsw_flag(w.get('avg_bsw'))} |"
            for w in sorted_bsw if sf(w.get('avg_bsw'), 1) > 30
        ) or "| — | No significant water breakthrough detected | — | ✅ |"
    ) + "\n\n"
    f"### Engineering Recommendations\n"
    f"1. **Critical wells:** {'Immediate workover for BSW > 80% wells — cement squeeze or perforation plugback.' if critical_bsw_wells else 'Monitor all wells with BSW > 50% on monthly basis.'}\n"
    f"2. **Tracer test:** Consider inter-well tracer test to identify water source and pathways.\n"
    f"3. **Conformance:** Evaluate conformance improvement treatments — gel injection or profile modification.\n\n"
    f"{SOURCE}"
)

add(
    "What is the production decline rate of EZZAOUIA field?",
    f"## 📊 EZZAOUIA Field — Production Decline Analysis\n\n"
    f"> **Executive Summary:** Based on available data, the EZZAOUIA field currently averages **{avg_bopd_f:,.1f} STB/j**. "
    f"A comprehensive decline curve analysis requires multi-year production history from the DWH.\n\n"
    f"### Current Production Status\n"
    f"| Parameter | Value | Unit | Status |\n"
    f"|-----------|------:|------|--------|\n"
    f"| Current avg BOPD | **{avg_bopd_f:,.1f}** | STB/j | {'✅ Above target' if avg_bopd_f > 50 else '⚠️ Below 50 STB/j target'} |\n"
    f"| Cumulative oil | **{total_oil_f:,.0f}** | STB | Historical total |\n"
    f"| Active wells | **{active_wells}** | — | Currently producing |\n"
    f"| Shut-in wells | **{shut_wells}** | — | Not producing |\n\n"
    + (
        "### Year-on-Year Production Trend\n"
        "| Year | Avg BOPD | Total Oil (STB) | BSW% |\n"
        "|-----:|---------:|----------------:|-----:|\n"
        + "\n".join(
            f"| {yr} | **{sf(ys.get('avg_bopd'), 1):,.1f}** | {si(ys.get('total_oil_stbd')):,.0f} | {sf(ys.get('avg_bsw'), 2):.2f}% |"
            for yr, ys in sorted(year_summaries.items())
        ) + "\n\n"
        if year_summaries else ""
    )
    + f"### Engineering Recommendations\n"
    f"1. **Decline curve analysis:** Fit Arps decline model (exponential, hyperbolic) to historical BOPD data to project future rates.\n"
    f"2. **Type curve matching:** Match field production to analogous reservoirs to estimate ultimate recovery.\n"
    f"3. **Infill drilling:** If decline rate is high, evaluate infill well locations to supplement declining producers.\n"
    f"4. **EOR screening:** Assess EOR potential (water flood, chemical EOR) to arrest decline.\n\n"
    f"{SOURCE}"
)

add(
    "Quelle est l'analyse de déclin de production du champ EZZAOUIA?",
    f"## 📊 Champ EZZAOUIA — Analyse du Déclin de Production\n\n"
    f"> **Résumé exécutif:** Le champ EZZAOUIA produit actuellement **{avg_bopd_f:,.1f} STB/j** en moyenne. "
    f"Une analyse complète de la courbe de déclin nécessite l'historique de production complet de la base DWH.\n\n"
    f"### Statut de Production Actuel\n"
    f"| Paramètre | Valeur | Unité |\n"
    f"|-----------|-------:|-------|\n"
    f"| BOPD moyen actuel | **{avg_bopd_f:,.1f}** | STB/j |\n"
    f"| Production cumulée | **{total_oil_f:,.0f}** | STB |\n"
    f"| Puits actifs | **{active_wells}** | — |\n\n"
    f"### Recommandations\n"
    f"1. **Analyse de déclin:** Appliquer le modèle de déclin Arps (exponentiel, hyperbolique) sur l'historique de production.\n"
    f"2. **EOR:** Évaluer le potentiel EOR pour inverser le déclin — injection d'eau, polymères ou CO2.\n\n"
    f"{SOURCE}"
)

add(
    "Which wells need workover intervention?",
    f"## 🛢️ Workover Intervention Candidates — EZZAOUIA Field\n\n"
    f"> **Executive Summary:** Based on current KPIs, **{len(critical_bsw_wells) + len(shut_list if 'shut_list' in dir() else [])}** wells require priority workover evaluation. "
    f"Main issues: high BSW water cut and shut-in reactivation.\n\n"
    f"### Priority 1 — Critical BSW (>80%)\n"
    + (
        "| Well | BSW% | BOPD | Recommended Action |\n"
        "|------|-----:|-----:|--------------------|\n"
        + "\n".join(
            f"| **{w['well_code']}** | 🔴 **{sf(w.get('avg_bsw'), 1):.1f}%** | {sf(w.get('avg_bopd'), 1):,.1f} | Cement squeeze / perforation plugback |"
            for w in critical_bsw_wells
        )
        if critical_bsw_wells else "| — | No critical BSW wells currently | — | — |"
    ) + "\n\n"
    f"### Priority 2 — Shut-in Reactivation\n"
    + (
        "| Well | Layer | Historical BOPD | Recommended Action |\n"
        "|------|-------|----------------:|--------------------|\n"
        + "\n".join(
            f"| **{w.well_code}** | {w.layer} | {sf(well_kpis.get(w.well_key, {}).get('avg_bopd'), 1):,.1f} STB/j | Evaluate reactivation — pressure test + completion review |"
            for w in (shut_list if 'shut_list' in dir() else [])
        )
        if 'shut_list' in dir() and shut_list else "| — | No shut-in wells | — | — |"
    ) + "\n\n"
    f"### Engineering Recommendations\n"
    f"1. **Water Management:** Cement squeeze or selective perforation plugback for BSW > 80% wells.\n"
    f"2. **Stimulation:** Matrix acidization for low-productivity active wells.\n"
    f"3. **Reactivation:** Pressure test and completion review for shut-in well evaluation.\n"
    f"4. **Prioritization:** Rank by NPV — highest BOPD uplift at lowest intervention cost.\n\n"
    f"{SOURCE}"
)

print(f"  After reservoir analysis: {len(dataset)} pairs")


# ═══════════════════════════════════════════════════════════════════
# CATEGORY 6 — Operational Data
# ═══════════════════════════════════════════════════════════════════

operational_wells_count = 0
for well in wells[:8]:  # Limit to avoid excessive queries
    k = well_kpis.get(well.well_key, {})
    if not k:
        continue
    wc = well.well_code
    avg_ph_w = sf(k.get('avg_prodhours'), 1)

    status_data = get_well_status_kpis(well_key=well.well_key)
    if status_data:
        operational_wells_count += 1
        latest = status_data[0]
        ph = latest.get('prodhours_val') or 'N/A'
        bsw_v = latest.get('bsw_val') or 'N/A'
        gor_v = latest.get('gor_val') or 'N/A'
        temp = latest.get('flowtemp_val') or 'N/A'
        choke = latest.get('choke_val') or 'N/A'
        tubing = latest.get('tubing_val') or 'N/A'
        casing = latest.get('casing_val') or 'N/A'
        report_date = latest.get('date', 'N/A')
        ph_num = float_or_none(ph)
        ph_reco = (
            "Well operating below 20 h/j optimal — investigate downtime."
            if ph_num is not None and ph_num < 20
            else "Production hours are acceptable."
        )

        add(
            f"What are the production hours and operational parameters for well {wc}?",
            f"## 🔬 Well {wc} — Operational Status (Latest Entry: {report_date})\n\n"
            f"> **Executive Summary:** Well **{wc}** latest operational data shows "
            f"**{ph} production hours**, BSW of **{bsw_v}%**, and tubing pressure of **{tubing} psig**.\n\n"
            f"### Operational Parameters\n"
            f"| Parameter | Value | Unit |\n"
            f"|-----------|------:|------|\n"
            f"| Production hours | **{ph}** | h |\n"
            f"| BSW | **{bsw_v}** | % |\n"
            f"| GOR | **{gor_v if gor_v not in ('N/A', None, 0) else 'Data unavailable'}** | SCF/STB |\n"
            f"| Flowing temperature | **{temp}** | °F |\n"
            f"| Choke 16\" | **{choke}** | — |\n"
            f"| Tubing pressure | **{tubing}** | psig |\n"
            f"| Casing pressure | **{casing}** | psig |\n\n"
            f"### Engineering Recommendations\n"
            f"1. **Production hours:** {ph_reco}\n"
            f"2. **Pressure monitoring:** Track tubing/casing pressure differential to detect paraffin deposition or pump wear.\n\n"
            f"{SOURCE}"
        )

        add(
            f"What is the choke setting and tubing pressure of well {wc}?",
            f"## 🔬 Well {wc} — Choke & Pressure Data\n\n"
            f"> **Executive Summary:** Well **{wc}** latest reported choke is **{choke}** with tubing pressure **{tubing} psig** and casing pressure **{casing} psig** (date: {report_date}).\n\n"
            f"### Pressure & Choke Summary\n"
            f"| Parameter | Value | Unit |\n"
            f"|-----------|------:|------|\n"
            f"| Choke 16\" | **{choke}** | — |\n"
            f"| Tubing pressure | **{tubing}** | psig |\n"
            f"| Casing pressure | **{casing}** | psig |\n"
            f"| Flowing temperature | **{temp}** | °F |\n"
            f"| Report date | {report_date} | — |\n\n"
            f"### Engineering Recommendations\n"
            f"1. **Choke optimization:** Evaluate optimal choke size to maximize oil rate while controlling BSW and GOR.\n"
            f"2. **Wellhead monitoring:** Regular wellhead pressure readings enable early detection of flow assurance issues.\n\n"
            f"{SOURCE}"
        )

print(f"  After operational data: {len(dataset)} pairs")


# ═══════════════════════════════════════════════════════════════════
# CATEGORY 7 — Additional multilingual field questions
# ═══════════════════════════════════════════════════════════════════

additional_qa = [
    (
        "What is the field average BSW of EZZAOUIA?",
        f"## 📊 EZZAOUIA Field — Average BSW / Water Cut\n\n"
        f"> **Executive Summary:** The EZZAOUIA field has an average BSW of **{avg_bsw_f:.2f}%** — "
        f"{'✅ within normal operating range (<15%)' if avg_bsw_f < 15 else '⚠️ elevated — water management intervention recommended'}.\n\n"
        f"### Field BSW Summary\n"
        f"| Indicator | Value | Unit | Status |\n"
        f"|-----------|------:|------|--------|\n"
        f"| Field average BSW | **{avg_bsw_f:.2f}** | % | {'✅ Normal' if avg_bsw_f < 15 else '⚠️ Elevated'} |\n"
        f"| Critical wells (BSW>80%) | **{len(critical_bsw_wells)}** | wells | {'🔴 Action required' if critical_bsw_wells else '✅ None'} |\n"
        f"| High BSW wells (BSW>50%) | **{len(high_bsw_wells)}** | wells | {'⚠️ Monitor' if high_bsw_wells else '✅ None'} |\n\n"
        f"### Engineering Recommendations\n"
        f"1. **Water Management:** {'Priority workover for critical BSW wells.' if critical_bsw_wells else 'Maintain current water management strategy.'}\n"
        f"2. **BSW benchmarking:** Field BSW of {avg_bsw_f:.2f}% — monitor for acceleration trend.\n\n"
        f"{SOURCE}"
    ),
    (
        "Quel est le BSW moyen du champ EZZAOUIA?",
        f"## 📊 Champ EZZAOUIA — BSW Moyen\n\n"
        f"> **Résumé exécutif:** Le champ EZZAOUIA a un BSW moyen de **{avg_bsw_f:.2f}%** — "
        f"{'✅ dans la plage normale (<15%)' if avg_bsw_f < 15 else '⚠️ élevé — intervention de gestion des eaux recommandée'}.\n\n"
        f"| Indicateur | Valeur | Unité |\n"
        f"|-----------|-------:|-------|\n"
        f"| BSW moyen champ | **{avg_bsw_f:.2f}** | % |\n"
        f"| Puits BSW critique (>80%) | **{len(critical_bsw_wells)}** | — |\n\n"
        f"{SOURCE}"
    ),
    (
        "ما هو متوسط BSW لحقل عزاوية؟",
        f"## 📊 حقل عزاوية — متوسط BSW\n\n"
        f"> **الملخص التنفيذي:** متوسط BSW في حقل عزاوية هو **{avg_bsw_f:.2f}%** — "
        f"{'✅ ضمن النطاق الطبيعي' if avg_bsw_f < 15 else '⚠️ مرتفع — مطلوب تدخل لإدارة المياه'}.\n\n"
        f"| المؤشر | القيمة | الوحدة |\n"
        f"|--------|-------:|--------|\n"
        f"| متوسط BSW للحقل | **{avg_bsw_f:.2f}** | % |\n"
        f"| الآبار ذات BSW حرج (>80%) | **{len(critical_bsw_wells)}** | — |\n\n"
        f"{SOURCE}"
    ),
    (
        "What is the field average GOR of EZZAOUIA?",
        f"## 📊 EZZAOUIA Field — Average GOR\n\n"
        f"> **Executive Summary:** Field average GOR is **{gor_note(avg_gor_f)}**.\n\n"
        f"| Indicator | Value | Status |\n"
        f"|-----------|------:|--------|\n"
        f"| Field avg GOR | **{gor_note(avg_gor_f)}** | {'ℹ️ Data unavailable' if avg_gor_f == 0 else '✅ Normal' if avg_gor_f < 500 else '🔴 Elevated'} |\n"
        f"| Total gas produced | **{total_gas_f:,.0f} MSCF** | — |\n\n"
        f"### Engineering Recommendations\n"
        f"1. **GOR surveillance:** {'Implement GOR measurement program immediately.' if avg_gor_f == 0 else 'Continue GOR monitoring — track for rising trend indicating gas breakthrough.'}\n\n"
        f"{SOURCE}"
    ),
    (
        "Rank all wells by total cumulative oil production.",
        f"## 🛢️ All Wells Ranked by Cumulative Production — EZZAOUIA Field\n\n"
        f"> **Executive Summary:** Total field cumulative production is **{total_oil_f:,.0f} STB**. "
        f"The top producer accounts for {(si(top_all[0].get('total_oil')) / total_oil_f * 100) if top_all and total_oil_f > 0 else 0:.1f}% of total.\n\n"
        f"### Well Production Ranking\n"
        f"| # | Well | Cumulative (STB) | % Field | Avg BOPD | BSW% |\n"
        f"|:-:|------|----------------:|--------:|----------:|-----:|\n"
        + "\n".join(
            f"| {i+1} | **{w['well_code']}** | {si(w.get('total_oil')):,.0f} | "
            f"{(si(w.get('total_oil')) / total_oil_f * 100) if total_oil_f > 0 else 0:.1f}% | "
            f"{sf(w.get('avg_bopd'), 1):,.1f} | {sf(w.get('avg_bsw'), 1):.1f}% |"
            for i, w in enumerate(sorted(top_all, key=lambda x: si(x.get('total_oil')), reverse=True))
        ) + "\n\n"
        f"### Engineering Recommendations\n"
        f"1. **Portfolio management:** Focus capital on wells with highest remaining reserves potential.\n"
        f"2. **Equity:** Low-cumulative wells may have upside — evaluate stimulation or artificial lift improvement.\n\n"
        f"{SOURCE}"
    ),
]

for prompt, response in additional_qa:
    add(prompt, response)

print(f"  After additional multilingual Q&A: {len(dataset)} pairs")

MIN_QA_PAIRS = 200
if len(dataset) < MIN_QA_PAIRS:
    print(f"  Dataset below minimum target ({len(dataset)} < {MIN_QA_PAIRS}), generating supplemental pairs...")
    for well in wells:
        k = well_kpis.get(well.well_key)
        if not k:
            continue

        wc = well.well_code
        avg_bopd = sf(k.get('avg_bopd'), 1)
        avg_bsw = sf(k.get('avg_bsw'), 1)
        avg_gor = sf(k.get('avg_gor'), 0)
        avg_ph = sf(k.get('avg_prodhours'), 1)
        status_en = "Shut-in" if well.closed == 'Y' else "Active"
        layer = well.layer or "N/A"

        add(
            f"Is well {wc} active or shut-in?",
            f"## 🔬 Well {wc} — Current Status\n\n"
            f"> **Executive Summary:** Well **{wc}** is currently **{status_en}** with avg oil rate **{avg_bopd:,.1f} STB/j** and BSW **{avg_bsw:.1f}%**.\n\n"
            f"| Parameter | Value | Unit |\n"
            f"|-----------|------:|------|\n"
            f"| Status | **{status_en}** | — |\n"
            f"| Avg BOPD | **{avg_bopd:,.1f}** | STB/j |\n"
            f"| Avg BSW | **{avg_bsw:.1f}** | % |\n"
            f"| Avg GOR | **{gor_note(avg_gor)}** | SCF/STB |\n\n"
            f"### Engineering Recommendations\n"
            f"1. **Status follow-up:** {'Prepare reactivation workflow and diagnostic test.' if status_en == 'Shut-in' else 'Maintain production surveillance with weekly KPI checks.'}\n"
            f"2. **Water and gas control:** Monitor BSW and GOR trends to detect breakthrough early.\n\n"
            f"{SOURCE}"
        )
        if len(dataset) >= MIN_QA_PAIRS:
            break

        add(
            f"What layer does well {wc} produce from?",
            f"## 🔬 Well {wc} — Producing Layer\n\n"
            f"> **Executive Summary:** Well **{wc}** produces from layer **{layer}** with average production **{avg_bopd:,.1f} STB/j**.\n\n"
            f"| Parameter | Value |\n"
            f"|-----------|-------|\n"
            f"| Well | **{wc}** |\n"
            f"| Layer | **{layer}** |\n"
            f"| Avg BOPD | **{avg_bopd:,.1f} STB/j** |\n"
            f"| Avg Prod Hours | **{avg_ph:.1f} h/j** |\n\n"
            f"### Engineering Recommendations\n"
            f"1. **Layer surveillance:** Track pressure and fluid behavior for layer {layer} to manage depletion.\n"
            f"2. **Completion optimization:** Validate completion strategy against layer productivity indicators.\n\n"
            f"{SOURCE}"
        )
        if len(dataset) >= MIN_QA_PAIRS:
            break

        add(
            f"What is the GOR of well {wc}?",
            f"## 📊 Well {wc} — GOR Assessment\n\n"
            f"> **Executive Summary:** Well **{wc}** has average GOR **{gor_note(avg_gor)}** with BSW **{avg_bsw:.1f}%**.\n\n"
            f"| Parameter | Value | Unit |\n"
            f"|-----------|------:|------|\n"
            f"| Average GOR | **{gor_note(avg_gor)}** | SCF/STB |\n"
            f"| Avg BOPD | **{avg_bopd:,.1f}** | STB/j |\n"
            f"| Avg BSW | **{avg_bsw:.1f}** | % |\n\n"
            f"### Engineering Recommendations\n"
            f"1. **GOR trend monitoring:** {'Start field measurement campaign to populate missing GOR data.' if sf(avg_gor, 0) == 0 else 'Track GOR trend for early gas cap breakthrough indication.'}\n"
            f"2. **Integrated diagnostics:** Correlate GOR changes with BSW and pressure response.\n\n"
            f"{SOURCE}"
        )
        if len(dataset) >= MIN_QA_PAIRS:
            break

    if len(dataset) < MIN_QA_PAIRS:
        raise RuntimeError(
            f"Generated {len(dataset)} Q&A pairs, below required minimum {MIN_QA_PAIRS}. "
            "Please verify DWH data availability."
        )


# ═══════════════════════════════════════════════════════════════════
# SAVE DATASET
# ═══════════════════════════════════════════════════════════════════

output_dir = os.path.dirname(os.path.abspath(__file__))
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, 'training_data.jsonl')

with open(output_path, 'w', encoding='utf-8') as f:
    for item in dataset:
        f.write(json.dumps(item, ensure_ascii=False) + '\n')

print(f"\n{'='*60}")
print(f"DATASET GENERATION COMPLETE")
print(f"{'='*60}")
print(f"Total Q&A pairs   : {len(dataset)}")
print(f"Output file        : {output_path}")
print(f"Wells processed    : {len(well_kpis)}")
print(f"Year summaries     : {len(year_summaries)} years ({min(year_summaries.keys()) if year_summaries else 'N/A'}–{max(year_summaries.keys()) if year_summaries else 'N/A'})")
print(f"Operational data   : {operational_wells_count} wells with status data")
print(f"\nFirst 3 entries:")
for item in dataset[:3]:
    print(f"  Q: {item['prompt'][:70]}...")
    print(f"  A: {item['response'][:80]}...")
    print()
