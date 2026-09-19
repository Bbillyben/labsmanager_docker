# Etat de la migration React

Current state
- UI Django/jQuery fonctionnelle, API historique sous `/api/` et socle versionne valide sous `/api/v1/`, avec capacites utilisateur, liste et detail minimal des employes v1, PostgreSQL et worker Django-Q.
- Socle React/Vite TypeScript valide sous `/app/`, avec bootstrap de session, client HTTP session/CSRF et tests.
- UX1 et AUTH1 valides sur Debian et dans le navigateur : shell, session Django, connexion/deconnexion React et liens historiques.
- R1 : retour fonctionnel positif sur la VM ; sélection au clic conservée.
- R1.1 — validé fonctionnellement par retour utilisateur : moteur commun, galerie, filtres Activité et Supérieur.
- Depot de distribution a la racine, avec `backend/` comme sous-module Django officiel et `frontend/` versionne dans le depot racine.

Completed
- Architecture, dependances, demarrage, routes, authentification, statiques, proxy et distribution inventories.
- Decisions et matrice initiales documentees ; aucun comportement applicatif modifie.
- Chaine Docker/distribution adaptee au sous-module source `backend/` ; chemins internes de l'image conserves.
- Socle `/api/v1/` valide sur la VM Debian : utilisateur courant, session Django, amorcage CSRF et compatibilite du routage historique.

Next recommended lot
- R1.1 validé fonctionnellement ; attendre une demande explicite avant R2 ou toute évolution backend des actions.

Following lot
- Ne pas engager automatiquement la migration Project avant clarification de son contrat et de ses permissions.

Known issues / questions
- Le CLI Docker n'est pas disponible sur la VM inspectee ; le build reel et la validation Compose restent a executer sur l'hote de distribution.
- Confirmer si Token/Basic doivent rester actifs et harmoniser les permissions des endpoints v1.

## Lot API v1 - session et CSRF

Completed
- Espace de routage `/api/v1/` ajoute sans modification des endpoints historiques `/api/`.
- `GET /api/v1/me/` ajoute pour l'amorcage anonyme ou authentifie par session.
- Cookie CSRF initialise par la reponse de `me`; controle CSRF DRF conserve pour les requetes authentifiees non sures.
- Tests cibles ajoutes pour la reponse anonyme, la session authentifiee, le contenu minimal, le CSRF et la resolution de `/api/users/`.
- Configuration DRF auditee : Token, Basic et Session restent actives sans changement.

Validation Debian
- `python3 manage.py test labsmanager.tests.test_api_v1 --verbosity 2` : 4 tests decouverts et reussis (`Ran 4 tests in 3.162s`, `OK`) ; creation puis destruction correcte de `test_django_db`.
- Le message `Forbidden: /api/v1/me/` pendant le test CSRF est attendu et le test correspondant reussit.
- `python3 manage.py check` : `System check identified no issues (0 silenced).`

Next recommended lot
- Choisir le prochain bloc fonctionnel apres la validation de la section Employee en lecture seule.

## Lot P0 - Capacites utilisateur

Completed
- Audit des decisions de navigation Django et du controle actuel de la liste des employes.
- Neuf capacites fonctionnelles ajoutees a la reponse authentifiee de `/api/v1/me/`, calculees exclusivement avec les permissions existantes.
- Reponse anonyme minimale conservee uniquement pour detecter une session absente ou expiree ; LabsManager reste une application entierement authentifiee.
- Tests etendus aux utilisateurs sans droits, avec droits et superutilisateurs.
- Aucune permission, regle `django-rules`, API historique ou logique frontend modifiee.

Validation Debian
- `python3 manage.py test labsmanager.tests.test_api_v1 --verbosity 2` : 6 tests decouverts et reussis (`Ran 6 tests in 6.270s`, `OK`) ; creation puis destruction correcte de `test_django_db`.
- Les cas anonyme, sans droits, avec droits, superutilisateur, CSRF et routage historique sont valides.
- Le message `Forbidden: /api/v1/me/` pendant le test CSRF est attendu.
- `python3 manage.py check` : `System check identified no issues (0 silenced).`

## Lot P1 - Liste des employes v1

Completed
- `GET /api/v1/employees/` ajoute en lecture seule, sans modification de `/api/employee/`.
- Acces reserve aux sessions authentifiees ; le perimetre est borne par `Employee.get_instances_for_user("view", user, queryset)` avant toute autre operation.
- Contrat minimal limite a l'identite, aux dates, a l'etat actif, aux statuts courants et aux superieurs courants.
- Pagination limit/offset, recherche sur le nom, filtres relationnels explicites et tri scalaire en place.
- `contract_quotity` et `project_quotity` reportees pour eviter deux agregations SQL supplementaires par ligne.
- Tests cibles ajoutes pour authentification, droits globaux, perimetre limite ou vide, non-contournement, pagination, recherche, filtres, tri et contrat de reponse.
- Aucun modele, migration, `rules.py`, endpoint historique, template ou frontend modifie.

Validation Debian
- `python3 manage.py test labsmanager.tests.test_api_v1 labsmanager.tests.test_api_v1_employees --verbosity 2` : 16 tests decouverts et reussis (`Ran 16 tests in 20.130s`, `OK`) ; creation puis destruction correcte de `test_django_db`.
- Les perimetres global, relationnel et vide, le non-contournement par recherche ou filtre, la pagination, les filtres, le tri et le contrat minimal sont valides.
- Les messages `Forbidden: /api/v1/me/` et `Unauthorized: /api/v1/employees/` sont attendus dans leurs tests respectifs.
- `python3 manage.py check` : `System check identified no issues (0 silenced).`

## Lot P1 - Detail employe v1

Completed
- `GET /api/v1/employees/<id>/` ajoute en lecture seule avec le meme contrat que chaque ligne de la liste v1.
- Recherche de la ressource limitee au queryset produit par `Employee.get_instances_for_user("view", user, queryset)` ; une ressource absente ou hors perimetre produit le meme `404`.
- Statuts courants et superieurs courants uniquement precharges ; aucune relation supplementaire de la fiche historique n'est chargee.
- Serialiseur P1 reutilise sans modification ; email, date de naissance et informations administratives restent absents.
- Divergence d'autorisation avec la fiche HTML historique documentee sans modifier son comportement.
- Tests ajoutes pour les droits global et relationnel, la fiche propre, l'anonymat, les deux cas `404`, le contrat et le non-contournement par identifiant.
- Aucun modele, migration, `rules.py`, endpoint historique, template ou frontend modifie.

Validation Debian
- `python3 manage.py test labsmanager.tests.test_api_v1 labsmanager.tests.test_api_v1_employees --verbosity 2` : 23 tests decouverts et reussis (`Ran 23 tests in 29.349s`, `OK`) ; creation puis destruction correcte de `test_django_db`.
- Les reponses journalisees `Unauthorized` pour les acces anonymes, `Not Found` pour les employes absents ou hors perimetre et `Forbidden` pour le controle CSRF sont attendues dans leurs tests respectifs.
- `python3 manage.py check` : `System check identified no issues (0 silenced).`

## Lot Employee - Historique des statuts v1

Completed
- `GET /api/v1/employees/<id>/statuses/` ajoute en lecture seule, sans pagination, recherche, filtres ou tri parametrique.
- Employe cible resolu exclusivement dans le perimetre produit par `Employee.get_instances_for_user("view", user, Employee.objects.all())` avant le chargement des statuts.
- Contrat limite a la relation, au type `id/code/name`, aux dates, au code/libelle de contractualite et a l'etat actif existant.
- Representation du type factorisee et reutilisee par `current_statuses`, dont le contrat reste inchange.
- Ordre deterministe par date de fin croissante, valeurs ouvertes en dernier, puis date de debut et identifiant.
- Tests ajoutes pour authentification, droits global et relationnel, fiche propre, deux cas `404`, historique vide, historique mixte, contrat, ordre et absence d'indicateurs d'edition.
- Aucun modele, migration, `rules.py`, endpoint historique, template ou frontend modifie.

Validation Debian
- `python3 manage.py test labsmanager.tests.test_api_v1 labsmanager.tests.test_api_v1_employees --verbosity 2` : 31 tests decouverts et reussis (`Ran 31 tests in 40.169s`, `OK`) ; creation puis destruction correcte de `test_django_db`.
- Les reponses journalisees `Unauthorized` pour les acces anonymes, `Not Found` pour les employes absents ou hors perimetre et `Forbidden` pour le controle CSRF sont attendues dans leurs tests respectifs.
- `python3 manage.py check` : `System check identified no issues (0 silenced).`

## Lot Employee - Hierarchie directe et historique v1

Completed
- `GET /api/v1/employees/<id>/hierarchy/` ajoute en lecture seule, sans pagination, recursion, recherche, filtres ou tri parametrique.
- Employe cible borne par `Employee.get_instances_for_user("view", user, Employee.objects.all())` ; une cible absente ou hors perimetre produit le meme `404`.
- Reponse separee en relations directes `superiors` et `subordinates`, avec identifiant de relation, identite minimale liee, dates et etat actif existant.
- Identite minimale d'une personne liee visible avec la relation, sans elargir son propre acces au detail Employee.
- Deux prechargements avec `select_related` evitent une requete par relation et ne chargent aucun autre bloc Employee.
- Ordre deterministe par date de fin croissante, relations ouvertes en dernier, puis date de debut et identifiant.
- Docstrings Google style ajoutees aux vues, serialiseurs et methodes non triviales du lot.
- Huit tests ajoutes pour authentification, perimetres global et relationnel, deux cas `404`, collections vides, contrats courant/historique, ordre, minimalite et personne liee hors perimetre.
- Aucun modele, migration, `rules.py`, endpoint historique, template ou frontend modifie.

Validation Debian
- `python3 manage.py test labsmanager.tests.test_api_v1 labsmanager.tests.test_api_v1_employees --verbosity 2` : 39 tests decouverts et reussis (`Ran 39 tests in 50.731s`, `OK`) ; creation puis destruction correcte de `test_django_db`.
- Les reponses journalisees `Unauthorized` pour les acces anonymes et `Not Found` pour les cibles absentes, hors perimetre ou les fiches liees non autorisees sont attendues dans leurs tests respectifs.
- `python3 manage.py check` : `System check identified no issues (0 silenced).`

## Lot Employee - Participations aux projets v1

Completed
- `GET /api/v1/employees/<id>/project-participations/` ajoute en lecture seule, sans pagination ni route Project v1.
- Employe cible borne exclusivement par `Employee.get_instances_for_user("view", user, Employee.objects.all())` ; une cible absente ou hors perimetre produit le meme `404`.
- Participations retournees sans filtre de visibilite Project supplementaire ; la reference Project minimale ne confere aucun droit autonome sur ce Project.
- Contrat limite a la relation, au Project `id/name/start_date/end_date`, au role code/libelle, aux dates, a la quotite et a l'etat temporel existant.
- Filtre optionnel `is_active=true|false` traduit exactement les bornes inclusives de `ActiveDateMixin.is_active` en conditions ORM ; valeur invalide ignoree comme pour les booleens v1 existants.
- Ordre deterministe : actives d'abord, puis dates de fin et de debut decroissantes, puis identifiant croissant.
- Tests ajoutes pour authentification, perimetres global et relationnel, deux cas `404`, collection vide, contrat, roles, quotite, ordre, bornes temporelles et visibilite relationnelle sans visibilite Project.
- Aucun modele, migration, `rules.py`, endpoint historique, frontend ou comportement Project modifie.

Validation Debian
- `python3 manage.py test labsmanager.tests.test_api_v1 labsmanager.tests.test_api_v1_employees --verbosity 2` : 48 tests decouverts et reussis (`Ran 48 tests in 63.550s`, `OK`) ; creation puis destruction correcte de `test_django_db`.
- Les reponses journalisees `Unauthorized`, `Not Found` et `Forbidden` correspondent aux tests de refus attendus.
- Les avertissements DRF sur les validateurs decimaux `max_value` et `min_value` n'ont pas provoque d'echec et ne remettent pas en cause la validation du lot.
- `python3 manage.py check` : `System check identified no issues (0 silenced).`

Point futur Project
- Clarifier ensemble `Project.status`, l'activite temporelle du modele et le perimetre de visibilite objet avant de stabiliser les endpoints Project v1.

## Lot R0 - Socle du frontend React

Completed
- Scaffold JSX remplace par React 19 + TypeScript, sans modification du backend ni de l'interface Django historique.
- React Router monte sous `/app`, avec accueil protege et route 404 ; aucune route Employee n'est encore creee.
- Client HTTP de meme origine avec cookies de session, lecture JSON/sans contenu, erreurs HTTP typees, annulation et en-tete CSRF pour les methodes non sures.
- Contexte de session amorce par `/api/v1/me/`, avec etats explicites et invalidation centralisee sur `401` uniquement.
- Ecran de connexion requise dirige vers Django avec `next=/app/`; shell minimal affichant l'identite et un lien normal vers l'interface historique.
- Tests Vitest/React Testing Library ajoutes pour le transport HTTP, le CSRF, les etats de session et le routage.
- Aucune integration Docker/Nginx et aucune interface metier ajoutees.

Validation Debian
- `npm install --package-lock-only` puis `npm ci` executes avec succes ; verrou npm regenere et 270 packages audites.
- `npm test` : 3 fichiers et 13 tests reussis avec Vitest (`3 passed`, `13 passed`).
- `npm run typecheck` : reussi sans erreur.
- `npm run lint` : reussi sans erreur.
- `npm run build` : reussi avec Vite 7.2.6, 55 modules transformes et artefacts produits dans `dist/`.
- npm signale 14 vulnerabilites de dependances (1 faible, 3 moderees, 10 elevees). Elles restent a auditer separement ; aucun `npm audit fix` automatique n'a ete applique.

Next
- Cadrer le lot UX/UI avant de commencer les ecrans Employee React.

## Lot UX1 - Fondations visuelles et structurelles

Completed
- Shell cible construit autour d'une sidebar retractable, d'une topbar legere et d'un contenu principal semantique.
- Navigation React limitee a l'accueil ; liens historiques transitoires filtres par les neuf capacites existantes, sans nouvelle capacite ni faux ecran React.
- Tokens semantiques, echelle d'espacement compacte, theme clair et CSS Modules introduits ; architecture compatible avec un futur theme sombre.
- Accessibilite structurelle : lien d'evitement, landmarks, navigation nommee, focus visible, boutons natifs et preferences de mouvement reduit.
- Responsive du shell pour desktop, laptop, tablette et telephone, sans architecture mobile distincte.
- `lucide-react` retenu pour les icones SVG React, sous reserve de regeneration et validation du lockfile Debian.
- Primitives creees : `Button`, `IconButton`, `PageHeader`, `StatusBadge`, `Alert`, `LoadingState` et `EmptyState`.
- Tables, filtres, pagination, formulaires, dialogs, selection de ligne et actions metier volontairement differes jusqu'a Employee R1.
- Le pattern selection et barre d'actions reste une hypothese a comparer ; selection et navigation demeurent distinctes, et toute action Employee exigera un audit des permissions objet.
- Aucun backend, endpoint, modele, migration, Docker ou Nginx modifie.

Validation
- Validation automatique Debian reussie avec le lot AUTH1 : 25 tests Vitest, lint, typecheck et build Vite sans erreur.
- Validation navigateur reussie : shell et navigation accessibles apres connexion, et liens transitoires diriges vers l'interface Django historique.

## Lot AUTH1 - Connexion et deconnexion React

Completed
- Audit classe en scenario B : django-allauth 0.63.3 porte une politique utile qui doit etre preservee, notamment l'authentification identifiant/email et les limites `login`/`login_failed`.
- `POST /api/v1/auth/login/` reutilise `LoginForm`, l'adapter et les backends existants ; succes minimal, erreurs generiques non enumerantes et quota depasse sont exposes en JSON.
- `POST /api/v1/auth/logout/` ferme la session Django ; les deux routes sont POST-only et explicitement protegees par CSRF.
- Page publique `/app/login`, retour interne sur la destination demandee, rafraichissement de `/api/v1/me/` et deconnexion depuis la topbar ajoutes.
- Les liens historiques utilisent `VITE_DJANGO_PUBLIC_URL`; Vite ne proxifie plus `/accounts` et conserve uniquement `/api`.
- Le logo historique est copie dans les assets appartenant au frontend et utilise pour la connexion, la sidebar et le favicon.
- Inscription/invitation, mot de passe et emails restent dans les workflows Django/allauth existants.
- Validation backend Debian : 9 tests AUTH1 reussis en 27.292 s, base de test creee puis detruite correctement et `manage.py check` sans anomalie. Les reponses `400`, `403`, `405` et `429` journalisees correspondent aux refus et limites attendus.
- Validation frontend Debian : 5 fichiers et 25 tests Vitest reussis, lint et typecheck sans erreur, puis build Vite 7.2.6 reussi avec 1933 modules transformes.
- npm continue de signaler les 14 vulnerabilites connues (1 faible, 3 moderees, 10 elevees) ; aucun `npm audit fix` automatique n'a ete applique.
- Validation navigateur reussie : erreur generique avec de mauvais identifiants, connexion valide, retour dans l'application, liens historiques diriges vers Django et deconnexion avec retour a `/app/login`.

Next
- AUTH1 et UX1 sont valides. Le prochain lot peut reprendre la migration fonctionnelle Employee React.


## Lot R1 — Liste Employee React

**R1 — implémenté mais non validé.** La validation navigateur appartient à l'utilisateur.

### Reprise et divergences documentaires

Les cinq documents de `docs/react-migration/` ont été lus intégralement avant inspection ciblée. Les contrats Employee v1 et AUTH1 concordent avec le code. Les paragraphes initiaux d'ARCHITECTURE décrivant seulement l'accueil, le proxy `/accounts` et le port 8000, ainsi que l'attente UX1 dans COMMANDES, sont des descriptions anciennes, supplantées par les sections AUTH1 et le présent lot. Aucun nouvel audit global ni changement de l'architecture de développement. Les modifications antérieures non commitées sont conservées.

### Écran et contrat utilisés

- Route protégée `/app/employees/`, destination de la sidebar Employés lorsque `view_employee_list` est présent. La route directe laisse l'API décider du périmètre, sans reproduire la capability comme permission objet.
- `GET /api/v1/employees/` via le client HTTP session existant. Types locaux pour `count/next/previous/results`, identité, dates nullables, activité, statuts `id/code/name` et supérieurs `id/first_name/last_name`.
- Colonnes : employé (prénom + nom), statuts actuels, supérieurs en texte, entrée, sortie, activité. Dates civiles `JJ/MM/AAAA` sans conversion de fuseau ; null représenté par un tiret. Aucune activité ni aucun statut recalculés.
- Recherche sur prénom/nom, soumise avec Entrée ou Rechercher : pas de requête à chaque frappe, aucun second filtrage client. Filtre Activité ajouté à la demande via « Ajouter un filtre », valeurs Actifs/Inactifs ; aucun filtre par défaut (Tous), contrairement au filtre historique `active=1`.
- Tri serveur par prénom depuis l'en-tête Employé, entrée, sortie et activité, croissant/décroissant. `last_name` reste accepté dans une URL partagée. Sans paramètre, ordre backend `first_name,last_name,pk`. Statuts et supérieurs ne sont pas triables.
- Pagination exclusivement limit/offset : 25 par défaut, `limit` URL de 1 à 250, compte total et plage affichée, précédent/suivant et page courante. Les URLs absolues de pagination ne sont pas suivies : seule la route relative v1 est appelée. Une page devenue vide propose Première page.
- État persistant dans `search`, `is_active`, `ordering`, `limit`, `offset`. Recherche/filtre/tri réinitialisent offset ; reset enlève recherche et activité, conserve tri/taille. Les changements créent une entrée navigateur, refresh et back/forward restaurent les contrôles. Paramètres inconnus/non supportés supprimés, nombres invalides normalisés, limite plafonnée ; normalisation par remplacement d'historique.
- Chargement local au tableau, avec hauteur réservée ; le shell et les filtres restent utilisables. Pas de cache, ni conservation de données précédentes. Les requêtes remplacées sont annulées et leurs réponses tardives ignorées.
- Collection vide, aucun résultat filtré, page hors résultats et erreur locale distingués. Réessayer conserve l'URL. `401` invalide la session via AUTH1 et conserve la destination de retour ; `403` affiche une interdiction locale sans logout.
- Sélection unique au clic sur la ligne, hors éléments interactifs et sélection de texte. Ligne focusable : Entrée/Espace sélectionne ou désélectionne ; `aria-selected`, coche et bordure complètent la couleur. Le nom reste un lien indépendant. Le bouton contextuel Désélectionner rend le focus à la ligne. Sélection effacée au changement d'URL/rechargement des résultats.
- Zone contextuelle nommée avec l'employé sélectionné, limitée à Ouvrir la fiche (Django) et Désélectionner. Aucun bouton d'écriture/Admin ni permission supposée.
- Nom et ouverture contextuelle : lien HTML `getDjangoUrl('/staff/employee/<id>')`, sans slash final conformément au routage historique, sans fausse fiche React. Retour navigateur vers la liste conservant l'URL. L'accès à la fiche historique reste contrôlé par Django, dont la divergence de permission avec v1 était déjà documentée ; être visible dans v1 n'est pas présenté comme une garantie d'ouverture historique.
- HTML sémantique table, caption, en-têtes de colonne/ligne, boutons de tri avec `aria-sort`, contrôles labellisés, région contextuelle nommée, compte annoncé et erreurs en alerte. Focus visible UX1 conservé. Tableau dense (lignes minimales 44 px, boutons 36 px), retour à la ligne pour relations multiples, région de scroll horizontal focusable sur petites largeurs ; aucune transformation en cards.
- Pas de DataGrid, TanStack Table, sélection multiple, export, framework de tableaux/actions ou nouvelle dépendance.

### Audit fonctionnel ciblé A/B/C/D

Sources : `templates/employee/employee_base.html`, `data/static/js/employee_base.js`, `data/static/js/tables/tables_formatters.js`, `tables_filters.js`, wrapper `data/static/js/labsmanager/tables.js` et filtres persistants historiques.

| Catégorie | Historique / correspondance v1 | Traitement R1 |
|---|---|---|
| A | Identité, dates, statut courant, supérieurs, activité ; recherche ; tri scalaire ; pagination serveur | Implémentés avec le contrat v1 et l'URL React |
| B | Filtres statut passé/courant, supérieur par identifiant, équipe ; tri par nom de famille via URL ; taille via limit | Filtres relationnels différés ; taille restaurable sans sélecteur dédié. Un sélecteur de statut/supérieur exige une source d'options complète et autorisée, non déduite de la seule page courante |
| C | Infos génériques (`view_genericinfo`), quotités contrats/projets, badges équipe/leader, organigramme/modal équipes, export ; filtre historique `superior_name` textuel | Absents du contrat list ou liés à d'autres domaines ; non reconstruits en React. Hiérarchie v1 disponible mais UI hors R1 |
| D | Créer, modifier, supprimer, accès Django Admin | Aucun affichage React, autorisations à stabiliser dans un lot dédié |

La liste historique utilise Bootstrap Table, recherche/pagination serveur, choix de taille 10/25/50/100/250, préférences de colonnes et filtres stockés localement. Les filtres exposés incluent activité, nom, nom du responsable, statut passé/courant et équipe ; les paramètres v1 ne sont pas tous identiques. Le nom legacy n'est un lien que lorsque le serializer historique fournit `has_perm`. R1 utilise une navigation explicite vers Django sans répliquer ce calcul ni modifier sa vue.

### Audit ciblé des actions historiques et permissions

| Action | URL/vue et affichage historique | Contrôle observé / besoin futur |
|---|---|---|
| Ouvrir | `/staff/employee/<pk>`, `EmployeeView` ; lien si `row.has_perm` | Vue : connexion, puis `is_staff` ou `staff.view_employee`, sinon propre employé ou `staff.change_employee` objet. Divergence v1 connue ; Django garde la décision. React ne déduit aucune permission objet |
| Modifier / changer l'activité | `/staff/employee/<pk>/udpate` (orthographe réelle), `EmployeeUpdateView`, `EmployeeModelForm` contenant `is_active` ; bouton si `staff.change_employee` global | Vue locale LoginRequired + BSModalUpdateView, formulaire sans contrôle objet explicite. Règles `staff.change_employee` objet existantes (self_edit ou subordonné), mais elles ne sont pas invoquées explicitement ici. Avant migration : auditer/verrouiller l'autorisation serveur effective et son exposition |
| Supprimer | `/staff/employee/<pk>/delete`, `EmployeeRemoveView` ; bouton si `staff.delete_employee` global | Vue LoginRequired ; mixin `BSmodalDeleteViwGenericForeingKeyMixin.post` résout l'objet puis `delete()` sans contrôle objet explicite. Pas de désactivation distincte trouvée sur la liste. Aucune transposition R1 ; futur contrat et confirmation explicite requis |
| Admin | `/admin/staff/employee/<pk>/change/`, `EmployeeAdmin(ImportExportModelAdmin)` | Colonne affichée seulement si change OU delete global, puis lien si `is_staff`. Aucun override local d'autorisation dans EmployeeAdmin ; accès réel soumis aux contrôles Admin (compte actif/staff, droits view/change et contrôles hérités). `/me/` expose staff/superuser mais pas les permissions modèle/Admin effectives : insuffisant pour afficher correctement le lien |
| Créer | `/staff/employee/add/`, `EmployeeCreateView` ; bouton via `has_project_add_perm` | Anomalie locale historique : le template emploie le helper Project, pas `has_employee_add_perm` ; il teste add_project puis change_project ou employé lié. Vue LoginRequired, création éventuelle d'une relation de supérieur. Aucun changement dans R1 |
| Organigramme / équipes | `/staff/ajax/<pk>/org_chart_modal`, `/staff/ajax/<pk>/empl_team_lead` | Icônes conditionnées par `has_subordinate`/supérieurs et `is_team_leader`/`is_team_mate`. Fonctions de rendu locales sans contrôle explicite dans leur corps ; données/contextes hors contrat list, migration différée |

Les conditions du template ne prouvent pas l'autorisation backend. Ce constat est ciblé sur les actions de liste, sans réaudit des scopes v1. Une future exposition calculée côté backend (éventuellement `allowed_actions` après clarification des règles) devra couvrir écriture et accès Admin ; aucun endpoint ajouté dans R1. Les capacités `/me/` continuent de servir uniquement à la navigation globale.

### Vérifications R1

Résultats automatisés consignés en fin de lot dans COMMANDES. Tests frontend ciblés couvrant rendu, URL, recherche, activité, reset, tri, pagination, historique navigateur, sélection, liens, états, annulation et refus HTTP ; suites R0/UX1/AUTH1 conservées. Aucun test backend ajouté ; suite v1 existante utilisée.

Validation manuelle attendue : parcours de liste, lisibilité/densité, recherche/filtre/reset, tri/pagination, refresh/back/forward, sélection/changement/désélection et fiche Django, états locaux, laptop/mobile, clavier/focus et console. Ne pas engager R2 ni modifier le backend des actions avant retour utilisateur.


### Retour VM et ajustements UX R1

L'utilisateur confirme le bon fonctionnement réel (connexion, accès à la liste), mais demande de revoir sélection et présentation des filtres. Le fonctionnement initial est confirmé ; **les ajustements UX restent à valider manuellement**, R1 n'est pas déclaré entièrement validé.

- Suppression de la colonne et des boutons « Sélectionner ». Le clic sur une ligne bascule sa sélection ; le nom ouvre exclusivement la fiche. Clavier Entrée/Espace sur la ligne, sans intercepter les interactions du lien.
- Bouton « Ajouter un filtre » ouvrant un panneau compact : choisir Activité puis Actifs/Inactifs ajoute le critère. Seuls les filtres actifs ont un contrôle visible, avec suppression individuelle. Fermeture explicite ou Échap depuis le panneau ; focus rendu au déclencheur. Les paramètres URL restent la source persistante.
- Catalogue déclaratif dans `frontend/src/config/employeeFilters.ts` : libellés, clé API et options séparés de la page ; affichage dans `EmployeeFilters.tsx`. Comme le script JS historique, ce catalogue appartient à l'interface et nécessite un build pour être modifié ; ce n'est pas une configuration servie dynamiquement par Django. Aucun endpoint de métadonnées ou source d'options inventé. Seule Activité est disponible pour le moment ; les filtres relationnels restent différés.
- Tests adaptés à la sélection de ligne, à la navigation indépendante, au retour de focus, à l'ajout/suppression progressifs et à Échap. Les comportements URL et historique navigateur restent couverts.


## Lot R1.1 — Moteur commun et galerie de filtres

**R1.1 validé fonctionnellement par l’utilisateur** (« ok pour fonctionnalité »). Le retour fonctionnel positif R1 est acquis ; le fonctionnement du nouveau système de filtres est confirmé. Cette section remplace la description du panneau provisoire R1 ci-dessus.

### Mini-audit ciblé du legacy

Lecture intégrale de `backend/data/static/js/tables/tables_filters.js`, sans suivi des domaines associés. Le fichier déclare des booléens (`bool`), dates (`date`), textes implicites, choix statiques (Tasks/Milestones) et choix alimentés par variables (`employee_status_codes`, `teams_codes`, nomenclatures et institutions). Aucune option fonction/callback n'est effectivement déclarée dans ce fichier ; pas de multi-valeur ni de range explicite. Les filtres numériques `available` sont des seuils minimum décrits textuellement, sans type numérique dédié. Les relations sont des choix ou recherches de nom. Dates `after`/`before` correspondent à deux critères distincts historiques.

Association des catalogues par égalité de nom (employee/project/project_orga/leave/teams) ou préfixe (contract/funditem/budget/contrib/milestones/expense). Les cas `stale`, `ongoing`, `delayed`, `incomming` sont des critères métier particuliers et non des capacités manquantes du moteur. Aucun écart architectural bloquant. Migration des autres domaines, anciens raccourcis par préfixe et valeurs préchargées différée ; les familles typées couvrent les besoins futurs sans couplage au legacy.

### Livré

- Moteur transversal dans `filters/`, catalogue Employee séparé et adaptateur de source distinct. Structure et limites exactes dans ARCHITECTURE ; décisions durables dans DECISIONS.
- Galerie compacte et recherchable, catégories Situation/Relations, indicateurs « Déjà ajouté », ajout unique sans choix de valeur dans la galerie. Contrôles actifs éditables, suppression et reset des seuls filtres ; recherche de liste conservée par ce reset. Le reset global R1 peut toujours enlever recherche et filtres ensemble.
- Activité : choix statique mono-valeur Actifs/Inactifs, paramètre `is_active=true|false`. Contrôle vide au premier ajout.
- Supérieur : recherche distante Employee v1 bornée à 10 résultats, filtre serveur `superior=<id>` déjà validé. Suggestions limitées au scope Employee normal ; résolution après refresh par détail v1. Aucune nouvelle route ou modification backend.
- URL source persistante, y compris contrôles ajoutés sans valeur sous forme `parameter=` ; les valeurs vides ne partent pas au serveur. Recherche/tri/pagination R1 conservés. Relations sérialisées par identifiant, jamais par nom.
- Accessibilité : focus à l'ouverture/restitution/ajout, Échap, boutons natifs dans la galerie, combobox avec listbox et flèches/Entrée, libellés, erreurs locales, focus visible. Galerie et barre adaptatives. Sélection de ligne au clic/clavier, lien Employee indépendant, sans bouton Sélectionner.

### Limites et besoins différés

`status`, `current_status`, `superior`, `team` sont bien des NumberFilter scalaires dans Employee v1. Supérieur dispose de ses sources liste/détail validées et est branché. Statut nécessite encore une route v1 de nomenclature Employee_Type (`id/code/name`) ; pour plusieurs valeurs, il faut en plus un filtre serveur acceptant une liste avec sémantique OR/IN validée. Proposition minimale pour un futur lot : exposer cette petite nomenclature en lecture seule et étendre explicitement le filtre de statut concerné avec tests de contrat. Aucune modification réalisée ni représentation multi-valeur imposée avant ce contrat (CSV/répétition ne fonctionne pas avec le NumberFilter actuel). Team reste sans source v1, hors périmètre.

Contrôles réellement livrés : choix statique simple et recherche distante d'entité simple. Choix dynamiques courts, multi-sélection, date, texte, numérique et range sont des extensions typées, pas des contrôles exposés artificiellement. Les ranges prévoient borne basse seule, haute seule ou les deux, sans comparaison métier frontend. Aucune source Project/Team/Contract/Organization/Fund ni valeur métier globale ajoutée. Aucune dépendance, backend, modèle, migration ou permission modifiés.

### Fichiers R1.1

Créés : `frontend/src/filters/{types.ts,url.ts,FilterBar.tsx,FilterGallery.tsx,EntitySearch.tsx,Filters.module.css,FilterBar.test.tsx,url.test.ts}` et `frontend/src/config/employeeFilterSources.ts`.
Modifiés : `frontend/src/config/employeeFilters.ts`, `frontend/src/api/employees.ts`, `frontend/src/pages/EmployeeListPage.tsx`, son CSS et ses tests ; STATUS, MATRIX, DECISIONS et ARCHITECTURE.
Supprimé : `frontend/src/pages/EmployeeFilters.tsx`, ancien panneau remplacé par le moteur commun. COMMANDES inchangé : scripts et lancement identiques au lot R1.

### Checklist de référence pour la validation manuelle

Liste Employee et sélection au clic/clavier ; lien de nom indépendant ; galerie (aspect, catégories, recherche, focus et fermeture) ; ajout Activité puis choix de valeur dans la barre ; doublon interdit, suppression/reset ; Supérieur (recherche, sélection clavier, nom restauré après refresh) ; URL et back/forward, filtres compacts, laptop/petit écran et console. Validation fonctionnelle confirmée par le retour utilisateur ; ne pas commencer R2 sans demande explicite.

### Vérifications automatisées R1.1 — VM

- Frontend avec Node 24.11.1 déjà installé : `npm test` **8 fichiers / 57 tests réussis** (dont moteur commun, intégration Supérieur et non-régression R1/AUTH1), `npm run lint`, `npm run typecheck` et `npm run build` réussis ; Vite 7.2.6, 1945 modules. Aucun ajout de dépendance ni audit fix.
- Backend inchangé : `python3 manage.py test labsmanager.tests.test_api_v1 labsmanager.tests.test_api_v1_employees --verbosity 1` **48 tests réussis en 73.200 s**, base de test créée/détruite, accès PostgreSQL déjà autorisé ; `python3 manage.py check` sans anomalie.
- Les tests ont détecté puis vérifié la correction d'une course de focus entre fermeture de galerie et montage du contrôle après navigation URL. Les recherches distantes couvrent annulation/réponse tardive, erreur/réessai, absence de résultat et résolution d'ID ; les tests d'intégration vérifient les véritables chemins v1 et l'absence de filtres de table dans les suggestions.
- Aucun test CSS ni validation visuelle revendiquée. Les commandes et les ports de lancement restent ceux de COMMANDES ; **R1.1 est désormais validé fonctionnellement par retour utilisateur**. Ce retour ne constitue pas une validation visuelle ou exhaustive de chaque point de la checklist.

## UX2 — Design System et Employee List pilote

Implémenté, **validation visuelle utilisateur en attente**. shadcn/ui Base UI/base-nova est la référence React ; Lucide, Tailwind v4 et tokens sémantiques Teal Light/Dark. Primitives : Button, Input, NativeSelect, Badge, Popover, DropdownMenu, Combobox (InputGroup/Textarea nécessaires à cette dernière). Wrappers UX1 conservés comme délégation, anciens CSS Button/StatusBadge remplacés.

Employee List : recherche et filtres légers, galerie en lignes sans cards, tableau compact avec cellule `⋯` réservée, visible au hover/focus/sélection (visible sur écran tactile). Le menu sélectionne la ligne en un clic, propose uniquement les deux actions existantes ; désélection rend le focus à la ligne, Échap au déclencheur. Thème accessible depuis la topbar, choix local mémorisé, aucune refonte des préférences Django. Catalogue, sources, URL et contrats API R1/R1.1 conservés. Aucun backend, port ou autre migration métier modifié par UX2.

À contrôler dans le navigateur : densité/lisibilité, teal light/dark, galerie et filtres actifs, recherche Supérieur, hover/sélection/menu, clavier, pagination, shell et responsive. Ne pas démarrer R2 avant cette validation.

Validation technique UX2 : **58 tests frontend passent**, ESLint et `tsc -b` passent, build Vite réussi. Suite finale exécutée seule avec `npm test -- --maxWorkers=1 --testTimeout=15000` pour éviter les délais dépassés observés sous charge concurrente. Tests adaptés aux primitives asynchrones, test ajouté pour sélection/ouverture du menu en un clic et au clavier ; retour du focus vérifié. Aucun test backend relancé, configuration Django non concernée. Rendu visuel à valider manuellement.
