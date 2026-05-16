import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from django.db import connection
with connection.cursor() as c:
    c.execute("""
        SELECT FullDate, comments 
        FROM dbo.DimDate 
        WHERE comments LIKE '%EZZ#1%' 
        AND comments LIKE '%work%'
        AND FullDate >= '2013-01-01' 
        AND FullDate <= '2013-12-31'
        ORDER BY FullDate
    """)
    rows = c.fetchall()
    print(f'Found {len(rows)} rows')
    for r in rows:
        print(r[0], '|', str(r[1])[:200])
