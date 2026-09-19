# Commandes operateur

## Lot 0 - Analyse et documentation initiales

### VM de developpement

Aucune action requise.

### Packages Python

Aucune action requise.

### Packages npm

Aucune action requise.

### Base de donnees

Aucune action requise.

### Build frontend

Aucune action requise.

### Docker / distribution

Aucune action requise.

## Lot 1 - Stabilisation documentaire de la structure Git

### VM de developpement

Aucune action requise.

### Packages Python

Aucune action requise.

### Packages npm

Aucune action requise.

### Base de donnees

Aucune action requise.

### Build frontend

Aucune action requise.

### Docker / distribution

Aucune action requise.

## Lot 2 - Adaptation Docker au sous-module backend

### VM de developpement

Aucune action requise.

### Packages Python

Aucune action requise.

### Packages npm

Aucune action requise.

### Base de donnees

Aucune action requise.

### Build frontend

Aucune action requise.

### Docker / distribution

Apres recuperation du changement sur l'hote de distribution :

```bash
git submodule update --init --recursive
docker compose build lab-server lab-worker
docker compose up -d lab-server lab-worker lab-proxy
```

## Lot 3 - Socle API v1, session et CSRF

### VM de developpement

Sur la VM Debian, depuis `backend/`, avec l'environnement virtuel du projet active :

```bash
python3 manage.py test labsmanager.tests.test_api_v1 --verbosity 2
python3 manage.py check
```

Validation realisee sur la VM Debian : 4 tests sur 4 reussis en 3.162 s, base `test_django_db` creee puis detruite correctement, et aucun probleme detecte par le system check. Le message `Forbidden: /api/v1/me/` emis pendant le test CSRF est attendu.

### Packages Python

Aucune action requise.

### Packages npm

Aucune action requise.

### Base de donnees

Aucune action requise.

### Build frontend

Aucune action requise.

### Docker / distribution

Aucune action requise.

## Lot 4 - Capacites utilisateur du shell React

### VM de developpement

Sur la VM Debian, depuis `backend/`, avec l'environnement virtuel du projet active :

```bash
python3 manage.py test labsmanager.tests.test_api_v1 --verbosity 2
python3 manage.py check
```

Validation realisee sur la VM Debian : 6 tests sur 6 reussis en 6.270 s, base `test_django_db` creee puis detruite correctement, et aucun probleme detecte par le system check. Le message `Forbidden: /api/v1/me/` emis pendant le test CSRF est attendu.

### Packages Python

Aucune action requise.

### Packages npm

Aucune action requise.

### Base de donnees

Aucune action requise.

### Build frontend

Aucune action requise.

### Docker / distribution

Aucune action requise.

## Lot 5 - Liste des employes v1

### VM de developpement

Sur la VM Debian, depuis `backend/`, avec l'environnement virtuel du projet active :

```bash
python3 manage.py test labsmanager.tests.test_api_v1 labsmanager.tests.test_api_v1_employees --verbosity 2
python3 manage.py check
```

Validation realisee sur la VM Debian : 16 tests sur 16 reussis en 20.130 s, base `test_django_db` creee puis detruite correctement, et aucun probleme detecte par le system check. Les messages `Forbidden: /api/v1/me/` et `Unauthorized: /api/v1/employees/` sont attendus.

### Packages Python

Aucune action requise.

### Packages npm

Aucune action requise.

### Base de donnees

Aucune action requise.

### Build frontend

Aucune action requise.

### Docker / distribution

Aucune action requise.

## Lot 6 - Detail employe v1

### VM de developpement

Sur la VM Debian, depuis `backend/`, avec l'environnement virtuel du projet active :

```bash
python3 manage.py test labsmanager.tests.test_api_v1 labsmanager.tests.test_api_v1_employees --verbosity 2
python3 manage.py check
```

Validation realisee sur la VM Debian : 23 tests sur 23 reussis en 29.349 s, base `test_django_db` creee puis detruite correctement, et aucun probleme detecte par le system check. Les messages `Unauthorized` pour les acces anonymes, `Not Found` pour les employes absents ou hors perimetre et `Forbidden` pour le controle CSRF sont attendus.

### Packages Python

Aucune action requise.

### Packages npm

Aucune action requise.

### Base de donnees

Aucune action requise.

### Build frontend

Aucune action requise.

### Docker / distribution

Aucune action requise.

## Lot 7 - Historique des statuts Employee v1

### VM de developpement

Sur la VM Debian, depuis `backend/`, avec l'environnement virtuel du projet active :

```bash
python3 manage.py test labsmanager.tests.test_api_v1 labsmanager.tests.test_api_v1_employees --verbosity 2
python3 manage.py check
```

Validation realisee sur la VM Debian : 31 tests sur 31 reussis en 40.169 s, base `test_django_db` creee puis detruite correctement, et aucun probleme detecte par le system check. Les messages `Unauthorized` pour les acces anonymes, `Not Found` pour les employes absents ou hors perimetre et `Forbidden` pour le controle CSRF sont attendus.

### Packages Python

Aucune action requise.

### Packages npm

Aucune action requise.

### Base de donnees

Aucune action requise.

### Build frontend

Aucune action requise.

### Docker / distribution

Aucune action requise.

## Lot 8 - Hierarchie Employee v1

### VM de developpement

Sur la VM Debian, depuis `backend/`, avec l'environnement virtuel du projet active :

```bash
python3 manage.py test labsmanager.tests.test_api_v1 labsmanager.tests.test_api_v1_employees --verbosity 2
python3 manage.py check
```

Validation realisee sur la VM Debian : 39 tests sur 39 reussis en 50.731 s, base `test_django_db` creee puis detruite correctement, et aucun probleme detecte par le system check. Les messages `Unauthorized` pour les acces anonymes et `Not Found` pour les cibles absentes, hors perimetre ou les fiches liees non autorisees sont attendus.

### Packages Python

Aucune action requise.

### Packages npm

Aucune action requise.

### Base de donnees

Aucune action requise.

### Build frontend

Aucune action requise.

### Docker / distribution

Aucune action requise.

## Lot 9 - Participations Project de l'Employee v1

### VM de developpement

Sur la VM Debian, depuis `backend/`, avec l'environnement virtuel du projet active :

```bash
python3 manage.py test labsmanager.tests.test_api_v1 labsmanager.tests.test_api_v1_employees --verbosity 2
python3 manage.py check
```

Validation realisee sur la VM Debian : 48 tests sur 48 reussis en 63.550 s, base `test_django_db` creee puis detruite correctement, et aucun probleme detecte par le system check. Les messages `Unauthorized`, `Not Found` et `Forbidden` correspondent aux refus attendus. Deux avertissements DRF non bloquants concernant les validateurs decimaux `max_value` et `min_value` ont ete emis pendant les tests.

### Packages Python

Aucune action requise.

### Packages npm

Aucune action requise.

### Base de donnees

Aucune action requise.

### Build frontend

Aucune action requise.

### Docker / distribution

Aucune action requise.

## Lot 10 - Socle du frontend React R0

### VM de developpement

Depuis `frontend/` sur la VM Debian :

```bash
npm ci
npm test
npm run typecheck
npm run lint
npm run build
```

Validation realisee sur Debian : 3 fichiers et 13 tests Vitest reussis, typecheck et lint sans erreur, puis build Vite 7.2.6 reussi avec 55 modules transformes.

### Packages Python

Aucune action requise.

### Packages npm

Le lot ajoute React Router, TypeScript, Vitest, jsdom et React Testing Library. Lors de la preparation du lot, regenerer le verrou depuis `frontend/` avec :

```bash
npm install --package-lock-only
```

Le fichier `package-lock.json` genere doit etre versionne avec `package.json`.

`npm install --package-lock-only` et `npm ci` ont ete executes avec succes. npm a audite 270 packages et signale 14 vulnerabilites (1 faible, 3 moderees, 10 elevees). Aucun `npm audit fix` automatique n'a ete applique dans ce lot.

### Base de donnees

Aucune action requise.

### Build frontend

Le build de validation est produit par `npm run build` depuis `frontend/`. Il reste un artefact local non versionne.

### Docker / distribution

Aucune action requise. L'integration du build React a la distribution est reportee apres validation du shell.

## Lot 11 - Fondations UX/UI React UX1

### VM de developpement

Depuis `frontend/` sur la VM Debian :

```bash
npm ci
npm test
npm run lint
npm run typecheck
npm run build
VITE_DJANGO_PROXY_TARGET=http://127.0.0.1:8000 npm run dev -- --host 0.0.0.0
```

La validation automatique et visuelle reste en attente du retour Debian.

### Packages Python

Aucune action requise.

### Packages npm

UX1 ajoute `lucide-react` pour les icones SVG React importees individuellement. Regenerer d'abord le verrou depuis `frontend/` :

```bash
npm install --package-lock-only
```

Ne pas executer `npm audit fix` ou `npm audit fix --force`. Comparer simplement le resume d'audit avec les 14 alertes connues de R0.

### Base de donnees

Aucune action requise.

### Build frontend

`npm run build` valide le typage et produit l'artefact local `dist/`, non versionne.

### Docker / distribution

Aucune action requise. Le fallback de production `/app/...` reste hors perimetre UX1.

## Lot 12 - Authentification React AUTH1

### VM de developpement

Depuis `backend/`, avec l'environnement virtuel du projet active :

```bash
python3 manage.py test labsmanager.tests.test_api_v1 labsmanager.tests.test_api_v1_auth --verbosity 2
python3 manage.py check
```

Puis depuis `frontend/` :

```bash
npm ci
npm test
npm run lint
npm run typecheck
npm run build
VITE_DJANGO_PROXY_TARGET=http://127.0.0.1:7000 VITE_DJANGO_PUBLIC_URL=http://192.168.1.145:7000 npm run dev -- --host 0.0.0.0
```

Validation Debian realisee : les 9 tests AUTH1 ont reussi en 27.292 s, la base `test_django_db` a ete creee puis detruite correctement et `python3 manage.py check` n'a signale aucune anomalie. Les reponses `Bad Request`, `Forbidden`, `Method Not Allowed` et `Too Many Requests` correspondent aux cas negatifs attendus.

Cote frontend, 5 fichiers et 25 tests Vitest ont reussi, puis lint, typecheck et build Vite 7.2.6 ont termine sans erreur. Le build a transforme 1933 modules. npm signale toujours les 14 vulnerabilites deja connues ; aucun correctif automatique n'a ete applique.

Validation visuelle realisee avec succes : message generique pour de mauvais identifiants, connexion valide, navigation React, liens historiques ouverts sur Django au port 7000 et deconnexion avec retour a `/app/login`.

### Packages Python

Aucune action requise.

### Packages npm

Aucune action requise.

### Base de donnees

Aucune action requise.

### Build frontend

`npm run build` produit l'artefact local `dist/`, non versionne.

### Docker / distribution

Aucune action requise. L'integration du build React et le fallback `/app/...` restent hors perimetre AUTH1.

## Lot 13 — Liste Employee React R1

### Validation automatisée sur la VM (19 septembre 2026)

Le shell de l'agent utilisait initialement Node 12.22.12, incompatible avec les outils existants (erreur de syntaxe au démarrage de Vitest/ESLint). Node 24.11.1 est déjà installé via nvm ; son utilisation ne nécessite aucune installation ni modification des dépendances.

```bash
cd /home/django_project/labsmanager/frontend
export PATH=/home/ben/.nvm/versions/node/v24.11.1/bin:$PATH
npm test
npm run lint
npm run typecheck
npm run build
```

Résultats : **6 fichiers / 43 tests réussis** (25 existants + 18 R1), lint et typecheck sans erreur, build Vite 7.2.6 réussi (1938 modules). Les tests R1 couvrent les interactions et contrats, pas les détails CSS. Aucune dépendance ajoutée, aucun `npm audit fix`, aucun nouveau résultat d'audit npm revendiqué ; les 14 alertes documentées restent un sujet séparé.

```bash
cd /home/django_project/labsmanager/backend
python3 manage.py test labsmanager.tests.test_api_v1 labsmanager.tests.test_api_v1_employees --verbosity 1
python3 manage.py check
```

Résultats : **48 tests réussis en 86.410 s**, base de test créée puis détruite ; `System check identified no issues (0 silenced).` L'exécution initiale dans le bac à sable bloquait la création de socket PostgreSQL (`Operation not permitted`). Après autorisation explicite, la suite a été exécutée avec accès PostgreSQL, sans changement de configuration ni contournement par une autre base.

### Lancement pour validation manuelle

Dans deux terminaux, avec l'environnement habituel du projet :

```bash
cd /home/django_project/labsmanager/backend
python3 manage.py runserver 0.0.0.0:7000
```

```bash
cd /home/django_project/labsmanager/frontend
export PATH=/home/ben/.nvm/versions/node/v24.11.1/bin:$PATH
VITE_DJANGO_PROXY_TARGET=http://192.168.1.145:7000 VITE_DJANGO_PUBLIC_URL=http://192.168.1.145:7000 npm run dev -- --host 0.0.0.0
```

Ouvrir `http://192.168.1.145:5173/app/employees/`. Réutiliser les serveurs déjà lancés s'ils utilisent ces ports. Aucun serveur supplémentaire n'a été démarré par le lot.

### Checklist navigateur

- Ouvrir directement la route et depuis la sidebar ; vérifier liste, densité, noms, statuts multiples, activité, supérieurs et dates nulles.
- Rechercher (Entrée/bouton), filtrer Actifs/Inactifs, réinitialiser ; trier dans les deux sens et paginer.
- Rafraîchir une URL filtrée/triée/paginée ; vérifier précédent/suivant du navigateur.
- Sélectionner, changer de ligne, désélectionner ; contrôler la zone contextuelle et l'absence de navigation lors de la sélection.
- Ouvrir une fiche via le nom et via la zone contextuelle, puis revenir à la liste ; la fiche Django conserve ses autorisations historiques.
- Observer le chargement en réseau ralenti, aucun résultat, collection vide si possible et erreur locale/réessai si testable.
- Vérifier largeur laptop, tablette/mobile avec scroll horizontal, clavier (Tab/Entrée/Espace), focus visible et console sans erreurs inattendues.

**R1 — implémenté mais non validé** : attendre le retour utilisateur avant validation, R2 ou changement backend des actions.

### Packages / base / distribution

Aucune installation Python/npm, migration, modification backend, Docker ou Nginx. Le build `dist/` reste un artefact local non versionné.

### Ajustement R1 après retour navigateur — sélection et filtres

Le retour utilisateur confirme le fonctionnement de la VM, notamment connexion et accès liste, mais demande de corriger l'ergonomie. Les ajustements de sélection de ligne et d'ajout progressif des filtres restent à confirmer visuellement.

Commandes frontend identiques à celles du lot 13, avec Node 24.11.1 : `npm test`, `npm run lint`, `npm run typecheck`, `npm run build`. Résultats : 6 fichiers / 45 tests réussis ; lint, TypeScript et build Vite réussis (1940 modules). Aucun backend modifié ; la suite backend n'a pas été relancée pour cet ajustement purement frontend, son résultat de 48 tests demeure celui du lot initial.

Vérification manuelle ciblée :

- Cliquer sur une cellule : sélection avec coche/bordure ; recliquer : désélection ; cliquer sur une autre ligne : changement.
- Tab vers une ligne puis Entrée/Espace ; vérifier que le lien de nom reste indépendant et ouvre uniquement Django.
- Cliquer « Ajouter un filtre », choisir Actifs/Inactifs, modifier la valeur, supprimer avec × ; vérifier URL, refresh et retour navigateur.
- Fermer le panneau avec Fermer ou Échap depuis le panneau ; vérifier le focus rendu au bouton d'ajout.
- Vérifier la compacité sur laptop et petit écran. Aucun bouton « Sélectionner » ni colonne de sélection ne subsiste.

Les libellés/options du filtre se modifient dans `frontend/src/config/employeeFilters.ts`, séparément du rendu. Cette configuration appartient au frontend comme le script historique ; un changement nécessite le build habituel.
