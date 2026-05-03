# UC01 - Authentication and Session Management

## Fiche

| Champ | Valeur |
|---|---|
| ID | UC01 |
| Domaine | accounts |
| Acteurs | User, Admin |
| Objectif | Authentifier les utilisateurs et gerer la session en securite |

## Diagramme de cas d'utilisation

```mermaid
flowchart LR
  U[User]
  A[Admin]

  subgraph S[Plateforme EZZAOUIA - Authentification]
    UC011([UC01.1 Login])
    UC012([UC01.2 Logout])
    UC013([UC01.3 Forced password change])
    UC014([UC01.4 Forgot password and reset])
    UC015([UC01.5 Voluntary password change])
    UC016([UC01.6 Session keep alive])
  end

  U --> UC011
  U --> UC012
  U --> UC013
  U --> UC014
  U --> UC015
  U --> UC016
  A --> UC011
  A --> UC012
  A --> UC015
```

## Cas couverts

1. UC01.1 Login
2. UC01.2 Logout
3. UC01.3 Forced Password Change (First Login)
4. UC01.4 Forgot Password / Self-Service Reset
5. UC01.5 Voluntary Password Change
6. UC01.6 Session Keep-Alive
