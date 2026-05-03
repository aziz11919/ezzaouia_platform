# UC02 - User Management

## Fiche

| Champ | Valeur |
|---|---|
| ID | UC02 |
| Domaine | accounts |
| Acteurs | Admin, User |
| Objectif | Administrer le cycle de vie des comptes utilisateurs |

## Diagramme de cas d'utilisation

```mermaid
flowchart LR
  A[Admin]
  U[User]

  subgraph S[Plateforme EZZAOUIA - Gestion des utilisateurs]
    UC021([UC02.1 Create user])
    UC022([UC02.2 List users])
    UC023([UC02.3 Edit user])
    UC024([UC02.4 Activate or deactivate user])
    UC025([UC02.5 Delete user])
    UC026([UC02.6 Admin reset password])
    UC027([UC02.7 Edit own profile])
  end

  A --> UC021
  A --> UC022
  A --> UC023
  A --> UC024
  A --> UC025
  A --> UC026
  A --> UC027
  U --> UC027
```

## Cas couverts

1. UC02.1 Create User
2. UC02.2 List Users
3. UC02.3 Edit User
4. UC02.4 Activate / Deactivate User
5. UC02.5 Delete User
6. UC02.6 Admin Reset Password
7. UC02.7 Edit Own Profile
