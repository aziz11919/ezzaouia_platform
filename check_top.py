import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from apps.kpis.calculators import get_top_producers
top = get_top_producers(limit=10)
for i, w in enumerate(top, 1):
    print(i, w['well_code'], '| BOPD:', round(float(w['avg_bopd'] or 0),1), '| Total:', int(w['total_oil'] or 0))
