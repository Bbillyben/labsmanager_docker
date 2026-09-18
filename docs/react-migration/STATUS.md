# Etat de la migration React

Current state
- UI Django/jQuery fonctionnelle, API DRF non versionnee sous `/api/`, PostgreSQL et worker Django-Q.
- Scaffold React/Vite JSX separe, sans fonctionnalite metier ni integration Docker.
- Depot de distribution a la racine, avec `backend/` comme sous-module Django officiel et `frontend/` versionne dans le depot racine.

Completed
- Architecture, dependances, demarrage, routes, authentification, statiques, proxy et distribution inventories.
- Decisions et matrice initiales documentees ; aucun comportement applicatif modifie.
- Chaine Docker/distribution adaptee au sous-module source `backend/` ; chemins internes de l'image conserves.

Next recommended lot
- Infrastructure — executer le build et le redemarrage documentes sur un hote disposant de Docker, puis valider Gunicorn, Django-Q et les fichiers statiques.

Following lot
- P0 — creation du socle `/api/v1/` : session/CSRF, utilisateur courant et permissions.

Known issues / questions
- Le CLI Docker n'est pas disponible sur la VM inspectee ; le build reel et la validation Compose restent a executer sur l'hote de distribution.
- Confirmer si Token/Basic doivent rester actifs et harmoniser les permissions des endpoints v1.
