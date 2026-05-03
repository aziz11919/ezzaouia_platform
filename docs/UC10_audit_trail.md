# UC10 - Audit Trail and Activity Logging

## Fiche

| Champ | Valeur |
|---|---|
| ID | UC10 |
| Domaine | audit |
| Acteurs | Admin, System |
| Objectif | Tracer les actions critiques et permettre le controle des activites |

## Diagramme de cas d'utilisation

```mermaid
flowchart LR
  A[Admin]
  SYS[System]

  subgraph S[Plateforme EZZAOUIA - Audit]
    UC101([UC10.1 Automatic event logging])
    UC102([UC10.2 View audit logs])
    UC103([UC10.3 Export audit log])
    UC104([UC10.4 Chatbot usage monitoring])
  end

  SYS --> UC101
  A --> UC102
  A --> UC103
  A --> UC104
```

## Cas couverts

1. UC10.1 Automatic Event Logging (System)
2. UC10.2 View Audit Logs (Admin)
3. UC10.3 Export Audit Log (Admin)
4. UC10.4 Chatbot Usage Monitoring
