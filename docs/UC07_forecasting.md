# UC07 - Production Forecasting

## Fiche

| Champ | Valeur |
|---|---|
| ID | UC07 |
| Domaine | forecasting |
| Acteurs | User, Admin |
| Objectif | Produire des previsions de production par champ et par puits |

## Diagramme de cas d'utilisation

```mermaid
flowchart LR
  U[User]
  A[Admin]

  subgraph S[Plateforme EZZAOUIA - Forecasting]
    UC071([UC07.1 Forecast field level production])
    UC072([UC07.2 Forecast well level production])
    UC073([UC07.3 Forecast all active wells])
    UC074([UC07.4 Prophet seasonal decomposition])
  end

  U --> UC071
  U --> UC072
  U --> UC073
  U --> UC074
  A --> UC071
  A --> UC073
```

## Cas couverts

1. UC07.1 Forecast Field-Level Production
2. UC07.2 Forecast Well-Level Production
3. UC07.3 Forecast All Active Wells
4. UC07.4 Prophet Seasonal Decomposition
