import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from apps.kpis.calculators import *
from apps.warehouse.models import DimWell

print('='*60)
print('1. FIELD SUMMARY')
print('='*60)
s = get_field_production_summary()
for k, v in s.items():
    print(f'  {k}: {v}')

print()
print('='*60)
print('2. TOP 10 PRODUCERS')
print('='*60)
top = get_top_producers(limit=10)
for i, w in enumerate(top, 1):
    print(f"  {i}. {w['well_code']:8} | BOPD: {float(w['avg_bopd'] or 0):>8.1f} | Total: {int(w['total_oil'] or 0):>10,} STB | BSW: {float(w['avg_bsw'] or 0):>5.1f}%")

print()
print('='*60)
print('3. WELL KPIs — ALL WELLS')
print('='*60)
kpis = get_well_kpis()
for w in kpis:
    print(f"  {w['well_code']:8} | BOPD: {float(w['avg_bopd'] or 0):>8.1f} | BSW: {float(w['avg_bsw'] or 0):>5.1f}% | GOR: {float(w['avg_gor'] or 0):>6.0f} | Cum: {int(w['total_oil'] or 0):>10,}")

print()
print('='*60)
print('4. FIELD SUMMARY BY YEAR')
print('='*60)
for year in [2022, 2023, 2024]:
    s = get_field_production_summary(year=year)
    print(f"  {year}: BOPD={float(s['avg_bopd'] or 0):.1f} | Total={int(s['total_oil_stbd'] or 0):,} STB | BSW={float(s['avg_bsw'] or 0):.2f}%")

print()
print('='*60)
print('5. MONTHLY TREND EZZ1 2024')
print('='*60)
well = DimWell.objects.get(well_code='EZZ1')
rows = get_monthly_trend(well_key=well.well_key, year=2024, lang='en')
for r in rows:
    print(f"  {r['month_name']:12} {r['year']}: Oil={int(r['total_oil'] or 0):,} STB | BSW={float(r['avg_bsw'] or 0):.1f}%")

print()
print('='*60)
print('6. TANK LEVELS (last 5)')
print('='*60)
tanks = get_tank_levels()
seen = {}
for t in tanks:
    seen[t['tank_code']] = t
for code, t in seen.items():
    print(f"  {code}: {t['volume']:,} BBL on {t['date']}")

print()
print('ALL CHECKS DONE!')
