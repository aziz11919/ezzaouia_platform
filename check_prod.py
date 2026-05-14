import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from django.db import connection
with connection.cursor() as c:
    c.execute("SELECT TOP 5 FullDate, SUM(OilProd) as total_oil FROM FactProduction f JOIN DimDate d ON f.date_key = d.date_key GROUP BY FullDate ORDER BY FullDate DESC")
    for r in c.fetchall():
        print(r)
