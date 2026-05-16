import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from django.db import connection

print('='*60)
print('1. FIELD BSW COMPARISON')
print('='*60)
with connection.cursor() as c:
    c.execute("""
        SELECT 
            AVG(CASE WHEN ws.BSW > 0 THEN CAST(ws.BSW AS FLOAT) END) as bsw_correct,
            AVG(CAST(ws.BSW AS FLOAT)) as bsw_old
        FROM dbo.FactProduction f
        JOIN dbo.DimWellStatus ws ON f.WellStatusKey = ws.WellStatusKey
        WHERE ws.ProdHours > 0 AND f.DailyOilPerWellSTBD > 0
    """)
    r = c.fetchone()
    print(f'  BSW (zeros excluded): {r[0]:.2f}%')
    print(f'  BSW (all values):     {r[1]:.2f}%')

print()
print('='*60)
print('2. TOP 10 BY CUMULATIVE OIL')
print('='*60)
with connection.cursor() as c:
    c.execute("""
        SELECT TOP 10 w.WellCode,
            SUM(f.DailyOilPerWellSTBD) as total_oil,
            AVG(CAST(f.DailyOilPerWellSTBD AS FLOAT)) as avg_bopd,
            AVG(CASE WHEN ws.BSW > 0 THEN CAST(ws.BSW AS FLOAT) END) as avg_bsw
        FROM dbo.FactProduction f
        JOIN dbo.DimWell w ON f.WellKey = w.WellKey
        JOIN dbo.DimWellStatus ws ON f.WellStatusKey = ws.WellStatusKey
        WHERE ws.ProdHours > 0
        GROUP BY w.WellCode
        ORDER BY total_oil DESC
    """)
    for i, r in enumerate(c.fetchall(), 1):
        print(f'  {i}. {r[0]:8} | Total: {int(r[1]):>10,} STB | BOPD: {float(r[2]):>8.1f} | BSW: {float(r[3] or 0):>5.1f}%')

print()
print('='*60)
print('3. WELLS WITH BSW > 80%')
print('='*60)
with connection.cursor() as c:
    c.execute("""
        SELECT w.WellCode,
            AVG(CASE WHEN ws.BSW > 0 THEN CAST(ws.BSW AS FLOAT) END) as avg_bsw,
            AVG(CAST(f.DailyOilPerWellSTBD AS FLOAT)) as avg_bopd
        FROM dbo.FactProduction f
        JOIN dbo.DimWell w ON f.WellKey = w.WellKey
        JOIN dbo.DimWellStatus ws ON f.WellStatusKey = ws.WellStatusKey
        WHERE ws.ProdHours > 0
        GROUP BY w.WellCode
        HAVING AVG(CASE WHEN ws.BSW > 0 THEN CAST(ws.BSW AS FLOAT) END) > 80
        ORDER BY avg_bsw DESC
    """)
    for r in c.fetchall():
        print(f'  {r[0]:8} | BSW: {float(r[1] or 0):>5.1f}% | BOPD: {float(r[2] or 0):>8.1f}')

print()
print('='*60)
print('4. ANNUAL PRODUCTION SUMMARY')
print('='*60)
with connection.cursor() as c:
    c.execute("""
        SELECT d.[Year],
            SUM(f.DailyOilPerWellSTBD) as total_oil,
            AVG(CAST(f.DailyOilPerWellSTBD AS FLOAT)) as avg_bopd,
            AVG(CASE WHEN ws.BSW > 0 THEN CAST(ws.BSW AS FLOAT) END) as avg_bsw
        FROM dbo.FactProduction f
        JOIN dbo.DimDate d ON f.DateKey = d.DateKey
        JOIN dbo.DimWellStatus ws ON f.WellStatusKey = ws.WellStatusKey
        WHERE ws.ProdHours > 0
        GROUP BY d.[Year]
        ORDER BY d.[Year]
    """)
    for r in c.fetchall():
        print(f'  {r[0]}: Total={int(r[1]):>10,} STB | BOPD={float(r[2]):>8.1f} | BSW={float(r[3] or 0):>5.1f}%')

print()
print('='*60)
print('5. EZZ1 MONTHLY 2024')
print('='*60)
with connection.cursor() as c:
    c.execute("""
        SELECT d.[Month], d.[Year],
            SUM(f.DailyOilPerWellSTBD) as total_oil,
            AVG(CASE WHEN ws.BSW > 0 THEN CAST(ws.BSW AS FLOAT) END) as avg_bsw
        FROM dbo.FactProduction f
        JOIN dbo.DimDate d ON f.DateKey = d.DateKey
        JOIN dbo.DimWell w ON f.WellKey = w.WellKey
        JOIN dbo.DimWellStatus ws ON f.WellStatusKey = ws.WellStatusKey
        WHERE w.WellCode = 'EZZ1' AND d.[Year] = 2024 AND ws.ProdHours > 0
        GROUP BY d.[Month], d.[Year]
        ORDER BY d.[Year], d.[Month]
    """)
    months = ['','Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
    for r in c.fetchall():
        print(f'  {months[r[0]]:4} {r[1]}: Oil={int(r[2]):,} STB | BSW={float(r[3] or 0):.1f}%')

print()
print('ALL DB CHECKS DONE!')
