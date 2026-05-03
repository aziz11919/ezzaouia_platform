# UC03 - File Ingestion and Document Processing

## Fiche

| Champ | Valeur |
|---|---|
| ID | UC03 |
| Domaine | ingestion |
| Acteurs | User, Admin, Celery Worker |
| Objectif | Ingerer, valider, parser et indexer les documents pour le RAG |

## Diagramme de cas d'utilisation

```mermaid
flowchart LR
  U[User]
  A[Admin]
  C[Celery Worker]

  subgraph S[Plateforme EZZAOUIA - Ingestion]
    UC031([UC03.1 Upload document])
    UC032([UC03.2 Background processing])
    UC033([UC03.3 Monitor upload status])
    UC034([UC03.4 View recent uploads])
    UC035([UC03.5 Use document in chatbot])
  end

  U --> UC031
  U --> UC033
  U --> UC034
  U --> UC035
  A --> UC031
  A --> UC033
  C --> UC032
  UC031 --> UC032
```

## Cas couverts

1. UC03.1 Upload a Document
2. UC03.2 Background Processing (Celery Task)
3. UC03.3 Monitor Upload Status
4. UC03.4 View Recent Uploads
5. UC03.5 Use Uploaded Document in Chatbot
