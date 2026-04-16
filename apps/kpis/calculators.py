"""
Calcul des KPIs pétroliers — SQL brut pour compatibilité SQL Server (mssql-django).

Toutes les requêtes utilisent connection.cursor() avec du SQL natif T-SQL
pour éviter les incompatibilités ORM/mssql-django (mots réservés Year/Month,
AVG sur INT, FK traversal dans aggregate, etc.).
"""
import logging
from django.db import connection

logger = logging.getLogger('apps')


def _safe_float(val, decimals=2):
    try:
        return round(float(val), decimals) if val is not None else 0
    except (TypeError, ValueError):
        return 0


def _safe_int(val):
    try:
        return int(val) if val is not None else 0
    except (TypeError, ValueError):
        return 0


# ─── 1. FIELD SUMMARY ────────────────────────────────────────────
def get_field_production_summary(year=None, month=None):
    """
    Production totale du champ EZZAOUIA.
    Sans filtre : KPIs du dernier jour disponible.
    Avec year/month : KPIs sur la période demandée.
    """
    try:
        where_clauses = []
        params = []

        if year is None and month is None:
            # Sans filtre : avg_bopd/total_oil sur le dernier jour avec huile,
            # avg_bsw/avg_gor/avg_prodhours sur le dernier jour avec BSW > 0
            # (ces deux jours peuvent différer quand le dernier jour de prod n'a
            #  pas encore de données DimWellStatus renseignées).
            sql = """
                SELECT
                    AVG(CAST(f.DailyOilPerWellSTBD AS FLOAT))  AS avg_bopd,
                    (SELECT AVG(CAST(ws2.BSW AS FLOAT))
                     FROM dbo.DimWellStatus ws2
                     WHERE ws2.DateKey = (
                         SELECT MAX(f3.DateKey)
                         FROM dbo.FactProduction f3
                         JOIN dbo.DimWellStatus ws3 ON f3.WellStatusKey = ws3.WellStatusKey
                         WHERE f3.DailyOilPerWellSTBD > 0 AND ws3.BSW > 0
                     ))                                         AS avg_bsw,
                    (SELECT AVG(CAST(ws2.GOR AS FLOAT))
                     FROM dbo.DimWellStatus ws2
                     WHERE ws2.DateKey = (
                         SELECT MAX(f3.DateKey)
                         FROM dbo.FactProduction f3
                         JOIN dbo.DimWellStatus ws3 ON f3.WellStatusKey = ws3.WellStatusKey
                         WHERE f3.DailyOilPerWellSTBD > 0 AND ws3.BSW > 0
                     ))                                         AS avg_gor,
                    CAST(SUM(f.DailyOilPerWellSTBD) AS BIGINT)  AS total_oil,
                    SUM(CAST(f.DailyGasPerWellMSCF AS FLOAT))   AS total_gas,
                    SUM(CAST(f.WellStatusWaterBWPD AS FLOAT))   AS total_water,
                    MAX(d.FullDate)                              AS last_date,
                    (SELECT AVG(CAST(ws2.ProdHours AS FLOAT))
                     FROM dbo.DimWellStatus ws2
                     WHERE ws2.DateKey = (
                         SELECT MAX(f3.DateKey)
                         FROM dbo.FactProduction f3
                         JOIN dbo.DimWellStatus ws3 ON f3.WellStatusKey = ws3.WellStatusKey
                         WHERE f3.DailyOilPerWellSTBD > 0 AND ws3.BSW > 0
                     ))                                         AS avg_prodhours
                FROM dbo.FactProduction f
                JOIN dbo.DimDate d       ON f.DateKey = d.DateKey
                LEFT JOIN dbo.DimWellStatus ws ON f.WellStatusKey = ws.WellStatusKey
                WHERE f.DateKey = (
                    SELECT MAX(DateKey) FROM dbo.FactProduction
                    WHERE DailyOilPerWellSTBD > 0
                )
            """
        else:
            if year:
                where_clauses.append("d.[Year] = %s")
                params.append(year)
            if month:
                where_clauses.append("d.[Month] = %s")
                params.append(month)

            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

            sql = f"""
                SELECT
                    AVG(CAST(f.DailyOilPerWellSTBD AS FLOAT))  AS avg_bopd,
                    AVG(CAST(ws.BSW AS FLOAT))                 AS avg_bsw,
                    AVG(CAST(ws.GOR AS FLOAT))                 AS avg_gor,
                    CAST(SUM(f.DailyOilPerWellSTBD) AS BIGINT) AS total_oil,
                    SUM(CAST(f.DailyGasPerWellMSCF AS FLOAT))  AS total_gas,
                    SUM(CAST(f.WellStatusWaterBWPD AS FLOAT))  AS total_water,
                    MAX(d.FullDate)                             AS last_date,
                    AVG(CAST(ws.ProdHours AS FLOAT))            AS avg_prodhours
                FROM dbo.FactProduction f
                JOIN dbo.DimDate d       ON f.DateKey = d.DateKey
                LEFT JOIN dbo.DimWellStatus ws ON f.WellStatusKey = ws.WellStatusKey
                WHERE {where_sql}
            """

        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            row = cursor.fetchone()

        if not row or row[0] is None:
            return {
                'avg_bopd': 0, 'avg_bsw': 0, 'avg_gor': 0,
                'total_oil_stbd': 0, 'total_gas_mscf': 0, 'total_water_bwpd': 0,
                'last_date': None, 'avg_prodhours': 0,
            }

        return {
            'avg_bopd':        _safe_float(row[0], 1),
            'avg_bsw':         _safe_float(row[1], 2),
            'avg_gor':         _safe_float(row[2], 0),
            'total_oil_stbd':  _safe_int(row[3]),
            'total_gas_mscf':  _safe_float(row[4], 0),
            'total_water_bwpd': _safe_float(row[5], 0),
            'last_date':       str(row[6]) if row[6] else None,
            'avg_prodhours':   _safe_float(row[7], 1),
        }

    except Exception as e:
        logger.error(f"get_field_production_summary error: {e}")
        return {
            'avg_bopd': 0, 'avg_bsw': 0, 'avg_gor': 0,
            'total_oil_stbd': 0, 'total_gas_mscf': 0, 'total_water_bwpd': 0,
            'last_date': None, 'avg_prodhours': 0,
        }


# ─── 2. WELL KPIs ────────────────────────────────────────────────
def get_well_kpis(well_key=None, year=None, month=None):
    """
    KPIs par puits — production journalière, BSW, GOR.
    """
    try:
        where_clauses = []
        params = []

        if well_key:
            where_clauses.append("f.WellKey = %s")
            params.append(well_key)
        if year:
            where_clauses.append("d.[Year] = %s")
            params.append(year)
        if month:
            where_clauses.append("d.[Month] = %s")
            params.append(month)

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        sql = f"""
            SELECT
                w.WellCode                                  AS well_code,
                w.Libelle                                   AS well_name,
                AVG(CAST(f.DailyOilPerWellSTBD AS FLOAT))   AS avg_bopd,
                AVG(CAST(ws.BSW AS FLOAT))                  AS avg_bsw,
                AVG(CAST(ws.GOR AS FLOAT))                  AS avg_gor,
                CAST(SUM(f.DailyOilPerWellSTBD) AS BIGINT)  AS total_oil,
                SUM(CAST(f.WellStatusWaterBWPD AS FLOAT))   AS total_water,
                SUM(CAST(f.DailyGasPerWellMSCF AS FLOAT))   AS total_gas,
                AVG(CAST(ws.ProdHours AS FLOAT))             AS avg_prodhours,
                MAX(f.DailyOilPerWellSTBD)                   AS max_bopd
            FROM dbo.FactProduction f
            JOIN dbo.DimDate d       ON f.DateKey = d.DateKey
            JOIN dbo.DimWell w       ON f.WellKey = w.WellKey
            LEFT JOIN dbo.DimWellStatus ws ON f.WellStatusKey = ws.WellStatusKey
            WHERE {where_sql}
            GROUP BY w.WellCode, w.Libelle
            ORDER BY avg_bopd DESC
        """

        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            columns = [col[0] for col in cursor.description]
            rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

        for row in rows:
            for key in row:
                if row[key] is None:
                    row[key] = 0

        return rows

    except Exception as e:
        logger.error(f"get_well_kpis error: {e}")
        return []


# ─── 3. MONTHLY TREND ────────────────────────────────────────────
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
    """
    try:
        where_clauses = []
        params = []

        if date_start and date_end:
            where_clauses.append("d.FullDate >= %s AND d.FullDate <= %s")
            params.extend([str(date_start), str(date_end)])
        elif year_start and year_end:
            where_clauses.append("d.[Year] >= %s AND d.[Year] <= %s")
            params.extend([year_start, year_end])
        elif year:
            where_clauses.append("d.[Year] = %s")
            params.append(year)

        if well_key:
            where_clauses.append("f.WellKey = %s")
            params.append(well_key)

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        sql = f"""
            SELECT
                d.[Month]                                   AS [month],
                d.[Year]                                    AS [year],
                CAST(SUM(f.DailyOilPerWellSTBD) AS BIGINT)  AS total_oil,
                SUM(CAST(f.WellStatusWaterBWPD AS FLOAT))   AS total_water,
                SUM(CAST(f.DailyGasPerWellMSCF AS FLOAT))   AS total_gas,
                AVG(CAST(ws.BSW AS FLOAT))                  AS avg_bsw,
                AVG(CAST(ws.GOR AS FLOAT))                  AS avg_gor
            FROM dbo.FactProduction f
            JOIN dbo.DimDate d       ON f.DateKey = d.DateKey
            LEFT JOIN dbo.DimWellStatus ws ON f.WellStatusKey = ws.WellStatusKey
            WHERE {where_sql}
            GROUP BY d.[Month], d.[Year]
            ORDER BY d.[Year], d.[Month]
        """

        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            columns = [col[0] for col in cursor.description]
            rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

        for r in rows:
            r['month_name'] = _MOIS_FR.get(r.get('month'), str(r.get('month', '')))

        return rows

    except Exception as e:
        logger.error(f"get_monthly_trend error: {e}")
        return []


# ─── 4. WELL STATUS KPIs ─────────────────────────────────────────
def get_well_status_kpis(well_key=None, year=None, month=None):
    """
    Données opérationnelles journalières depuis DimWellStatus :
    ProdHours, BSW, GOR, pressions, températures.
    """
    try:
        where_clauses = []
        params = []

        if well_key:
            where_clauses.append("ws.WellKey = %s")
            params.append(well_key)
        if year:
            where_clauses.append("d.[Year] = %s")
            params.append(year)
        if month:
            where_clauses.append("d.[Month] = %s")
            params.append(month)

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        sql = f"""
            SELECT
                w.WellCode          AS well_code,
                w.Libelle           AS well_name,
                d.FullDate          AS [date],
                ws.ProdHours        AS prodhours_val,
                ws.BSW              AS bsw_val,
                ws.GOR              AS gor_val,
                ws.FlowTempDegF     AS flowtemp_val,
                ws.Choke16In        AS choke_val,
                ws.TubingPsig       AS tubing_val,
                ws.CasingPsig       AS casing_val,
                ws.Remarque         AS remarque_val
            FROM dbo.DimWellStatus ws
            JOIN dbo.DimWell w ON ws.WellKey = w.WellKey
            JOIN dbo.DimDate d ON ws.DateKey = d.DateKey
            WHERE {where_sql}
            ORDER BY d.FullDate DESC
        """

        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    except Exception as e:
        logger.error(f"get_well_status_kpis error: {e}")
        return []


# ─── 5. TOP PRODUCERS ────────────────────────────────────────────
def get_top_producers(limit=5, year=None, month=None):
    """
    Top N puits producteurs par huile (STB cumulé sur la période).
    """
    try:
        where_clauses = []
        params = []

        if year:
            where_clauses.append("d.[Year] = %s")
            params.append(year)
        if month:
            where_clauses.append("d.[Month] = %s")
            params.append(month)

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        sql = f"""
            SELECT TOP(%s)
                w.WellCode                                  AS well_code,
                w.Libelle                                   AS well_name,
                CAST(SUM(f.DailyOilPerWellSTBD) AS BIGINT)  AS total_oil,
                AVG(CAST(f.DailyOilPerWellSTBD AS FLOAT))   AS avg_bopd,
                AVG(CAST(ws.BSW AS FLOAT))                  AS avg_bsw
            FROM dbo.FactProduction f
            JOIN dbo.DimDate d       ON f.DateKey = d.DateKey
            JOIN dbo.DimWell w       ON f.WellKey = w.WellKey
            LEFT JOIN dbo.DimWellStatus ws ON f.WellStatusKey = ws.WellStatusKey
            WHERE {where_sql}
            GROUP BY w.WellCode, w.Libelle
            ORDER BY total_oil DESC
        """
        params_full = [limit] + params

        with connection.cursor() as cursor:
            cursor.execute(sql, params_full)
            columns = [col[0] for col in cursor.description]
            rows = [dict(zip(columns, row)) for row in cursor.fetchall()]

        for row in rows:
            for key in row:
                if row[key] is None:
                    row[key] = 0

        return rows

    except Exception as e:
        logger.error(f"get_top_producers error: {e}")
        return []


# ─── 6. TANK LEVELS ──────────────────────────────────────────────
def get_tank_levels(tank_key=None, year=None, month=None,
                    date_start=None, date_end=None):
    """
    Niveau des tanks par date (VolumeBBLS).
    """
    try:
        where_clauses = []
        params = []

        if tank_key:
            where_clauses.append("ft.TankKey = %s")
            params.append(tank_key)
        if date_start:
            where_clauses.append("d.FullDate >= %s")
            params.append(str(date_start))
        if date_end:
            where_clauses.append("d.FullDate <= %s")
            params.append(str(date_end))
        if year:
            where_clauses.append("d.[Year] = %s")
            params.append(year)
        if month:
            where_clauses.append("d.[Month] = %s")
            params.append(month)

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        sql = f"""
            SELECT
                t.TankCode          AS tank_code,
                t.TankName          AS tank_name,
                d.FullDate          AS [date],
                ft.VolumeBBLS       AS volume
            FROM dbo.FactTankLevel ft
            JOIN dbo.DimTank t ON ft.TankKey = t.TankKey
            JOIN dbo.DimDate d ON ft.DateKey = d.DateKey
            WHERE {where_sql}
            ORDER BY d.FullDate
        """

        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    except Exception as e:
        logger.error(f"get_tank_levels error: {e}")
        return []
