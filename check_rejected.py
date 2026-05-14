import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from apps.chatbot.rag_pipeline import get_global_vectorstore

vs = get_global_vectorstore()
col = vs._collection
r = col.get(where={'filename': 'DGH_EZZ1.pdf'}, include=['documents'])
print('Total chunks:', len(r['ids']))
for i, doc in enumerate(r['documents']):
    if 'rejected' in doc.lower() or '58 tubing' in doc.lower():
        print(f'FOUND in chunk {i+1}:')
        print(doc[:600])
        print()
