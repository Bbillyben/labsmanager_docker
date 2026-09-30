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

## R2.6a.1 — FullCalendar React pour Employee Calendar

### Installation npm

Depuis `frontend/`, avec Node 24 :

```bash
export PATH=/home/ben/.nvm/versions/node/v24.11.1/bin:$PATH
npm install --save @fullcalendar/react@7.1.0 temporal-polyfill
```

`@fullcalendar/react` fournit ici les sous-chemins Standard `daygrid`, `multimonth`, `interaction` et le thème classic. Ne pas installer Scheduler/Premium et ne configurer aucune clé de licence. Le `package-lock.json` généré doit être versionné avec `package.json`. Aucun `npm audit fix` automatique n'est demandé.

### Validation automatisée

```bash
cd /home/django_project/labsmanager/frontend
export PATH=/home/ben/.nvm/versions/node/v24.11.1/bin:$PATH
npm test -- --run src/calendar/fullCalendarAdapter.test.ts src/pages/EmployeeLeaves.test.tsx
npm run lint
npm run typecheck
npm run build
```

```bash
cd /home/django_project/labsmanager/backend
python3 manage.py test common.tests_calendar plugin.tests labsmanager.tests.test_api_v1_employees --verbosity 1 --keepdb
python3 manage.py check
```

Résultats du lot : 7 tests frontend ciblés réussis, ESLint et TypeScript sans erreur, build Vite réussi avec 2 751 modules et l'avertissement existant sur le chunk supérieur à 500 kB. Les 78 tests backend combinés ont réussi en 114,617 s avec la base de test existante conservée ; `manage.py check` ne signale aucune anomalie.

### Validation navigateur ciblée

- Vérifier les vues Mois et Année, la navigation précédent/suivant/Aujourd'hui et le passage vers la synthèse cinq ans.
- Vérifier qu'un Leave couvrant plusieurs jours forme un seul événement continu, que les demi-journées restent explicites et que clic, Tab, Entrée et Espace ouvrent le Sheet.
- Vérifier que vacances scolaires et jours fériés sont des fonds continus, sans chips répétés et sans ouverture du Sheet Leave.
- Vérifier une description contenant une apostrophe, par exemple `Vacances d'Été`, sans `&#x27;` visible.
- Vérifier filtres, mode Tableau, persistance du mode, light/dark et comportement mobile avec défilement horizontal si nécessaire.

Aucune migration de base, dépendance Python, modification Docker/Nginx ou fonctionnalité d'écriture n'est requise.


## R2.7 — mutations GenericInfo et migration des icônes

### Dépendances et périmètre

Aucune installation pip/npm ni modification des verrous. Lucide, Base UI et auditlog déjà
présents suffisent. FAIcon reste nécessaire aux autres modèles et migrations historiques.
Aucun changement Docker/Nginx. R2.6a.2 et R2.7 sont validés manuellement.

### Migration : développement effectué, futur déploiement à prévoir

`staff.0014` a été appliquée et ses conversions d’icônes vérifiées par l’utilisateur sur
la base de développement. React R2.7 et le legacy Django après migration sont validés.
Aucune réexécution n’est requise sur cette base pour clôturer R2.7.

Les commandes suivantes restent la procédure pour un environnement non encore migré,
notamment lors du futur déploiement production, après sauvegarde selon la section suivante.
Depuis `backend/`, avec l’environnement Python habituel, après mise à jour du code :

```bash
python3 manage.py migrate staff 0014 --plan
python3 manage.py migrate staff 0014
python3 manage.py check
```

La migration `0014_genericinfotype_icon_lucide` change le champ puis convertit exactement
six chaînes FA connues. Elle conserve les chaînes inconnues, null et vide. Elle est atomique
sur PostgreSQL et la conversion est explicitement non réversible. Aucun SQL manuel n’est
nécessaire. Ne pas tenter `migrate staff 0013` comme rollback de cette conversion.

### Production : sauvegarde et restauration

Avant migration, arrêter les écritures applicatives et les workers, conserver la version
applicative précédente et réaliser une sauvegarde complète vérifiée de la base PostgreSQL
avec l’outillage habituel (`pg_dump --format=custom`, paramètres de connexion du déploiement).
Vérifier que l’archive peut être restaurée sur une base séparée avant de poursuivre. Exécuter
le plan puis la migration ci-dessus avec le backend et les workers de la même version.

En cas de retour arrière exact, maintenir les écritures arrêtées, restaurer la sauvegarde
complète avec `pg_restore` vers une base de remplacement, remettre la version applicative
correspondante et sa configuration, puis vérifier avant reprise. Ne pas restaurer seulement
la colonne icon : l’historique Django des migrations doit correspondre au code restauré.
Une restauration perd les écritures postérieures à la sauvegarde ; la fenêtre de maintenance
évite cette divergence. Les paramètres et chemins de sauvegarde restent ceux de l’opérateur,
aucun secret ni nom de base de production n’est introduit dans ce document.

### Validation automatisée R2.7

Depuis `backend/` :

```bash
python3 manage.py test labsmanager.tests.test_api_v1_generic_info labsmanager.tests.test_generic_info_icons --verbosity 1 --keepdb
python3 manage.py test labsmanager.tests.test_api_v1 labsmanager.tests.test_api_v1_auth labsmanager.tests.test_api_v1_employees --verbosity 1 --keepdb
python3 manage.py check
python3 manage.py makemigrations staff --check --dry-run
```

Le contrôle global `python3 manage.py makemigrations --check --dry-run` révèle des écarts
préexistants dans endpoints (Milestones.start_date) et project (Participant.employee).
Ne pas générer ces migrations dans R2.7 ; leur traitement nécessite un lot distinct.

Depuis `frontend/`, utiliser Node 24 déjà installé :

```bash
export PATH=/home/ben/.nvm/versions/node/v24.11.1/bin:$PATH
npm test -- src/api/errors.test.ts src/api/useMutation.test.tsx src/pages/useEmployeeResource.test.tsx src/components/common/ConfirmDialog.test.tsx src/pages/EmployeeGenericInfo.test.tsx --maxWorkers=1 --testTimeout=15000
npm test -- src/pages/EmployeeDetailPage.test.tsx src/api/client.test.ts src/pages/EmployeeContracts.test.tsx src/pages/EmployeeFunding.test.tsx src/pages/EmployeeLeaves.test.tsx src/pages/EmployeeProjectWorkload.test.tsx --maxWorkers=1 --testTimeout=15000
npm run lint
npm run typecheck
npm run build
```

Depuis la racine : `git diff --check` puis `git -C backend diff --check`.
Les tests utilisent la base de test PostgreSQL, jamais une migration manuelle de la base métier.

### Protocole navigateur court

1. Lecteur : consulter les informations ; aucun ajout/menu de mutation. Soi sans self_edit :
   ajout seulement. Soi avec self_edit puis éditeur Employee : ajout/modification/suppression.
2. Créer une valeur normale puis une valeur vide, et deux informations du même type.
   Modifier la valeur : le type reste textuel et immuable ; vérifier le résultat après refresh.
3. Supprimer : annuler d’abord (aucun DELETE), puis confirmer ; vérifier disparition et focus.
4. Provoquer une erreur backend dans les outils réseau (par exemple valeur >150 via requête
   modifiée) ; vérifier messages et conservation du Sheet/texte. Bloquer la relecture GET après
   un POST réussi : message de succès déjà enregistré, réessai GET seul, aucun doublon.
5. Vérifier hover, clic/sélection maintenant le menu visible, Tab/Entrée/Espace/Échap et retour
   du focus ; bouton de copie indépendant. Tester tactile, Sheet mobile, light/dark et icônes
   Lucide/fallback. Vérifier aussi les écrans Django Employee/types et une icône Project.

La validation UX React et legacy a été confirmée par l’utilisateur : R2.7 est clôturé.
Ce protocole est conservé comme référence ; R2.8 attend une instruction explicite.


### Résultats automatisés R2.7 — 23 septembre 2026

- Backend ciblé : **14 tests réussis en 26,531 s** (CRUD, matrice complète incluant
  self_edit/global/hiérarchie, CSRF, audit avec acteur, migration et compatibilité legacy).
  Après renforcement des attentes explicites du mapping, les **2 tests icônes** ont été
  relancés et réussissent en **0,293 s**.
- Régression backend session/auth/Employee : **90 tests réussis en 156,493 s**.
- Frontend ciblé : **5 fichiers / 36 tests réussis**, durée **46,41 s**.
- Régression frontend client/détail/Contracts/Financement/Leave/charge Project :
  **6 fichiers / 43 tests réussis**, durée **50,50 s**.
- Les premiers tests backend ont nécessité un accès PostgreSQL hors du bac à sable
  (`could not create socket: Operation not permitted`). Le test du formulaire legacy
  a été corrigé pour fournir la requête attendue par bootstrap-modal-forms.
- La première régression frontend a révélé une fixture encore au format tableau, corrigée.
  Des tests d’intégration ont aussi dépassé 5 s sous charge ; la validation finale utilise
  `--maxWorkers=1 --testTimeout=15000`, sans changer les assertions ni la configuration globale.
- `manage.py check` : aucune anomalie. `makemigrations staff --check --dry-run` : aucun
  changement manquant. Le contrôle global reste en échec pour les deux écarts préexistants
  endpoints/project décrits ci-dessus ; aucune migration supplémentaire n’a été créée.
- ESLint et TypeScript réussis ; build final Vite 7.2.6 réussi (2 760 modules), avec
  l’avertissement existant de chunk JavaScript >500 kB. Aucun changement de dépendance.
- `git diff --check` réussi à la racine et dans backend ; nouveaux fichiers également
  contrôlés pour les espaces de fin de ligne.
- La migration en développement et la validation manuelle React/legacy ont ensuite été
  réalisées et confirmées par l’utilisateur ; elles n’ont pas été exécutées par l’agent.

## R2.8 — Gantt Employee (24 septembre 2026)

Depuis `frontend/`, avec Node 24 déjà présent :

```bash
export PATH=/home/ben/.nvm/versions/node/v24.11.1/bin:$PATH
npm install @svar-ui/react-gantt@2.7.3
npm install --package-lock-only --lockfile-version=3 --ignore-scripts --no-audit
npm test -- src/gantt/EmployeeGanttAdapter.test.ts --maxWorkers=1
npm test -- src/pages/EmployeeDetailPage.test.tsx --maxWorkers=1 --testTimeout=15000
npm run typecheck
npm run lint
npm run build
```

Le registre npm indique la licence MIT et les peer dependencies React/ReactDOM `>=18`.
Dans `backend/` :

```bash
python3 manage.py test labsmanager.tests.test_api_v1_employees.EmployeeLeaveV1ApiTests --keepdb
python3 manage.py test plugin.tests.FrenchHolidayCalendarTests --keepdb
python3 manage.py check
```

Aucune migration BDD R2.8. Validation navigateur terminée avec succès.

## R2.9 — dépendances Task/Milestone (24 septembre 2026)

`endpoints.0006_milestonedependency` est une migration additive créée pour le lot ; Codex
ne l'avait pas appliquée pendant l'implémentation. Vérifier son état réel avant toute
nouvelle application, puis exécuter depuis `backend/` selon l'environnement :

```bash
python3 manage.py migrate endpoints 0006 --plan
python3 manage.py migrate endpoints 0006
python3 manage.py check
python3 manage.py test labsmanager.tests.test_api_v1_dependencies --keepdb
```

Répéter la procédure de migration dans chaque environnement de déploiement ; l'application
future en production est distincte des essais de développement. Depuis `frontend/`, avec
Node 24 : `npm run typecheck`, `npm run lint`, `npm test -- src/gantt/EmployeeGanttAdapter.test.ts src/gantt/SvarGanttAdapter.test.tsx src/pages/EmployeeDetailPage.test.tsx --maxWorkers=1 --testTimeout=15000`, `npm test -- src/pages/MilestoneDependencies.test.tsx --maxWorkers=1`, puis `npm run build`. Ces contrôles ciblés et les 14 tests backend ont réussi sur la base de test PostgreSQL ; la base métier de développement n'a pas été migrée par Codex.

Vérification navigateur R2.9 : ouvrir un Sheet Task/Milestone depuis Liste et Gantt ;
vérifier lecture, projet courant proposé, recherche Project puis item, création inter-Project,
droits `change` sur les deux Projects, refus self/doublon/cycle, alerte temporelle non
bloquante, annulation/confirmation DELETE, liens Gantt visibles uniquement pour les deux
éléments du scope Employee, clavier et responsive. Le Gantt reste en lecture seule.

R2.9 a ensuite été validé fonctionnellement, y compris lecture sans droit de modification
et formulaire d'ajout ouvert à la demande. L'état de la migration est propre à chaque
environnement et ne se déduit pas de cette validation fonctionnelle.

## R2.10 — CRUD Leave Employee

Aucune migration de schéma R2.10 : `python3 manage.py makemigrations leave --check --dry-run`
indique « No changes detected in app 'leave' ». Déployer le code backend et frontend selon
la procédure habituelle ; ne pas lancer de migration Leave artificielle.

Contrôles ciblés depuis `backend/` et `frontend/` respectivement :

```bash
python3 manage.py test labsmanager.tests.test_api_v1_leave_mutations --keepdb
python3 manage.py check
```

```bash
export PATH=/home/ben/.nvm/versions/node/v24.11.1/bin:$PATH
npm test -- src/pages/EmployeeLeaveSheet.test.tsx src/pages/EmployeeLeaves.test.tsx src/pages/EmployeeCalendarSelection.test.tsx src/calendar/leaveSelection.test.ts --maxWorkers=1 --testTimeout=15000
npm run lint
npm run typecheck
npm run build
```

Exécution R2.10 : tests backend ciblés **8 réussis** sur PostgreSQL de test ; **16 tests
frontend ciblés** réussis, ESLint et build Vite direct réussis. `python3 manage.py check` est sans erreur.
`npm run typecheck` échoue encore sur trois erreurs préexistantes du Gantt 60/120 mois
(`EmployeeGanttPanel.tsx`, `SvarGanttAdapter.tsx` et libellé anglais `gantt.months60`).
Le build de production a été vérifié séparément avec `./node_modules/.bin/vite build` ;
le script `npm run build` reste bloqué par le contrôle TypeScript initial. Aucune nouvelle
dépendance n'a été installée.

Le protocole navigateur R2.10 doit couvrir : consultation depuis Tableau et Calendrier,
création par bouton dans les trois vues, sélection d'un jour puis de plusieurs jours en
Mois/Année, périodes ST/MI/EN, changement de type, chevauchement et contiguïté, droits
lecture seule, annulation et confirmation DELETE, rafraîchissement des deux vues, clavier,
mobile et thèmes. La synthèse cinq ans ne propose pas de sélection de plage.

La validation navigateur R2.10 est terminée avec succès. Les corrections finales ajoutent
le déplacement et le redimensionnement des Leave autorisés dans Mois/Année via le PATCH
métier, et utilisent `dayGridYear` pour l'année. La lisibilité annuelle pourra être revue
dans un lot ultérieur ; aucune migration de schéma R2.10 n'a été nécessaire.

## R2.11a — Project List

Aucune migration de schéma ni nouvelle dépendance. Contrôles ciblés depuis `backend/` et
`frontend/` respectivement :

```bash
python3 manage.py test labsmanager.tests.test_api_v1_projects --keepdb
python3 manage.py check
```

```bash
export PATH=/home/ben/.nvm/versions/node/v24.11.1/bin:$PATH
npm test -- --run src/api/projects.test.ts src/pages/ProjectListPage.test.tsx src/pages/EmployeeListPage.test.tsx src/router/AppRouter.test.tsx src/filters/FilterBar.test.tsx --maxWorkers=1 --testTimeout=15000
npm run typecheck
```

Le contrôle TypeScript global reste limité par les trois erreurs Gantt/i18n déjà consignées
ci-dessus. Exécution R2.11a : **8 tests backend** sur PostgreSQL de test et **50 tests
frontend ciblés** réussis ; ESLint ciblé, `manage.py check`, build Vite direct et
`git diff --check` réussis. Le build Vite conserve l'avertissement de taille de chunk connu.
La validation navigateur R2.11a a été confirmée par l'utilisateur. La recherche Employee
du filtre Participant a été ajoutée ensuite et reste à valider au navigateur.

## R2.11b — ProjectSingle et vue d’ensemble

Aucune migration de schéma ni nouvelle dépendance. Contrôles ciblés :

```bash
cd backend
python3 manage.py test labsmanager.tests.test_api_v1_projects labsmanager.tests.test_api_v1_project_overview --keepdb
python3 manage.py check
```

```bash
cd frontend
export PATH=/home/ben/.nvm/versions/node/v24.11.1/bin:$PATH
npm test -- --run src/pages/ProjectDetailPage.test.tsx src/pages/ProjectListPage.test.tsx src/pages/EmployeeGenericInfo.test.tsx --maxWorkers=1 --testTimeout=15000
npx vite build
npm run typecheck
```

Résultat : **17 tests backend** et **39 tests frontend** ciblés réussis ; `manage.py check`,
ESLint ciblé, build Vite direct et `git diff --check` réussis. La validation navigateur
R2.11b reste à faire. Le contrôle TypeScript global conserve les trois erreurs Gantt/i18n
préexistantes ; le build Vite avertit seulement sur la taille du chunk déjà connue.

### Complément R2.11b — icônes GenericInfoTypeProject

`project.0008_genericinfotypeproject_icon_lucide` convertit les cinq anciennes valeurs
FAIcon connues vers Lucide, après passage du champ à `CharField`. Elle est **créée mais
non appliquée sur la base de développement**. Les valeurs inconnues, nulles et vides
restent inchangées. Après vérification et sauvegarde de la base cible, l’utilisateur
exécutera depuis `backend/` :

```bash
python3 manage.py migrate project 0008_genericinfotypeproject_icon_lucide --plan
python3 manage.py migrate project 0008_genericinfotypeproject_icon_lucide
```

Les tests ciblés utilisent uniquement la base PostgreSQL de test ; ils n’appliquent pas
manuellement la migration à la base de développement.
Validation du complément : **13 tests backend** (mapping, champs, legacy, API et CRUD)
et **43 tests frontend** ciblés réussis ; `manage.py check`, ESLint ciblé, build Vite
direct et `git diff --check` réussis. Les trois erreurs TypeScript Gantt/i18n déjà
connues restent présentes. `makemigrations --check --dry-run project` propose encore
`AlterField Participant.employee`, écart sans rapport avec cette migration d’icônes.

## R2.11-i18n — vérifications React

Le contrôle `frontend/src/i18n/i18n.test.ts` vérifie l’égalité des clés FR/EN, la
parité des interpolations et quelques rendus représentatifs. Depuis `frontend/` :

```bash
export PATH=/home/ben/.nvm/versions/node/v24.11.1/bin:$PATH
npm test -- --maxWorkers=2 --testTimeout=15000
npm run typecheck
npm run lint
npx vite build
```
`npm run typecheck` reste bloqué par deux erreurs de typage Gantt préexistantes
(`EmployeeGanttPanel.tsx:18` et `SvarGanttAdapter.tsx:100`, union `120`). Les
anciennes erreurs de clés `gantt.months60`/`gantt.months120` ont disparu ; le
build Vite direct (`npx vite build`) vérifie les ressources compilées.

Résultat final : **36 fichiers / 207 tests frontend réussis**, ESLint réussi,
`npx vite build` réussi et `git diff --check` réussi.

## R2.12a — Project Funding Core

Depuis `backend/`, exécuter les tests ciblés avec accès à la base PostgreSQL de
test, puis le contrôle Django :

```bash
python3 manage.py test labsmanager.tests.test_api_v1_funding --keepdb
python3 manage.py check
```

Depuis `frontend/`, avec Node NVM existant :

```bash
export PATH=/home/ben/.nvm/versions/node/v24.11.1/bin:$PATH
npx vitest run src/pages/ProjectFundingPanel.test.tsx src/pages/ProjectDetailPage.test.tsx src/router/AppRouter.test.tsx src/i18n/i18n.test.ts --maxWorkers=1 --testTimeout=15000
npx eslint src/pages/ProjectFundingPanel.tsx src/pages/ProjectFundingPanel.test.tsx src/pages/ProjectDetailPage.tsx src/pages/ProjectDetailPage.test.tsx src/api/funding.ts src/api/projects.ts src/router/AppRouter.tsx src/i18n/i18n.ts
npm run typecheck
npx vite build
```

Contrôler les diffs à la racine et dans `backend/` avec `git diff --check`.
Aucune commande de migration n'est nécessaire pour R2.12a. La validation navigateur
reste à effectuer ; ne pas exécuter de mutation manuelle sur la base de développement
par cette procédure de tests.

Résultat technique : **19 tests backend** Funding/Project Overview et **50 tests
frontend** ciblés réussis ; `manage.py check`, ESLint ciblé, TypeScript et build Vite
réussis. Le build conserve l'avertissement existant de taille de chunk.

## R2.12b — Expense individuelle et synchronisation

Depuis `backend/` avec la base PostgreSQL de test :

```bash
python3 manage.py test labsmanager.tests.test_api_v1_expenses.ExpenseV1Tests labsmanager.tests.test_api_v1_funding --keepdb
python3 manage.py check
```

Depuis `frontend/` avec Node NVM existant :

```bash
export PATH=/home/ben/.nvm/versions/node/v24.11.1/bin:$PATH
npx vitest run src/pages/ExpenseSection.test.tsx src/pages/EmployeeContracts.test.tsx src/pages/ProjectFundingPanel.test.tsx src/components/common/ConfirmDialog.test.tsx src/i18n/i18n.test.ts --maxWorkers=1 --testTimeout=15000
npx eslint src/api/expenses.ts src/pages/ExpenseSection.tsx src/pages/ExpenseSection.test.tsx src/pages/ProjectFundingPanel.tsx src/pages/ProjectFundingPanel.test.tsx src/pages/ContractDetailSheet.tsx src/pages/EmployeeContracts.test.tsx src/components/common/ConfirmDialog.tsx src/i18n/i18n.ts
npm run typecheck
npx vite build
```

Résultats : **18 tests backend** Expense/Funding et **23 tests frontend** ciblés
réussis ; contrôle Django, ESLint ciblé, TypeScript et build Vite réussis. Le
build conserve l'avertissement connu sur la taille du chunk. Aucune migration
de schéma n'est nécessaire. La validation navigateur R2.12b a depuis été effectuée
avec succès.

## R2.12c — Synthèse financière Fund unifiée

Depuis `frontend/`, avec le Node NVM existant :

```bash
export PATH=/home/ben/.nvm/versions/node/v24.11.1/bin:$PATH
npx vitest run src/pages/ProjectFundingPanel.test.tsx src/pages/ExpenseSection.test.tsx src/pages/ProjectDetailPage.test.tsx src/router/AppRouter.test.tsx src/i18n/i18n.test.ts --maxWorkers=1 --testTimeout=15000
npx eslint src/pages/ProjectFundingPanel.tsx src/pages/ProjectFundingPanel.test.tsx src/i18n/i18n.ts
npm run typecheck
npx vite build
```

Résultats : **61 tests frontend** sur 5 fichiers, ESLint ciblé, TypeScript et
build Vite réussis. Le build garde son avertissement de taille de chunk. Contrôle
final `git diff --check` à la racine. Aucun fichier backend, contrat API ou
migration modifié ; aucun nouveau contrôle Django nécessaire. R2.12a/b/c ont
depuis été validés au navigateur.

## R2.13a — Menus d’entité et exports Project/Employee

Depuis `backend/`, avec PostgreSQL de test :

```bash
python3 manage.py test labsmanager.tests.test_api_v1_reports labsmanager.tests.test_api_v1_projects.ProjectListV1Tests labsmanager.tests.test_api_v1_employees.EmployeeDetailV1ApiTests --keepdb
python3 manage.py check
```

Depuis `frontend/`, avec Node NVM existant :

```bash
export PATH=/home/ben/.nvm/versions/node/v24.11.1/bin:$PATH
npx vitest run src/api/client.test.ts src/components/EntityActionMenu.test.tsx src/components/ReportExportDialog.test.tsx src/pages/ProjectDetailPage.test.tsx src/pages/EmployeeDetailPage.test.tsx src/i18n/i18n.test.ts --maxWorkers=1 --testTimeout=15000
npx eslint src/api/client.ts src/api/client.test.ts src/api/reports.ts src/components/EntityActionMenu.tsx src/components/EntityActionMenu.test.tsx src/components/ReportExportDialog.tsx src/components/ReportExportDialog.test.tsx src/pages/ProjectDetailPage.tsx src/pages/ProjectDetailPage.test.tsx src/pages/EmployeeDetailPage.tsx src/pages/EmployeeDetailPage.test.tsx src/pages/ProjectSheet.tsx src/i18n/i18n.ts
npm run typecheck
npx vite build
```

Résultats : **22 tests backend** et **65 tests frontend** réussis, contrôle Django,
ESLint ciblé, TypeScript et build Vite réussis. Le build garde l'avertissement
connu de taille de chunk. Contrôler `git diff --check` à la racine et dans
`backend/`. Aucune migration ni dépendance ajoutée. R2.12a/b/c sont validés
au navigateur ; validation navigateur R2.13a attendue.

Le `git diff --check` racine et le contrôle limité aux fichiers backend R2.13a
passent. Le contrôle global du dépôt `backend/` relève des espaces finaux déjà
présents dans la modification préexistante de `fund/rules.py`, hors de ce lot.

## R2.13b — Project Settings

Depuis `backend/`, avec PostgreSQL de test :

```bash
python3 manage.py test labsmanager.tests.test_api_v1_project_settings labsmanager.tests.test_api_v1_projects.ProjectListV1Tests --keepdb
python3 manage.py check
```

Depuis `frontend/`, avec Node NVM existant :

```bash
export PATH=/home/ben/.nvm/versions/node/v24.11.1/bin:$PATH
npx vitest run src/components/SettingsSheet.test.tsx src/pages/ProjectDetailPage.test.tsx --maxWorkers=1 --testTimeout=15000
npx vitest run src/pages/ProjectFundingPanel.test.tsx src/components/EntityActionMenu.test.tsx --maxWorkers=1 --testTimeout=15000
npx eslint src/api/settings.ts src/components/SettingsSheet.tsx src/components/SettingsSheet.test.tsx src/pages/ProjectDetailPage.tsx src/pages/ProjectDetailPage.test.tsx src/api/projects.ts src/i18n/i18n.ts
npm run typecheck
npx vite build
```

Résultats : **13 tests backend et 54 tests frontend** réussis, contrôle Django,
ESLint ciblé, TypeScript et build Vite réussis. Le build conserve son avertissement
connu de taille de chunk. Les catalogues Django FR/EN ont été recompilés pour les
libellés et descriptions des trois Settings. Aucun changement de schéma, migration
ou dépendance. R2.13b a été validé au navigateur.

## R2.13c — Édition partielle du Planning Employee

Depuis `backend/`, avec PostgreSQL de test :

```bash
python3 manage.py test labsmanager.tests.test_api_v1_employee_milestone_mutations labsmanager.tests.test_api_v1_employees.EmployeeMilestoneV1ApiTests labsmanager.tests.test_api_v1_project_planning --keepdb
python3 manage.py check
```

Depuis `frontend/`, avec Node NVM existant :

```bash
export PATH=/home/ben/.nvm/versions/node/v24.11.1/bin:$PATH
npx vitest run src/pages/EmployeeDetailPage.test.tsx src/pages/MilestoneDetailSheet.test.tsx --maxWorkers=1 --testTimeout=20000
npx vitest run src/pages/ProjectDetailPage.test.tsx --maxWorkers=1 --testTimeout=20000
npx vitest run src/pages/PlanningMilestoneFormSheet.test.tsx --maxWorkers=1 --testTimeout=20000
npx eslint src/api/planning.ts src/api/employees.ts src/pages/EmployeeProjects.tsx src/gantt/EmployeeGanttPanel.tsx src/pages/MilestoneDetailSheet.tsx src/pages/EmployeeDetailPage.test.tsx src/i18n/i18n.ts
npm run typecheck
npx vite build
```

Résultats : **12 tests backend** et **58 tests frontend** réussis sur les lots
ciblés, contrôle Django, ESLint ciblé, TypeScript et build Vite réussis. Un
lancement frontend combiné a connu un délai de rendu sur un test Project
préexistant ; sa relance isolée passe. Le build conserve son avertissement
connu de taille de chunk. Aucun changement de schéma ni dépendance. Validation
navigateur R2.13c attendue.
