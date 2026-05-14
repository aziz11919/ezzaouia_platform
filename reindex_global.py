import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from apps.chatbot.rag_pipeline import get_global_vectorstore, get_embeddings
from apps.ingestion.models import UploadedFile
from apps.ingestion.tasks import parse_pdf
from apps.chatbot.rag_pipeline import index_document
import re

DGH_NAME = 'EZZAOUIA WELLS OPERATIONS ACTIVITIES - DGH REPORT SEP2025 (2).pdf'

vs = get_global_vectorstore()
col = vs._collection

# Step 1: find all chunk IDs for DGH in global store
all_results = col.get(where={'filename': DGH_NAME}, include=['metadatas'])
ids_to_delete = all_results['ids']
print('DGH chunks in global store:', len(ids_to_delete))

# Step 2: delete them
if ids_to_delete:
    col.delete(ids=ids_to_delete)
    print('Deleted', len(ids_to_delete), 'old DGH chunks from global store')

# Step 3: re-index with corrected regex (only into global store)
doc = UploadedFile.objects.get(id=23)
result = parse_pdf(doc.file.path)
text = result[0]

# Re-index into global store only (doc_id=None skips doc-specific collection)
count = index_document(text, metadata={'filename': DGH_NAME, 'file_type': 'pdf'}, doc_id=None)
print('Re-indexed into global store:', count, 'chunks')

# Step 4: verify
verify = col.get(where={'filename': DGH_NAME}, include=['metadatas'], limit=20)
tagged = sum(1 for m in verify['metadatas'] if m.get('well_num'))
print('Chunks with well_num tag:', tagged, '/', len(verify['ids']))
