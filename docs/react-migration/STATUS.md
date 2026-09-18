# Etat de la migration React

Current state
- UI Django/jQuery fonctionnelle, API DRF non versionnee sous `/api/`, PostgreSQL et worker Django-Q.
- Scaffold React/Vite JSX separe, sans fonctionnalite metier ni integration Docker.
- Deux depots Git locaux : distribution a la racine et backend Django dans `backend/` ; agencement Docker local incoherent a clarifier.

Completed
- Architecture, dependances, demarrage, routes, authentification, statiques, proxy et distribution inventories.
- Decisions et matrice initiales documentees ; aucun comportement applicatif modifie.

Next recommended lot
- P0 : definir et tester uniquement le socle `/api/v1/` de session/CSRF, utilisateur courant et permissions, sans UI React.

Known issues / questions
- Determiner l'agencement Git/build canonique (`labsmanager` gitlink historique contre `backend/` local).
- Confirmer si Token/Basic doivent rester actifs et harmoniser les permissions des endpoints v1.
