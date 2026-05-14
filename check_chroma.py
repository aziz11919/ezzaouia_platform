from apps.chatbot.rag_pipeline import get_global_vectorstore
vs = get_global_vectorstore()
results = vs.similarity_search('EZZ 8 ST 2250 CLOSED', k=3)
for i, doc in enumerate(results):
    print(f'--- chunk {i+1} ---')
    print(repr(doc.page_content[:300]))
