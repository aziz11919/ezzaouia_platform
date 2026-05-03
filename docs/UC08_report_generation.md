# UC08 - Monthly Production Report Generation

## Fiche

| Champ | Valeur |
|---|---|
| ID | UC08 |
| Domaine | reports |
| Acteurs | User, Admin |
| Objectif | Generer, previsualiser et telecharger les rapports PDF de production |

## Diagramme de cas d'utilisation

```mermaid
flowchart LR
  U[User]
  A[Admin]

  subgraph S[Plateforme EZZAOUIA - Reporting]
    UC081([UC08.1 Generate and download monthly PDF report])
    UC082([UC08.2 Preview report])
    UC083([UC08.3 Anomaly detection and reporting])
  end

  U --> UC081
  U --> UC082
  U --> UC083
  A --> UC081
  A --> UC083
```

## Cas couverts

1. UC08.1 Generate and Download Monthly PDF Report
2. UC08.2 Preview Report (No Download)
3. UC08.3 Anomaly Detection and Reporting
