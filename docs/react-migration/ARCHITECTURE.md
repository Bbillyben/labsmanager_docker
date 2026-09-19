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

`frontend/` contient le socle React 19 + TypeScript de la SPA. React Router est monte avec le basename `/app`; seul l'accueil protege et une page 404 existent a ce stade. Le serveur Vite ecoute sur `0.0.0.0:5173` et proxifie `/api` et `/accounts` vers la cible Django definie par `VITE_DJANGO_PROXY_TARGET`, avec `http://192.168.1.145:8000` comme valeur de developpement par defaut. Le build n'est pas encore integre a Django/Nginx.

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

## Socle du frontend React

Le shell React est reserve a `/app/` et utilise des URLs d'API relatives a l'origine courante. Son client HTTP envoie toujours les cookies de session, lit les reponses JSON ou sans contenu, propage les annulations par `AbortSignal` et transforme les reponses non reussies en erreurs typees portant le statut et le corps. Pour une methode non sure, il recopie le cookie Django `csrftoken` dans `X-CSRFToken` lorsqu'il est present.

L'amorcage appelle exclusivement `GET /api/v1/me/` et distingue quatre etats : chargement, session authentifiee, session absente ou expiree, et erreur technique. Une session anonyme n'ouvre aucun mode fonctionnel : le routeur dirige vers la page React `/app/login`. Toute future reponse `401` recue par le client invalide centralement l'etat du shell ; une reponse `403` reste une interdiction metier et ne doit pas etre assimilee a une expiration de session.

Le contexte frontend reprend exactement l'identite et les capacites du contrat backend. Ces capacites servent uniquement a adapter la navigation ; elles ne remplacent jamais les autorisations appliquees par Django. Les liens vers l'interface historique restent des navigations HTML hors SPA et sont construits depuis `VITE_DJANGO_PUBLIC_URL` en developpement separe.

## Authentification React AUTH1

React possede l'ecran de connexion et l'action de deconnexion, mais Django et django-allauth restent l'autorite. `POST /api/v1/auth/login/` reutilise le `LoginForm` Allauth configure : connexion par nom d'utilisateur ou email, backends existants, duree de session et limitation native des tentatives sont ainsi conserves. La limite globale `login` est consommee par la vue API et la limite `login_failed` reste appliquee par l'adapter. Les erreurs d'identifiant inconnu, mot de passe incorrect et compte inactif partagent volontairement le meme contrat afin de ne pas permettre l'enumeration des comptes.

`POST /api/v1/auth/logout/` appelle la deconnexion Django native. Les deux endpoints sont exclusivement accessibles en POST et proteges par CSRF, y compris lorsque la connexion est encore anonyme. Le frontend initialise le cookie avec `/api/v1/me/`, envoie `X-CSRFToken`, puis recharge `/me/` apres une connexion reussie avant d'ouvrir le shell. Une route protegee conserve sa destination React dans l'etat du routeur ; seuls les chemins internes commençant par `/` et non par `//` sont acceptes au retour.

Les workflows d'inscription sur invitation, reinitialisation/changement de mot de passe et gestion des emails restent servis par Allauth dans l'interface Django. Vite ne proxifie plus `/accounts`; seul `/api` est proxifie pendant le developpement. Le proxy aligne vers sa cible l'en-tete `Origin` des requetes API, ce qui permet a Django d'appliquer son controle CSRF sans ajouter l'origine temporaire Vite aux origines de confiance. Cette adaptation reste limitee au serveur de developpement.

Ce lot ne cree aucune route ni interface Employee. Avant toute interface metier React significative, un lot UX/UI doit fixer les principes de navigation, de composants, d'accessibilite et de presentation qui guideront les ecrans suivants.

## Fondations UX/UI React

Le shell cible combine une sidebar principale retractable, une topbar legere et une zone `main`. La sidebar est ouverte par defaut sur desktop, compacte lorsqu'elle est reduite et hors du flux avec fond de fermeture sur les ecrans plus etroits. Un lien d'evitement, des landmarks nommes, un focus visible et des controles natifs posent l'accessibilite structurelle.

La seule route React fonctionnelle reste l'accueil. Les domaines autorises par les capacites de `/api/v1/me/` sont presentes comme liens HTML explicitement transitoires vers l'interface historique tant que leur route React n'existe pas. Cette presentation ne vaut jamais autorisation backend et ne determine pas l'architecture finale des domaines migres.

Les styles utilisent une couche globale limitee au reset, aux tokens semantiques, au theme clair et aux structures partagees, puis des CSS Modules pour les composants. Les couleurs fonctionnelles passent par des proprietes CSS semantiques afin qu'un futur theme sombre puisse les redefinir. Aucun theme sombre selectionnable n'est livre dans UX1.

Les primitives initiales sont limitees a `Button`, `IconButton`, `PageHeader`, `StatusBadge`, `Alert`, `LoadingState` et `EmptyState`. Les tables, filtres, paginations, formulaires, dialogs, tabs et composants metier attendent un cas reel. Les icones React proviennent de `lucide-react`, avec imports individuels, texte visible pour les actions importantes et noms accessibles pour les boutons compacts.

Le responsive distingue fonctionnellement grand desktop, laptop, tablette et telephone sans creer une application mobile distincte. Le shell preserve la largeur du contenu, replie la navigation sous 1024 px et simplifie les libelles secondaires sous 640 px. Les futurs tableaux conserveront une strategie specifique, a definir avec Employee R1.

## Socle API v1

Le premier contrat versionne est expose sous `/api/v1/`, dans un URLconf separe du routeur historique `/api/`. `GET /api/v1/me/` est public afin de permettre l'amorcage de la SPA : il renvoie seulement `is_authenticated: false` pour un visiteur anonyme et, pour une session authentifiee, l'identite Django minimale (`id`, nom d'utilisateur, prenom, nom, email) ainsi que les indicateurs globaux `is_staff` et `is_superuser`.

La reponse de `GET /api/v1/me/` force aussi la creation du cookie CSRF natif Django. Le futur client doit envoyer les cookies avec ses requetes (`credentials: "include"` en cas d'origine distincte) et recopier la valeur du cookie `csrftoken` dans l'en-tete `X-CSRFToken` pour toute requete non sure. `SessionAuthentication` applique alors le controle CSRF aux sessions authentifiees.

Les classes globales DRF restent, sans changement, `TokenAuthentication`, `BasicAuthentication` et `SessionAuthentication`. Le contrat cible de la SPA utilise la session ; la conservation a long terme de Token et Basic reste a decider apres audit de leurs usages existants.

## Authentification requise et capacites du frontend

LabsManager ne propose aucun mode fonctionnel anonyme. La reponse minimale `{"is_authenticated": false}` de `GET /api/v1/me/` sert uniquement a detecter une session absente ou expiree ; le frontend doit alors interrompre l'amorcage de l'application et orienter l'utilisateur vers l'authentification. Seul un utilisateur authentifie charge le shell React.

Pour un utilisateur authentifie, `me` expose un objet `capabilities` limite aux entrees du shell et au prochain ecran de liste des employes. Les noms du contrat sont fonctionnels ; leur calcul reste entierement cote Django :

| Capacite API | Permissions Django existantes | Usage Django actuel |
|---|---|---|
| `view_employee_list` | `common.employee_list` ou `staff.view_employee` | Lien Employes dans la barre et carte d'accueil ; la future API de liste devra encore appliquer son propre controle et son filtrage objet. |
| `view_team_list` | `common.team_list` ou `staff.view_team` | Lien Equipes dans la barre et carte d'accueil. |
| `view_contract_list` | `common.contract_list` ou `expense.view_contract` | Lien Contrats dans la barre et carte d'accueil. |
| `view_project_list` | `common.project_list` ou `project.view_project` | Lien Projets dans la barre et carte d'accueil. |
| `view_organizations` | `common.display_infos` | Lien Organisations dans la barre et carte d'accueil. |
| `view_calendar` | `common.display_calendar` ou `leave.view_leave` | Calendrier ; la page d'accueil accepte les deux droits, tandis que la barre Django historique ne teste que `common.display_calendar`. Le contrat v1 conserve l'union la plus permissive deja exposee par l'UI existante. |
| `view_dashboard` | `common.display_dashboard` | Lien Tableau de bord dans la barre et carte d'accueil. |
| `use_fund_finder` | `fund.view_fund` | Entree Recherche de fonds dans le menu Outils. |
| `import_data` | `common.import` | Entree Import dans le menu Outils. |

Ces booleens servent exclusivement a presenter ou masquer des elements d'interface. Ils ne constituent pas une autorisation : chaque endpoint conserve la responsabilite de verifier les permissions Django et, lorsque necessaire, les regles objet `django-rules`. Aucune logique de regle metier n'est dupliquee dans React.

## Convention d'autorisation des collections v1

Les capacites de `/api/v1/me/` pilotent uniquement la navigation et la presentation. Elles ne remplacent jamais le perimetre objet calcule par Django. Pour chaque collection v1, le backend doit d'abord reutiliser la logique metier existante du modele afin de borner le queryset, puis seulement appliquer recherche, filtres, tri et pagination. Une permission globale peut ouvrir l'ensemble du queryset tandis qu'un utilisateur sans cette permission peut conserver un perimetre relationnel limite. Cette convention sera appliquee endpoint par endpoint, sans abstraction generique prematuree.

## Liste des employes v1

`GET /api/v1/employees/` est une collection strictement en lecture seule et reservee aux utilisateurs authentifies. Son queryset initial est obligatoirement passe a `Employee.get_instances_for_user("view", user, queryset)`. Un utilisateur ayant `staff.view_employee` voit l'ensemble ; sinon la logique actuelle borne la reponse a son employe et a ses subordonnes visibles. Un perimetre vide produit une collection paginee vide, pas un refus lie a la capability de navigation.

Le contrat d'une ligne contient uniquement `id`, `first_name`, `last_name`, `entry_date`, `exit_date`, `is_active`, `current_statuses` et `superiors`. Les relations courantes sont prechargees avant serialisation. `contract_quotity` et `project_quotity` sont reportees : leurs methodes actuelles executent chacune une agregation SQL par employe et leur inclusion naive creerait un cout proportionnel au nombre de lignes.

La pagination reutilise le contrat limit/offset existant (`count`, `next`, `previous`, `results`), avec 25 elements par defaut et 250 au maximum. La recherche `search` porte uniquement sur prenom et nom. Les filtres retenus sont `is_active`, `status`, `current_status`, `superior` et `team`. Le tri est limite a `first_name`, `last_name`, `entry_date`, `exit_date` et `is_active`, avec `first_name,last_name,id` par defaut.

## Detail employe v1

`GET /api/v1/employees/<id>/` est le point d'entree minimal de la future fiche React. Il reutilise le meme perimetre de consultation, les memes prechargements et le meme serialiseur que la liste. Il etablit l'identite de la ressource, verifie son appartenance au perimetre visible et expose le noyau commun `id`, `first_name`, `last_name`, `entry_date`, `exit_date`, `is_active`, `current_statuses` et `superiors`. Il ne reproduit pas l'ensemble de la fiche HTML historique et n'expose notamment ni email, date de naissance, compte lie, contrat, projet, budget, contribution, absence, note ou information generique.

Le queryset est borne par `Employee.get_instances_for_user("view", user, queryset)` avant la recherche de la cle primaire. Un employe absent et un employe hors perimetre produisent donc tous deux un `404`, sans requete de distinction. Un utilisateur anonyme recoit un `401`.

Cette convention differe volontairement de la vue HTML historique, qui autorise notamment `is_staff` et teste `staff.change_employee` dans certains cas. L'API v1 conserve une separation nette entre consultation et modification en reutilisant la logique de consultation validee pour la liste. Le comportement HTML n'est pas modifie. Les autres blocs de la fiche seront ajoutes progressivement, par enrichissement justifie ou par endpoints specialises lorsque leurs donnees, leur cycle de vie ou leurs permissions l'exigeront.

## Sous-ressources Employee v1

Le noyau `GET /api/v1/employees/<id>/` reste volontairement leger. Les collections historiques ou fonctionnelles sont exposees par des sous-ressources lorsqu'elles ont leur propre contrat, leur propre volume ou leur propre evolution. Chaque sous-ressource commence par resoudre l'employe cible exclusivement dans le queryset produit par `Employee.get_instances_for_user("view", user, Employee.objects.all())`. Un identifiant absent ou hors perimetre produit le meme `404`, sans requete de distinction. Pour les futurs blocs sensibles, les permissions propres au domaine s'ajouteront a ce premier controle.

`GET /api/v1/employees/<id>/statuses/` expose l'historique complet des relations `Employee_Status` en lecture seule et sans pagination. Chaque element contient l'identifiant de la relation, le type dans la meme representation `id/code/name` que `current_statuses`, les dates, le code et le libelle Django du caractere contractuel ou statutaire, et l'etat actif calcule par `ActiveDateMixin.is_active`. L'ordre reprend la chronologie historique par date de fin croissante, place explicitement les relations sans date de fin en dernier, puis departage par date de debut croissante et identifiant.

`GET /api/v1/employees/<id>/hierarchy/` expose separement les relations directes `superiors` et `subordinates`, actuelles et historiques, sans pagination ni recursion. Chaque relation porte son propre identifiant, ses dates, l'etat actif calcule par `ActiveDateMixin.is_active` et seulement l'identite `id/first_name/last_name` de la personne liee. Les deux collections suivent l'ordre historique par date de fin croissante, relations ouvertes en dernier, puis date de debut et identifiant.

L'autorisation de cette sous-ressource porte sur l'employe cible, resolu dans le perimetre Employee v1. Une fois ce dernier visible, l'identite minimale d'une personne directement liee peut etre exposee meme si cette personne n'appartient pas elle-meme au perimetre general de la liste. Cette representation relationnelle ne donne aucun droit supplementaire : la fiche `GET /api/v1/employees/<linked_id>/` reste inaccessible et retourne `404` si la personne liee est hors perimetre.

`GET /api/v1/employees/<id>/project-participations/` expose en lecture seule les relations `Participant` de l'employe visible. Chaque element contient l'identifiant de la participation, le role code/libelle, les dates, la quotite decimale, l'etat temporel `is_active` et une reference Project limitee a `id`, `name`, `start_date` et `end_date`. La collection n'est pas paginee ; elle place les participations actives avant les historiques, puis les dates de fin et de debut les plus recentes avant les plus anciennes, et utilise l'identifiant comme dernier departage deterministe.

Cette sous-ressource applique une visibilite relationnelle propre au contexte Employee : une fois l'employe cible borne par `Employee.get_instances_for_user("view", ...)`, ses participations sont retournees sans filtrage supplementaire par `Project.get_instances_for_user("view", ...)`. La reference Project minimale explique la participation, mais ne confere aucun droit autonome sur le Project et ne prefigure pas sa fiche v1. Le futur lot Project devra definir explicitement la semantique de `Project.status`, sa relation avec l'activite temporelle et son perimetre de visibilite objet.

Le parametre optionnel `is_active=true|false` filtre en base selon la definition exacte de `ActiveDateMixin.is_active` : bornes absentes ouvertes, date de debut atteinte et date de fin non depassee, avec les deux bornes inclusives. Sans parametre ou avec une valeur booleenne invalide, la convention des filtres v1 conserve la collection complete.


## Moteur commun de filtres R1.1

Les décisions fonctionnelles durables figurent dans DECISIONS. L'implémentation commune réside dans `frontend/src/filters/` et ne dépend d'aucun domaine. `FilterBar` reçoit un catalogue, un registre de sources, les query parameters et une fonction de navigation ; il coordonne la galerie et les contrôles actifs. `FilterGallery` est un panneau non modal `role=dialog`, avec recherche locale des libellés (insensible aux accents), catégories déclarées et filtres déjà ajoutés désactivés. L'ajout ferme le panneau puis place le focus sur le contrôle vide ; fermer rend le focus au déclencheur. Échap et clic extérieur ferment le panneau, sans piège de focus. Les choix se parcourent avec Tab puis Entrée/Espace.

`types.ts` définit des unions discriminées : `static-choice`, `entity-search`, `dynamic-choice`, `date`, `text`, `number`, `range`. `SupportedFilter` limite volontairement les catalogues rendus aujourd'hui aux choix statiques mono-valeur et recherches d'entité mono-valeur. Les autres familles ont un contrat d'extension, pas un composant prétendument fonctionnel. `DynamicChoiceFilter` distingue mono-valeur et `multiple: true` avec encodage explicite `csv` ou `repeat` à fixer lors du branchement backend. `RangeFilter` impose deux noms de paramètres et un type date/nombre ; `RangeValue` autorise des bornes omises. Aucun filtre date/range/multiple n'est branché sur Employee.

Une source courte a seulement `loadAll(signal)` ; une source distante a `search(text, signal)` (options + indicateur de résultats supplémentaires) et `resolve(id, signal)` (option ou null). Les sources métier adaptent les contrats API en `{value,label}`. Les définitions contiennent une référence de source, pas des fonctions. Les nomenclatures et les collections courtes ne sont pas copiées dans le frontend ; leur chargement complet et résolution locale seront implémentés à leur premier branchement réel.

`EntitySearch` est une combobox avec debounce 300 ms, suggestions bornées, chargement/erreur/réessai/aucun résultat, flèches haut/bas et validation Entrée. Échap annule le texte de recherche non appliqué et conserve l'ID courant. Saisir un nom ne change pas le filtre tant qu'une suggestion n'est pas choisie ; la valeur actuellement appliquée reste alors indiquée. Les requêtes remplacées sont annulées et les réponses tardives ignorées. Un ID introuvable/hors scope reste visible comme indisponible et peut être remplacé ou supprimé ; aucune disparition silencieuse du critère.

`url.ts` normalise les paramètres supportés, modifie/supprime une instance et réinitialise le catalogue sans écraser les paramètres étrangers. La page fournit les paramètres de pagination à effacer (`offset` pour Employee). Exemple : `?superior=` conserve un filtre ajouté en attente de valeur, `?superior=42` applique l'ID ; seules les valeurs non vides partent à l'API. Refresh et back/forward restaurent aussi les contrôles vides. L'ajout et le choix de valeur créent donc deux étapes d'historique. La sérialisation de la requête serveur sert de clé des résultats : ajouter un contrôle vide, à pagination inchangée, ne recharge pas inutilement la table.

Le catalogue Employee reste `config/employeeFilters.ts` : Activité, catégorie Situation, et Supérieur, catégorie Relations. `config/employeeFilterSources.ts` réutilise `GET /api/v1/employees/?search=...&limit=10` sans les filtres de la table ; aucun téléchargement de toutes les pages. Un message invite à affiner si d'autres résultats existent. La résolution utilise `GET /api/v1/employees/<id>/`. Le client HTTP session/401/403 existant reste unique. Le moteur n'interprète jamais les permissions ni la relation de supérieur.

Depuis UX2, la galerie utilise un Popover shadcn de 20rem maximum avec des lignes compactes par catégorie. La barre active revient à la ligne. EntitySearch utilise la Combobox shadcn ; sources, debounce et sérialisation restent identiques. La sélection de ligne R1 reste indépendante.


## Design System UX2

shadcn/ui (Base UI, style base-nova) constitue la référence pour les nouvelles interfaces React ; Lucide reste la bibliothèque d'icônes unique. Les primitives locales sont dans `src/components/ui/`, configurées par `components.json`, avec `cn` dans `src/lib/utils.ts`. Tailwind v4 est intégré au plugin Vite ; les CSS Modules conservent les layouts et styles métier. Les wrappers historiques Button/StatusBadge délèguent aux primitives, sans seconde implémentation visuelle.

Les thèmes Teal Light/Dark définissent les mêmes tokens sémantiques dans `styles/tokens.css`. Les alias historiques permettent la transition des autres pages. La classe racine `dark` sélectionne la palette ; le bouton de topbar mémorise seulement le choix local au navigateur (préférence système au premier affichage), sans synchronisation avec les préférences Django. Ajouter une palette doit changer les tokens, pas les composants.

Direction commune : sections par défaut, Card seulement pour une unité autonome ; typographie fonctionnelle compacte, surfaces discrètes, boutons pleins rares. Employee List est le seul pilote métier UX2. Son tableau HTML conserve clic/clavier et lien indépendant ; la cellule d'actions réservée affiche un DropdownMenu au survol/focus ou après sélection. Le menu sélectionne la ligne et propose uniquement ouvrir la fiche Django/désélectionner.
