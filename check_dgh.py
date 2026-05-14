import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from apps.chatbot.rag_pipeline import get_global_vectorstore
vs = get_global_vectorstore()
col = vs._collection
results = col.get(where={'filename': 'EZZAOUIA WELLS OPERATIONS ACTIVITIES - DGH REPORT SEP2025 (2).pdf'}, include=['metadatas','documents'], limit=10)
for i, (doc, meta) in enumerate(zip(results['documents'], results['metadatas'])):
    wn = meta.get('well_num', 'NONE')
    print('Chunk', i+1, '| well_num=', wn)
    print(doc[:150])
    print()
