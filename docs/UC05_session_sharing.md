# UC05 - Session Sharing and Collaboration

## Fiche

| Champ | Valeur |
|---|---|
| ID | UC05 |
| Domaine | chatbot |
| Acteurs | User, Admin |
| Objectif | Partager une session de chat en lecture seule pour collaboration |

## Diagramme de cas d'utilisation

```mermaid
flowchart LR
  U[User]
  A[Admin]
  V[Invited Viewer]

  subgraph S[Plateforme EZZAOUIA - Partage de session]
    UC051([UC05.1 Share chat session])
    UC052([UC05.2 Access shared session read only])
    UC053([UC05.3 View sessions shared with me])
    UC054([UC05.4 Generate public share link])
  end

  U --> UC051
  U --> UC053
  U --> UC054
  V --> UC052
  A --> UC051
  A --> UC053
```

## Cas couverts

1. UC05.1 Share a Chat Session
2. UC05.2 Access a Shared Session (Read-Only)
3. UC05.3 View Sessions Shared With Me
4. UC05.4 Generate a Public Share Link
