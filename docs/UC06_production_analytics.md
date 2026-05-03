# UC06 - Production Analytics Dashboard and KPI API

## Fiche

| Champ | Valeur |
|---|---|
| ID | UC06 |
| Domaine | dashboard, kpis |
| Acteurs | User, Admin, Power BI |
| Objectif | Consulter les indicateurs de production et exposer les KPIs via API |

## Diagramme de cas d'utilisation

```mermaid
flowchart LR
  U[User]
  A[Admin]
  P[Power BI]

  subgraph S[Plateforme EZZAOUIA - Analytics]
    UC061([UC06.1 Field production summary])
    UC062([UC06.2 Well specific KPIs])
    UC063([UC06.3 Monthly production trend])
    UC064([UC06.4 Top producers])
    UC065([UC06.5 Well operational status])
    UC066([UC06.6 Tank levels])
    UC067([UC06.7 Power BI DirectQuery integration])
  end

  U --> UC061
  U --> UC062
  U --> UC063
  U --> UC064
  U --> UC065
  U --> UC066
  A --> UC061
  A --> UC067
  P --> UC067
```

## Cas couverts

1. UC06.1 View Field Production Summary
2. UC06.2 View Well-Specific KPIs
3. UC06.3 View Monthly Production Trend
4. UC06.4 View Top Producers
5. UC06.5 View Well Operational Status
6. UC06.6 View Tank Levels
7. UC06.7 Power BI DirectQuery Integration
