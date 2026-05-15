import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from django.db import connection
with connection.cursor() as c:
    c.execute("""
        SELECT w.WellCode, ws.BSW, ws.ProdHours, f.DailyOilPerWellSTBD
        FROM dbo.FactProduction f
        JOIN dbo.DimWell w ON f.WellKey = w.WellKey
        JOIN dbo.DimWellStatus ws ON f.WellStatusKey = ws.WellStatusKey
        JOIN dbo.DimDate d ON f.DateKey = d.DateKey
        WHERE d.FullDate = '2025-11-24' AND ws.ProdHours > 0
        ORDER BY f.DailyOilPerWellSTBD DESC
    """)
    for r in c.fetchall():
        print(r)
