# Architecture de migration React

## Organisation du dépôt

Le dépôt de distribution se trouve à la racine. `backend/` est le sous-module Django canonique ; `frontend/` et `docs/react-migration/` sont versionnés dans le dépôt racine. La distribution copie `backend/` vers le chemin interne historique `${LAB_HOME}/labsmanager`, ce qui préserve Gunicorn, Django-Q, collectstatic et les tâches Invoke.

Django reste le backend, porte la logique métier et les permissions, utilise PostgreSQL et conserve l'interface historique pendant la migration. La SPA React 19/TypeScript est montée sous `/app/`. Les contrats stables ajoutés pour React sont publiés sous `/api/v1/`; les routes historiques `/api/` restent compatibles.

## Session, transport et shell React

React utilise la session Django et le cookie CSRF. Le client appelle des URL relatives, envoie les cookies, copie `csrftoken` dans `X-CSRFToken` pour les méthodes non sûres et centralise uniquement les `401` comme expiration de session. Un `403` reste une interdiction locale.

`GET /api/v1/me/` amorce la session, expose les capacités de navigation et une référence Employee nullable pour l'identité utilisateur. Ces capacités adaptent le shell ; elles ne remplacent jamais les contrôles backend. La connexion et la déconnexion React réutilisent django-allauth via les endpoints v1 dédiés.

React Router utilise `/app` comme basename. En développement, Vite proxifie `/api` vers Django ; `VITE_DJANGO_PUBLIC_URL` fournit l'origine des liens HTML vers les parcours Django non migrés. Le build React n'est pas encore intégré à Nginx/Docker.

Les workflows d'invitation, de réinitialisation/changement de mot de passe et de gestion des emails restent servis par django-allauth dans l'interface Django. LabsManager n'expose aucun mode métier anonyme : la réponse anonyme de `/me/` sert uniquement à orienter vers l'authentification.

## Runtime et distribution

Le développement bare-metal lance Django depuis `backend/` et Vite depuis `frontend/`; Django-Q reste un processus séparé. La configuration Django vient des variables d'environnement puis de `backend/config.yaml`. Les fichiers de configuration sensibles restent ignorés par Git.

La distribution actuelle utilise Python 3.11, PostgreSQL 13, Gunicorn, un worker Django-Q et Nginx. `requirements.in` décrit les dépendances Python sources et `requirements.txt` leur verrou installé par Docker ; les dépendances npm sont verrouillées dans `frontend/package-lock.json`. Nginx sert les statiques Django et proxifie l'application, sans servir encore le build Vite.

Les capacités `/me/` couvrent actuellement la navigation vers Employees, Teams, Contracts, Projects, Organizations, Calendar, Dashboard, Fund finder et Import. Elles sont calculées depuis les permissions Django existantes et ne constituent jamais une permission d'accès à un objet.

## Design System frontend

Le frontend utilise shadcn/ui avec Base UI/base-nova, Tailwind v4, Lucide et des tokens sémantiques Light/Dark. Les primitives partagées résident dans `frontend/src/components/ui/`; les layouts métier restent en CSS Modules. L'i18n React suit la langue du navigateur avec les catalogues `fr` et `en`, indépendamment de la langue métier des rapports.

Le moteur commun de filtres réside dans `frontend/src/filters/`. Il reçoit un catalogue déclaratif et des sources séparées, conserve l'état dans l'URL et ne déduit aucune permission. Employee utilise actuellement un choix statique Activité et une recherche distante Supérieur.

`FilterBar` coordonne la galerie et les contrôles actifs. Les définitions de filtres ne contiennent pas de callbacks métier ; elles référencent des sources qui chargent une petite nomenclature ou recherchent/résolvent une entité. Les relations sont sérialisées par identifiant stable. Un filtre ajouté sans valeur reste présent dans l'URL mais n'est pas envoyé à l'API. Les extensions date, texte, nombre, plage, choix dynamique et multi-valeur restent typées mais ne sont branchées qu'après validation du contrat backend correspondant.

## Autorisation et visibilité relationnelle

Les collections et détails Employee v1 commencent par borner l'Employee avec `Employee.get_instances_for_user("view", user, queryset)`. Les recherches, filtres et chargements de sous-ressources interviennent ensuite. Un objet absent et un objet hors périmètre produisent le même `404`.

Une sous-ressource Employee peut exposer l'identité minimale d'une ressource liée pour expliquer la relation. Cette visibilité contextuelle ne confère aucun droit autonome sur la ressource liée. Les endpoints liés conservent leur propre périmètre objet. Le frontend ne rend un lien que si le contrat fournit le droit indépendant nécessaire et si une destination réelle existe.

Ce principe s'applique notamment à la hiérarchie Employee, aux collaborateurs de jalons et aux Project associés aux jalons, participations et segments de charge.

## Contrats Employee v1 actuels

| Endpoint | Rôle |
|---|---|
| `GET /api/v1/employees/` | Liste paginée, recherche, filtres et tri |
| `GET /api/v1/employees/<id>/` | Noyau du détail, données générales et indicateurs Django-side |
| `GET/POST /api/v1/employees/<id>/generic-info/` | Collection enveloppée, capacités contextuelles et création |
| `PATCH/DELETE /api/v1/employees/<id>/generic-info/<info_id>/` | Valeur modifiable, suppression définitive |
| `GET /api/v1/generic-info-types/` | Catalogue global authentifié, lecture seule |
| `GET /api/v1/employees/<id>/statuses/` | Statuts courants et historiques |
| `GET /api/v1/employees/<id>/hierarchy/` | Supérieurs et subordonnés directs, courants et historiques |
| `GET /api/v1/employees/<id>/milestones/` | Jalons et tâches contextualisés |
| `GET /api/v1/employees/<id>/project-participations/` | Relations `Participant` de l'Employee |
| `GET /api/v1/employees/<id>/project-workload/` | Profil temporel agrégé de charge projet |
| `GET /api/v1/employees/<id>/contracts/` | Synthèse des Contracts visibles, classés temporellement |
| `GET /api/v1/employees/<id>/contracts/<contract_id>/` | Détail Contract et dépenses chargés à la demande |
| `GET /api/v1/employees/<id>/contributions/` | Contributions contextuelles classées temporellement |
| `GET /api/v1/employees/<id>/contribution-workload/` | Profil temporel agrégé des quotités de Contribution |
| `GET /api/v1/employees/<id>/budgets/` | Budget items explicitement affectés et valeurs financières interprétées |
| `GET /api/v1/employees/<id>/leaves/` | Congés contextuels, filtrables par intersection de période et type |
| `GET /api/v1/employees/<id>/leaves/capabilities/` | Capacités Leave calculées par `change_employee` |
| `POST /api/v1/employees/<id>/leaves/`, `PATCH/DELETE /api/v1/employees/<id>/leaves/<leave_id>/` | Mutations Leave bornées à l'Employee de l'URL |
| `GET /api/v1/leave-types/` | Catalogue MPTT hiérarchique, tous les niveaux sélectionnables |
| `GET /api/v1/employees/<id>/calendar/` | Événements Calendar normalisés et bornés : Leave du cœur puis plugins actifs |
| `GET /api/v1/employees/<id>/calendar/filters/` | Filtres déclarés par les plugins actifs pour le contexte Calendar Employee |

Le détail utilise un sérialiseur dédié pour ne pas alourdir la liste. Il ajoute `birth_date`, `email`, `contract_quotity`, `project_quotity`, `contribution_quotity` et `active_milestones_count`. Les quatre indicateurs réutilisent les méthodes métier du modèle Employee. `generic-info` transporte un identifiant d’icône texte, résolu par un registre Lucide statique, jamais injecté comme HTML.

Les historiques de statut et de hiérarchie sont des sous-ressources distinctes. Leur chargement, leur erreur et leur réessai restent locaux dans la Vue d'ensemble. `CopyableValue` sépare la valeur copiée du rendu affiché et utilise la Clipboard API avec un fallback compatible avec le développement HTTP.

## Layout Employee et sous-routes

`EmployeeDetailPage` est le layout partagé de la fiche. Il charge l'Employee, affiche le retour liste, le header commun et `EmployeeResourceNav`, puis rend le panneau actif avec `Outlet`.

Les routes imbriquées sont :

- `/app/employees/:id` → `EmployeeOverview` ;
- `/app/employees/:id/projects` → `EmployeeProjects` ;
- `/app/employees/:id/contracts` ;
- `/app/employees/:id/funding` → `EmployeeFunding` ;
- `/app/employees/:id/leaves` ;
- `/app/employees/:id/notes`.

La navigation ressemble à des onglets mais reste une navigation par liens et routes. L'URL porte le panneau actif, permet refresh et back/forward, et évite de charger les données des panneaux non affichés. Contracts rend `EmployeeContracts`, Financement rend `EmployeeFunding`, Congés rend `EmployeeLeaves` et Notes reste un placeholder.

`EmployeeOverview` charge les statuts et relations hiérarchiques et délègue les `GenericInfo` au bloc métier `EmployeeGenericInfo`. Il commence directement par **Informations générales** : aucun titre « Vue d'ensemble » redondant et aucun collapse, car ce panneau ne contient qu'une grande section.

`EmployeeProjects` charge les jalons et participations uniquement lorsque sa route est active. Il contient deux `PersistentCollapsibleSection`, **Jalons et tâches** et **Participations projets**. La seconde contient la timeline de charge puis le tableau des participations.

## Sections persistantes

`PersistentCollapsibleSection` est le composant transversal des grandes sections internes dont le repli a une utilité fonctionnelle. Toute la ligne de titre est un bouton accessible portant `aria-expanded` et `aria-controls`. L'état est mémorisé dans `localStorage` avec une clé stable par type de section, jamais par Employee, et la première ouverture est dépliée.

Les sous-routes et les collapsibles ont des rôles complémentaires : les sous-routes séparent les domaines principaux ; les collapsibles structurent plusieurs grandes sections au sein d'un même panneau. Une seule grande section ne justifie pas à elle seule un collapse.

## Jalons et tâches R2.2

`EmployeeMilestoneV1View` retourne tous les jalons affectés à l'Employee visible et annote chaque référence Project/Employee avec `can_view`, sans filtrer la collection selon ces droits indépendants.

La classification est calculée côté Django, dans cet ordre : completed, overdue, due soon, planned, in progress. Le seuil due soon utilise `NOTIFICATION_ENDPOINTS_MILESTONES_STALE` résolu par `LMUserSetting` pour l'utilisateur courant. `start_date is None` produit `work_kind="milestone"`; une date de début produit `work_kind="task"`. Le type `q` autorise l'affichage de `quotity` comme progression ; le type `o` n'a pas de progression chiffrée pertinente.

`EmployeeMilestones` regroupe les données selon les cinq états et conserve uniquement l'ouverture des groupes dans son état local. `MilestoneDetailSheet` affiche les détails dans un panneau latéral ; ni le Sheet ni les sous-groupes ne sont persistés.

## Profil temporel de charge R2.3

`EmployeeProjectWorkloadV1View` calcule la charge depuis les bornes `start_date`/`end_date` et la `quotity` des `Participant`, sans utiliser les dates Project. Il construit des intervalles inclusifs uniquement aux événements de début et de fin, additionne les quotités actives et agrège par Project les participations qui se chevauchent. Les segments consécutifs de composition identique sont fusionnés.

Une requête bornée exige `start` et `end`. `range=all` est explicite, incompatible avec ces paramètres et conserve les bornes ouvertes sous forme `null`. Les références Project incluent `can_view`, mais le graphique ne crée actuellement aucun lien Project.

`EmployeeProjectWorkload` gère les presets et le chargement local. Le preset un an couvre aujourd'hui −3 mois / +9 mois ; cinq ans couvre −1 an / +4 ans. Les boutons précédent/suivant déplacent une fenêtre bornée de six mois et Aujourd'hui remet son offset à zéro. Le mode Tout n'a pas de navigation temporelle.

`WorkloadTimeline` est le renderer neutre partagé. Son SVG dessine un profil compact en escalier, une ligne de seuil à 100 % et une échelle qui peut dépasser ce seuil. Seule la partie excédentaire utilise le token destructif. `ProjectWorkloadTimeline` adapte les segments et le vocabulaire Project sans déplacer la logique métier dans le renderer.

## Limites et prochaine évolution

## Contrats Employee R2.4b

`EmployeeContractListV1View` résout d'abord l'Employee dans son scope v1, puis obtient directement ses Contracts par leur relation à cet Employee. Aucun second périmètre autonome Contract ne réduit les données contextuelles de la fiche.

La classification temporelle est calculée côté Django avec la priorité future (`start_date > today`), past (`end_date < today`), puis current. Les bornes nulles restent ouvertes. L'ordre place les contrats courants par échéance croissante, les futurs par début croissant et les passés du plus récent au plus ancien. Le booléen historique `is_active` devient `requires_follow_up` dans le contrat API.

Le sérialiseur charge `contract_type`, `fund`, `project`, `funder` et `institution` avec `select_related`. Le Fund fournit son rendu historique, sa référence et ses relations. `Fund_Institution` représente le financeur ; `project.Institution` est l'Institution gestionnaire. Son `can_view` correspond à `common.display_infos` et sa destination réelle est le parcours Django Organization. Les Project restent textuels faute de route autonome.

`EmployeeContracts` rend les groupes current/future/history et garde l'historique compact sans persistance. `ContractDetailSheet` demande le second endpoint seulement à l'ouverture. Celui-ci sélectionne les `Contract_expense` du contrat demandé, additionne directement leurs montants et n'expose jamais `Expense.status`.

## Financement Employee R2.5

`EmployeeContributionListV1View` résout l'Employee avec son scope v1 puis charge directement `Contribution.objects.filter(employee=employee)`. Les relations Fund, Project, Cost Type, Employee Type et Contract Types sont descriptives ; aucune navigation autonome n'est inventée. La temporalité current/future/past repose exclusivement sur les bornes de Contribution et `timezone.localdate()`.

`EmployeeContributionWorkloadV1View` additionne en `Decimal` les quotités des Contributions actives aux frontières de leurs propres dates. Les bornes nulles restent ouvertes, les chevauchements sont agrégés et chaque segment conserve sa composition Contribution/Fund/Project. Les dates du Fund et du Project ne participent pas au calcul.

`EmployeeBudgetListV1View` applique le même gate Employee puis charge directement `Budget.objects.filter(employee=employee)`, sans périmètre autonome Budget. Pour `Budget` et `Contribution`, `expense` est la somme algébrique réelle des écritures : une valeur positive consomme le budget et une valeur négative représente un remboursement ou une contre-écriture. `BudgetAbstract` définit donc `available=amount-expense` et `consumption_ratio=expense/amount`. `EmployeeBudgetV1Serializer` expose cette dépense nette signée sous le champ historique `consumed` et réutilise les calculs du modèle. Un ratio impossible à calculer reste `null`.

`EmployeeFunding` contient deux `PersistentCollapsibleSection`, Contributions et Budgets affectés, ouvertes par défaut et persistées par type de section. `EmployeeContributionWorkload` adapte les données au renderer neutre `WorkloadTimeline`. `EmployeeBudgets` affiche les trois montants et une barre de consommation financière ; son erreur et son état vide restent locaux sans masquer les Contributions.

## Calendar Core et absences Employee R2.6a

Le noyau non persistant `common.calendar` définit `CalendarContext`, les types de calendrier historiques, `LabsManagerCalendarEvent` et `CalendarService`. Les contrats `events` et `context` ne dépendent pas des plugins. Le service découvre uniquement les plugins actifs par `registry.with_mixin("calendarevent", active=True)`, applique leurs filtres et agrège leurs événements en journalisant chaque défaillance isolée.

```text
common.calendar
    ↓
CalendarService
    ├── producteurs core
    └── registre plugins → CalendarEventMixin
    ↓
LabsManagerCalendarEvent[]
    ↓
API / renderer
```

`CalendarEventMixin` reçoit désormais un contexte typé : `get_calendar_events(context)` retourne des événements et `filter_calendar_queryset(queryset, context)` retourne le queryset filtré. `FrenchHollidayPlugin` utilise ce contrat. `/api/plugin/calendar_plugin/` reste la façade FullCalendar des écrans historiques mais traduit d'abord la requête en contexte et délègue au service unique.

Le domaine Leave reste responsable de la conversion de ses modèles. Il conserve les marqueurs `ST`, `MI` et `EN` dans les métadonnées ; le cœur Calendar n'interprète pas ces codes. L'API Employee autorise d'abord l'Employee, puis lit directement `Leave.objects.filter(employee=employee)`. Aucun droit autonome Leave ne réduit le contexte.

`EmployeeLeaves` propose Calendrier/Tableau avec préférence persistée. Le calendrier demande toujours une fenêtre bornée et fournit Mois, Année et cinq ans avec navigation temporelle. Le tableau consomme le contrat Leave, les événements calendrier consomment le contrat Calendar ; seul un événement `kind="leave"` ouvre le Sheet Leave.

Les vues Mois et Année utilisent FullCalendar React Standard : `dayGridMonth` pour le mois et `dayGridYear` pour l'année. La vue cinq ans conserve une synthèse interne plus légère. L'adaptateur `LabsManagerCalendarEvent → EventInput` est la frontière frontend unique : il traduit `all_day` en `allDay`, conserve `description`, `source`, `kind` et `metadata` dans `extendedProps`, et transmet `display="background"` au moteur sans reconstruire des chips par jour. Les plugins `daygrid`, `interaction` et le thème classic viennent des sous-chemins de `@fullcalendar/react`; aucune dépendance Scheduler/Premium ni clé de licence n'est utilisée.

R2.6a.2 ajoute `LabsManagerCalendarFilter`, contrat neutre contenant `id`, `title`, `type`, `source`, `choices` et `default`. `CalendarEventMixin.get_calendar_filters(context)` résout les définitions statiques ou dynamiques, puis `CalendarService.get_filters(context)` agrège les filtres des plugins actifs avec la même isolation que les événements. La façade Django historique adapte ce contrat ; elle ne maintient pas un second moteur de résolution.

React charge les filtres applicables depuis l'endpoint Employee et rend génériquement `select`, `checkbox`, `radio`, `input-text` et `input-color`. Leurs identifiants restent opaques au frontend. Les valeurs survivent à la navigation temporelle locale et sont transmises aux requêtes bornées `/calendar/`. FrenchHolliday fournit ainsi son choix dynamique de zone sans branche spécifique dans React.

Sur écran étroit, la vue annuelle `dayGridYear` conserve la grille FullCalendar ; sa lisibilité reste améliorable. La synthèse cinq ans omet volontairement les événements `display="background"`, affiche les dates des événements restants et réutilise le même Sheet Leave. La présentation textuelle des demi-journées est centralisée : Matin, Après-midi, À partir de midi, Jusqu'à midi ou Midi → midi selon les bornes. `eventDrop` et `eventResize` (y compris depuis le début) appellent le PATCH Leave pour les seuls événements `core/leave` modifiables, conservent ST/MI/EN et rétablissent l'événement si l'écriture échoue.

Les panneaux Employee restent en lecture seule à l’exception de GenericInfo, premier cas de mutation R2.7. Notes ne dispose encore d’aucun contrat métier React.

## Roadmap après clôture R2.6a.2

- **R2.7** établit le socle des mutations React avec `GenericInfo` comme premier objet simple : permissions, validation, erreurs, feedback et rafraîchissement. `Note` reste hors périmètre de ce lot.
- **R2.8** implémente Employee uniquement : Employee API v1 → EmployeeGanttAdapter → contrat `LabsManagerGantt` (`items`, identité, parent, nature, dates et état) → LabsManagerGantt → SvarGanttAdapter → SVAR OSS. En parallèle, CalendarService fournit `LabsManagerCalendarEvent[]` et les filtres plugins du contexte `employee-gantt`. L'endpoint Employee Calendar existant reçoit `context=employee-gantt` et ne mélange pas les Leave de l'Agenda à ce contexte. Les filtres restent limités aux événements Calendar. Les événements temporels ordinaires sont des lignes ; `display="background"` reste omis car l'API OSS publique ne permet pas de placer une plage colorée de fond proprement. Les bornes ouvertes sont projetées jusqu'au bord de la fenêtre affichée, sans changer les valeurs métier. Une tâche utilise sa période, un jalon sa date de fin. Le Gantt est strictement en lecture seule.
- La future fiche Project créera ses propres endpoints et `ProjectGanttAdapter` vers le même contrat ; la future vue globale créera l'agrégation adaptée et `GlobalGanttAdapter`. Leurs contextes Calendar et la volumétrie globale seront décidés dans leurs lots.
- **R2.9** introduit `MilestoneDependency` entre deux instances du modèle commun Task/Milestone, avec unicité SQL, auto-dépendance interdite et cycles vérifiés côté backend. Le Sheet Employee utilise une API métier : recherche Project puis planning item, tous deux bornés par `Project.get_instances_for_user("change")` pour les mutations. L'incohérence temporelle est calculée côté backend et n'empêche aucune écriture. Le contrat LabsManagerGantt ajoute les dépendances par identités métier ; SvarGanttAdapter ne rend que les liens dont les deux extrémités figurent déjà dans le scope Employee, en lecture seule. Aucun scheduling, type FS/SS/FF/SF, lag ou calendrier ouvré n'est ajouté.
- **R2.10** ajoute POST/PATCH/DELETE Leave sous l'Employee de l'URL, avec capacités `change_employee` publiées séparément pour les deux vues et catalogue MPTT de Leave_Type. La validation métier compare des intervalles de demi-journées et est réévaluée lors de l'écriture. `EmployeeLeaves` partage un Sheet view/create/edit entre Tableau et Calendrier ; CalendarService reste le seul agrégateur des événements. FullCalendar Mois/Année fournit une sélection à fin exclusive convertie en dates Leave inclusives dans l'UI ; la synthèse cinq ans n'offre pas de sélection. Le workflow demande/approbation reste ultérieur.


## R2.11a — liste Project

`/api/v1/projects/` sert une liste paginée et filtrée sous la visibilité canonique de
`Project.get_instances_for_user("view", user, ...)`. Les relations Institutions,
Participants et Funds sont préchargées et sérialisées en éléments compacts ; Funds est
également borné par sa propre visibilité. Les capacités d'écriture viennent du backend :
`change` objet Project, `add_project` et `delete_project` globaux. Les mêmes contrôles
protègent POST/PATCH/DELETE. Le Sheet d'écriture porte seulement les champs racine Project.

Le catalogue commun de filtres React définit type, options et valeur initiale. Son
marqueur d'initialisation dans l'URL permet d'appliquer Active=true au premier accès sur
Project et Employee sans le réintroduire après suppression volontaire. Les définitions
restent propres à chaque domaine ; `FilterBar` rend les filtres texte, date et choix
dynamiques ajoutés pour Project. Les listes partagent localement badge de statut,
comportement de ligne et en-tête triable ; aucun moteur DataTable distinct n'est introduit.
`/app/projects/:id` est une route React transitoire minimale pour la navigation et la
création ; la fiche métier n'est pas encore migrée.

## R2.7 — mutations GenericInfo

La collection retourne `{capabilities: {can_add, can_change, can_delete}, items}` même
lorsqu’elle est vide. Les capacités restent contextuelles à l’Employee, pas dans `/me/`.
Le catalogue global des types retourne un tableau `{id, name, icon}`, trié par nom puis
identifiant, sans pagination ni mutation. Tous ces endpoints exigent une session authentifiée.

Le gate Employee existant est appliqué avant toute opération. PATCH/DELETE recherchent
ensuite le GenericInfo exclusivement parmi les enfants de cet Employee (404 si absent ou
étranger). Le payload ne peut jamais fixer l’Employee. POST accepte `type_id` et `value` ;
PATCH accepte uniquement `value`. Les champs interdits, dont le type en PATCH, produisent
un 400 explicite. La valeur autorise omission à la création, null et chaîne vide ; sa limite
est 150 caractères. Les doublons de type sont autorisés. POST retourne 201 et l’objet
sérialisé, PATCH 200 et l’objet, DELETE 204. PUT n’est pas exposé.

`staff.rules.can_change_employee` combine les permissions globales et objet existantes,
sans modifier `staff.change_employee` ni `is_user_employee`. `is_linked_employee` exprime
seulement le lien User/Employee. La rule `staff.change_partial_employee` combine full change
et ce lien ; elle est enregistrée par `rules`, sans permission modèle attribuable supplémentaire.
`staff.permissions_v1.generic_info_capabilities` fournit le calcul partagé par GET et les
contrôles d’écriture : partial pour create, full pour update/delete. `common.self_edit`
conserve donc le plein droit de mutation sur sa propre fiche via la règle historique.
Les écritures ordinaires de modèle conservent les signaux et le middleware auditlog.

React réutilise `apiRequest`, la session et CSRF. `useMutation` gère pending, erreur et
verrou immédiat contre une seconde soumission. Une réponse tardive après démontage du
formulaire ne déclenche pas de rafraîchissement de son ancien contexte. `normalizeMutationError` conserve les
messages DRF par champ, `non_field_errors` et `detail`, distingue validation/403/404/401,
serveur et réseau. Les 401 restent aussi traités centralement. Les erreurs n’effacent
pas les valeurs et ne ferment pas le formulaire.

`EmployeeGenericInfo` reste un composant métier. `GenericInfoFormSheet` utilise le Sheet
existant ; le type est sélectionnable seulement en création. `ConfirmDialog` utilise
Base UI AlertDialog et exige une confirmation avant DELETE, avec annulation et retour du
focus. Le menu de ligne est réservé aux actions autorisées ; l’ajout reste indépendant.
Aucune dépendance toast ni framework CRUD n’est introduit.

Après succès, la représentation serveur actualise immédiatement la collection locale
(ou l’item est retiré après 204), puis `useEmployeeResource.refresh()` relit la collection.
`updateData()` invalide les lectures antérieures ; `refresh()` conserve les données et
retourne un booléen. `refreshError` est distinct de l’erreur initiale. Un échec de relecture
annonce que la mutation est déjà enregistrée et ne propose que de rejouer GET. Le retry
historique des autres panneaux conserve son comportement. Les lectures sont annulées au
changement de contexte ou démontage.

`GenericInfoType.icon` est un CharField nullable/blank de 50 caractères. La migration
0014 convertit les six chaînes FA connues ; les inconnues, null et vide restent intacts.
Le registre statique React résout Badge, Contact, Search, Columns3 et Stethoscope, avec
CircleQuestionMark en fallback. Le legacy Employee conserve le texte sans rendu FAIcon ;
son admin est spécialisé. Les autres usages FAIcon, notamment Project, sont conservés.
