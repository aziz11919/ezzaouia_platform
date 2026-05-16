import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from apps.kpis.calculators import get_monthly_trend
from apps.warehouse.models import DimWell
well = DimWell.objects.filter(well_code__icontains='EZZ1').exclude(well_code__icontains='EZZ1').first()
well = DimWell.objects.filter(well_code='EZZ1').first()
print('Well:', well.well_code, well.well_key)
rows = get_monthly_trend(well_key=well.well_key, year=2024, lang='fr')
print('Months found:', len(rows))
for r in rows:
    print(r)
