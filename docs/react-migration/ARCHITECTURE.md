# Architecture de migration React

## Organisation reelle

La copie de travail `labsmanager/` est organisee autour du depot Git de distribution a la racine et de son sous-module Django officiel :

- le depot de distribution `labsmanager_docker` a la racine, avec Docker, Compose, Nginx, les requirements et les scripts Invoke ;
- `backend/` est le sous-module Django officiel, lie a `git@github.com:Bbillyben/labsmanager.git` et suivant la branche `dev` ;
- `frontend/` est versionne directement dans le depot racine. Il contient le scaffold Vite/React et son propre `package-lock.json` ;
- `docs/react-migration/` est egalement versionne dans le depot racine.

L'ancien gitlink `labsmanager/` a ete supprime au profit du sous-module canonique `backend/`. La chaine Docker/distribution copie maintenant ce sous-module dans l'image. Le chemin interne historique `${LAB_HOME}/labsmanager` est conserve : il reste coherent avec `WORKDIR`, Gunicorn, Django-Q, collectstatic et les taches Invoke, sans imposer le nom du repertoire source.

## Backend Django actuel

Le point d'entree est `backend/manage.py`, avec le projet `backend/labsmanager/` (`settings.py`, `urls.py`, `wsgi.py`). Les apps metier restent separees : `staff`, `project`, `fund`, `expense`, `endpoints`, `leave`, `infos`, `notification`, `reports`, `settings`, `plugin`, `common`, `dashboard` et `import`.

L'UI est rendue par Django depuis `backend/templates/`, avec les assets sources dans `backend/data/static/`. Elle utilise notamment Bootstrap, jQuery/plugins de tables, calendriers et graphiques. DRF expose deja des ViewSets pour utilisateurs, groupes, employees, equipes, projets, fonds, contrats, depenses, budgets, contributions, jalons, conges, favoris, abonnements, organisations et notes.

Les routes REST sont sous `/api/`, avec `/api/settings/`, `/api/plugin/` et l'interface DRF `/api-auth/`. Les permissions globales DRF utilisent `DjangoModelPermissionsOrAnonReadOnly`, plusieurs ViewSets ajoutent `IsAuthenticated`, et des mixins metier gerent aussi des droits. Un audit endpoint par endpoint reste requis.

PostgreSQL est la base par defaut. La configuration est lue d'abord depuis les variables d'environnement, puis `backend/config.yaml` (ou `LABSMANAGER_CONFIG_FILE`), puis les valeurs par defaut. `config.yaml` et `.env` sont sensibles et ignores par Git.

## Frontend actuel

`frontend/` est le template Vite React minimal : React 19, JSX, aucune fonctionnalite metier et aucune configuration TypeScript. `npm run dev` ecoute sur `0.0.0.0:5173` et proxifie `/api` vers `http://192.168.1.145:8000`. Il n'existe ni integration de son build dans Django/Nginx, ni route `/app/`, ni gestion explicite de CSRF dans le scaffold.

## Developpement bare-metal

Django est lance depuis `backend/` avec `python manage.py runserver` et rejoint PostgreSQL selon l'environnement ou `config.yaml`. Le frontend se lance separement par `npm run dev` depuis `frontend/`. Les origines Vite locales sont deja autorisees avec credentials et comme origines CSRF de confiance. Django-Q se lance avec `python manage.py qcluster` ; la distribution encapsule cette commande sous `invoke worker`.

## Build et distribution Docker actuels

Le `Dockerfile` Python 3.11 installe les paquets systeme puis le `requirements.txt` racine avec `pip install -U -r base_requirements.txt`. Il copie le sous-module source `backend/` vers `${LAB_HOME}/labsmanager` dans l'image. Gunicorn sert `labsmanager.wsgi` sur le port 8000. Compose lance PostgreSQL 13, Gunicorn, un worker Django-Q et Nginx.

Le volume persistant partage contient PostgreSQL, les medias et les statiques. `init.sh` initialise les repertoires et copie les assets fournis quand ils sont vides. La collecte Django est explicite : `invoke update` execute actuellement `makemigrations`, `migrate`, `check` et `collectstatic`. Nginx sert `/static/` depuis le volume et reverse-proxy les autres routes vers Gunicorn. Vite n'entre pas dans ce build.

`requirements.in` est la liste source et `requirements.txt` le verrou effectivement installe par Docker. Les dependances npm sont declarees dans `frontend/package.json` et verrouillees dans `frontend/package-lock.json`.

## Architecture cible et coexistence

La cible reste : React + TypeScript -> API REST -> Django/DRF -> logique metier et permissions -> ORM Django -> PostgreSQL. Les apps et modeles existants restent en place.

Les routes Django historiques sont conservees et le nouveau shell React sera monte sous `/app/`, chemin actuellement libre. En developpement, Vite peut proxifier l'API vers Django. En production, il faudra tester le routage Nginx des assets et le fallback SPA sans modifier le proxy historique.

L'authentification cible privilegie la session Django et le cookie CSRF sur la meme origine. Token et Basic sont actuellement actifs dans DRF, mais ne constituent pas le contrat cible sans decision explicite. Le backend reste seul autoritaire pour les permissions.

Les nouvelles routes stables seront publiees sous `/api/v1/`. Les routes `/api/` actuelles ne seront ni renommees ni cassees pendant la transition.
