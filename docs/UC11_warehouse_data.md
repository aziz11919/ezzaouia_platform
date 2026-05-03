# UC11 - Warehouse Data Access

## Fiche

| Champ | Valeur |
|---|---|
| ID | UC11 |
| Domaine | warehouse |
| Acteurs | User, Admin, Power BI |
| Objectif | Exposer les donnees DWH en lecture seule pour analyse |

## Diagramme de cas d'utilisation

```mermaid
flowchart LR
  U[User]
  A[Admin]
  P[Power BI]

  subgraph S[Plateforme EZZAOUIA - Warehouse API]
    UC111([UC11.1 Query dimension data])
    UC112([UC11.2 Query fact data via API])
    UC113([UC11.3 Monitor well active status])
  end

  U --> UC111
  U --> UC112
  U --> UC113
  A --> UC111
  P --> UC112
```

## Cas couverts

1. UC11.1 Query Dimension Data
2. UC11.2 Query Fact Data via API
3. UC11.3 Monitor Well Active Status
