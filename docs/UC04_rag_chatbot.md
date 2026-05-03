# UC04 - RAG Chatbot and AI-Powered Analysis

## Fiche

| Champ | Valeur |
|---|---|
| ID | UC04 |
| Domaine | chatbot |
| Acteurs | User, Admin, Ollama LLM |
| Objectif | Interroger les donnees et documents via une conversation assistee par IA |

## Diagramme de cas d'utilisation

```mermaid
flowchart LR
  U[User]
  A[Admin]
  L[Ollama LLM]

  subgraph S[Plateforme EZZAOUIA - Chatbot RAG]
    UC041([UC04.1 Start new chat session])
    UC042([UC04.2 Ask question])
    UC043([UC04.3 View conversation history])
    UC044([UC04.4 Rate answer])
    UC045([UC04.5 Rename session])
    UC046([UC04.6 Delete session])
    UC047([UC04.7 Morning suggestions])
    UC048([UC04.8 Add analysis comment])
    UC049([UC04.9 View comments])
  end

  U --> UC041
  U --> UC042
  U --> UC043
  U --> UC044
  U --> UC045
  U --> UC046
  U --> UC047
  U --> UC048
  U --> UC049
  A --> UC043
  A --> UC047
  L --> UC042
  L --> UC047
```

## Cas couverts

1. UC04.1 Start a New Chat Session
2. UC04.2 Ask a Question
3. UC04.3 View Conversation History
4. UC04.4 Rate an Answer
5. UC04.5 Rename a Session
6. UC04.6 Delete a Session
7. UC04.7 Morning Suggestions
8. UC04.8 Add Analysis Comment
9. UC04.9 View Comments on a Message
