# UC09 - Document Library

## Fiche

| Champ | Valeur |
|---|---|
| ID | UC09 |
| Domaine | bibliotheque |
| Acteurs | User, Admin |
| Objectif | Consulter et administrer les documents deja indexes |

## Diagramme de cas d'utilisation

```mermaid
flowchart LR
  U[User]
  A[Admin]

  subgraph S[Plateforme EZZAOUIA - Bibliotheque]
    UC091([UC09.1 Browse document library])
    UC092([UC09.2 Search documents])
    UC093([UC09.3 Open document for chatbot analysis])
    UC094([UC09.4 Delete a document])
    UC095([UC09.5 View document details])
  end

  U --> UC091
  U --> UC092
  U --> UC093
  U --> UC095
  A --> UC091
  A --> UC094
```

## Cas couverts

1. UC09.1 Browse Document Library
2. UC09.2 Search Documents
3. UC09.3 Open Document for Chatbot Analysis
4. UC09.4 Delete a Document
5. UC09.5 View Document Details
