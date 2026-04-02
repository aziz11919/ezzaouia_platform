"""
Calcul des KPIs pétroliers depuis FactDailyProduction et FactWellTest.
"""
import logging
from django.db.models import Sum, Avg, Max, Min, F, Q
from django.db.models.functions import TruncMonth, TruncYear
from apps.warehouse.models import (
    FactDailyProduction, FactWellTest, DimWell, DimDate
)

logger = logging.getLogger('apps')


def get_field_production_summary(year=None, month=None):
    """
    Production totale du champ EZZAOUIA.
    Retourne : huile, eau, gaz, BSW moyen, GOR moyen.
    """
    qs = FactDailyProduction.objects.all()

    if year:
        qs = qs.filter(datekey__year=year)
    if month:
        qs = qs.filter(datekey__month=month)

    result = qs.aggregate(
        total_oil_stbd   = Sum('dailyoilprodstbd'),
        total_water_blsd = Sum('dailywaterprodblsd'),
        total_gas_mscf   = Sum('dailygasprodmscf'),
        avg_bsw          = Avg('bsw'),
        avg_gor          = Avg('gorscfstb'),
        avg_prodhours    = Avg('prodhours'),
        total_lifting    = Sum('lifting'),
        total_sales      = Sum('sales'),
    )

    # Calculer BOPD moyen (production journalière moyenne)
    count = qs.values('datekey').distinct().count()
    result['avg_bopd'] = round(
        result['total_oil_stbd'] / count, 1
    ) if count and result['total_oil_stbd'] else 0

    # Arrondir les valeurs
    for key in result:
        if result[key] is not None:
            result[key] = round(float(result[key]), 2)
        else:
            result[key] = 0

    return result


def get_well_kpis(well_key=None, year=None, month=None):
    """
    KPIs par puits — production journalière, BSW, GOR.
    """
    qs = FactDailyProduction.objects.select_related(
        'wellkey', 'datekey'
    )

    if well_key:
        qs = qs.filter(wellkey=well_key)
    if year:
        qs = qs.filter(datekey__year=year)
    if month:
        qs = qs.filter(datekey__month=month)

    result = qs.values(
        well_code=F('wellkey__wellcode'),
        well_name=F('wellkey__libelle'),
    ).annotate(
        avg_bopd      = Avg('dailyoilprodstbd'),
        avg_bsw       = Avg('bsw'),
        avg_gor       = Avg('gorscfstb'),
        total_oil     = Sum('dailyoilprodstbd'),
        total_water   = Sum('dailywaterprodblsd'),
        total_gas     = Sum('dailygasprodmscf'),
        avg_prodhours = Avg('prodhours'),
        max_bopd      = Max('dailyoilprodstbd'),
    ).order_by('-avg_bopd')

    return list(result)


_MOIS_FR = {
    1: 'Janvier', 2: 'Février', 3: 'Mars', 4: 'Avril',
    5: 'Mai', 6: 'Juin', 7: 'Juillet', 8: 'Août',
    9: 'Septembre', 10: 'Octobre', 11: 'Novembre', 12: 'Décembre',
}


def get_monthly_trend(year=None, well_key=None, year_start=None, year_end=None,
                      date_start=None, date_end=None):
    """
    Tendance mensuelle de production — pour graphiques.
    Priorité : date_start/date_end > year_start/year_end > year.
    GROUP BY year+month numériques uniquement (évite les doublons si monthname
    est inconsistant dans DimDate).
    """
    qs = FactDailyProduction.objects.select_related('datekey')

    if date_start and date_end:
        qs = qs.filter(datekey__fulldate__gte=date_start, datekey__fulldate__lte=date_end)
    elif year_start and year_end:
        qs = qs.filter(datekey__year__gte=year_start, datekey__year__lte=year_end)
    elif year:
        qs = qs.filter(datekey__year=year)
    if well_key:
        qs = qs.filter(wellkey=well_key)

    rows = list(
        qs.values(
            month=F('datekey__month'),
            year=F('datekey__year'),
        ).annotate(
            total_oil   = Sum('dailyoilprodstbd'),
            total_water = Sum('dailywaterprodblsd'),
            total_gas   = Sum('dailygasprodmscf'),
            avg_bsw     = Avg('bsw'),
            avg_gor     = Avg('gorscfstb'),
        ).order_by('year', 'month')
    )

    for r in rows:
        r['month_name'] = _MOIS_FR.get(r['month'], str(r['month']))

    return rows


def get_well_test_kpis(well_key=None, year=None):
    """
    Résultats des tests de puits — BOPD, GOR, Water Cut.
    """
    qs = FactWellTest.objects.select_related('wellkey', 'datekey')

    if well_key:
        qs = qs.filter(wellkey=well_key)
    if year:
        qs = qs.filter(datekey__year=year)

    result = qs.values(
        well_code=F('wellkey__wellcode'),
        well_name=F('wellkey__libelle'),
        date=F('datekey__fulldate'),
    ).annotate(
        oil_bopd   = F('oilbopd'),
        water_bwpd = F('waterbwpd'),
        gas_mscfd  = F('gasmscfd'),
        gor_value  = F('gor'),
    ).order_by('-date')

    return list(result)


def get_top_producers(limit=5, year=None):
    """
    Top N puits producteurs par huile.
    """
    qs = FactDailyProduction.objects.select_related('wellkey')

    if year:
        qs = qs.filter(datekey__year=year)

    return list(
        qs.values(
            well_code=F('wellkey__wellcode'),
            well_name=F('wellkey__libelle'),
        ).annotate(
            total_oil = Sum('dailyoilprodstbd'),
            avg_bopd  = Avg('dailyoilprodstbd'),
            avg_bsw   = Avg('bsw'),
        ).order_by('-total_oil')[:limit]
    )


def get_cumulative_production(well_key=None):
    """
    Production cumulée depuis le début.
    """
    qs = FactDailyProduction.objects.all()
    if well_key:
        qs = qs.filter(wellkey=well_key)

    return qs.aggregate(
        cum_oil_stb   = Sum('cumoilstbcorrected'),
        cum_water_bbl = Sum('cumwaterbbls'),
        cum_gas_mscf  = Sum('cumgasmscf'),
    )