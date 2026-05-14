import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from apps.chatbot.rag_pipeline import get_global_vectorstore
import re

DGH_NAME = 'EZZAOUIA WELLS OPERATIONS ACTIVITIES - DGH REPORT SEP2025 (2).pdf'
vs = get_global_vectorstore()
col = vs._collection

results = col.get(where={'filename': DGH_NAME}, include=['metadatas','documents'], limit=50)
for doc, meta in zip(results['documents'], results['metadatas']):
    if not meta.get('well_num'):
        matches = re.findall(r'(?:EZZ|EZZAOUIA|Ezzaouia).{0,5}\d+', doc, re.IGNORECASE)
        if matches:
            print('UNTAGGED | matches:', matches[:5])
            print(doc[:200])
            print()
