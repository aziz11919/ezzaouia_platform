import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from apps.chatbot.rag_pipeline import _build_structured_well_year_trend_answer
result = _build_structured_well_year_trend_answer('Montrez evolution mensuelle EZZ1 2024', 'fr', '15/05/2026')
print(result[:1000] if result else 'None returned')
