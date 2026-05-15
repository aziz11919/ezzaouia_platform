import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from apps.kpis.calculators import get_top_producers
top = get_top_producers(limit=5)
for i, w in enumerate(top, 1):
    print(f"{i}. {w['well_code']} | BOPD: {w.get('avg_bopd')} | Total: {w.get('total_oil')} | BSW: {w.get('avg_bsw')}")
