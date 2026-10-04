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

## Méthode permanente de réutilisation

Avant tout nouveau lot, lire la mémoire canonique : `ARCHITECTURE.md`,
`DECISIONS.md`, `STATUS.md`, `MATRIX.md`, `COMMANDES.md` et [REUSABLE.md](REUSABLE.md).
Avant toute nouvelle implémentation, consulter le registre puis rechercher dans le code
une implémentation, brique configurable, contrat, adapter, classe de base, mixin,
héritage, service, helper, mécanisme backend canonique ou pattern architectural/UX
répondant déjà au besoin. Réutiliser directement si possible ; configurer une brique
si la variation est simple ; employer adapter, contrat ou héritage/mixin lorsque
c'est la frontière naturelle. Quand plusieurs contextes partagent réellement un
comportement ou contrat, préférer une factorisation appropriée à des implémentations
parallèles. Un même pattern UX peut toutefois être appliqué sans composant commun.

Ne pas factoriser sur une simple ressemblance de fichiers, mélanger des règles métier
distinctes, accumuler des conditions de contexte dans un composant générique ou créer
une abstraction spéculative. Une duplication limitée est préférable à une mauvaise
frontière ; créer une nouvelle implémentation lorsqu'aucune réutilisation propre ne
répond au besoin. Ajouter à `REUSABLE.md` toute nouvelle brique conçue pour être
réutilisée, toute brique existante reconnue comme canonique et tout nouveau pattern
UX transversal effectivement décidé. Ce registre est une orientation initiale, pas
un inventaire exhaustif ni un substitut à l'inspection du code courant.

## Design System frontend

Le frontend utilise shadcn/ui avec Base UI/base-nova, Tailwind v4, Lucide et des
tokens sémantiques Light/Dark. Les primitives partagées résident dans
`frontend/src/components/ui/`; les layouts métier restent en CSS Modules.
L'i18n React suit la langue du navigateur avec les catalogues `fr` et `en`,
indépendamment de la langue métier des rapports. Tout texte UI statique du
frontend React, y compris les libellés accessibles (`aria-label`, annonces,
titres), passe par `useTranslation().t(...)` : aucune nouvelle chaîne UI
statique ne doit être codée en dur. Les clés et leurs interpolations doivent
être présentes en français et en anglais, et chaque lot frontend vérifie les
deux langues. Les données métier fournies par le backend (noms, valeurs
configurables, commentaires et libellés dynamiques de plugins) restent
affichées telles que stockées, sauf contrat métier explicite de traduction.
Les erreurs métier Django/DRF restent sous la responsabilité du backend.

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

La navigation ressemble à des onglets mais reste une navigation par liens et routes. L'URL porte le panneau actif, permet refresh et back/forward, et évite de charger les données des panneaux non affichés. Contracts rend `EmployeeContracts`, Financement rend `EmployeeFunding`, Congés rend `EmployeeLeaves` et Notes rend `GenericNotes` depuis R2.17.

`EmployeeOverview` charge les statuts et relations hiérarchiques et délègue les `GenericInfo` au bloc métier `EmployeeGenericInfo`. Il commence directement par **Informations générales** : aucun titre « Vue d'ensemble » redondant et aucun collapse, car ce panneau ne contient qu'une grande section.

`EmployeeProjects` charge les jalons et participations uniquement lorsque sa route est active. Il contient deux `PersistentCollapsibleSection`, **Jalons et tâches** et **Participations projets**. La seconde contient la timeline de charge puis le tableau des participations.

## Sections persistantes

`PersistentCollapsibleSection` est le composant transversal des grandes sections internes dont le repli a une utilité fonctionnelle. Toute la ligne de titre est un bouton accessible portant `aria-expanded` et `aria-controls`. L'état est mémorisé dans `localStorage` avec une clé stable par type de section, jamais par Employee, et la première ouverture est dépliée.

Les sous-routes et les collapsibles ont des rôles complémentaires : les sous-routes séparent les domaines principaux ; les collapsibles structurent plusieurs grandes sections au sein d'un même panneau. Une seule grande section ne justifie pas à elle seule un collapse.

## Jalons et tâches R2.2

`EmployeeMilestoneV1View` retourne tous les jalons affectés à l'Employee visible et annote chaque référence Project/Employee avec `can_view`, sans filtrer la collection selon ces droits indépendants.

La classification est calculée côté Django, dans cet ordre : completed, overdue, due soon, planned, in progress. Le seuil due soon utilise `NOTIFICATION_ENDPOINTS_MILESTONES_STALE` résolu par `LMUserSetting` pour l'utilisateur courant. `start_date is None` produit `work_kind="milestone"`; une date de début produit `work_kind="task"`. Le type `q` autorise l'affichage de `quotity` comme progression ; le type `o` n'a pas de progression chiffrée pertinente.

`PlanningMilestoneTable` regroupe les données selon les cinq états et conserve uniquement l'ouverture des groupes dans son état local. Ce composant et `MilestoneDetailSheet` consomment le contrat Planning commun ; ni le Sheet ni les sous-groupes ne sont persistés. Depuis R2.11-refactor-2, la liste compacte affiche aussi les Employees affectés.

Le Sheet de détail partagé présente les mêmes informations métier depuis Employee et
Project, notamment les deux directions des dépendances. Il reçoit du contexte appelant
les interactions autorisées : Employee consulte les dépendances et peut éditer uniquement
`desc`, `quotity` et `status` selon `endpoints.change_milestones`, tandis que Project
peut ajouter un prédécesseur ou un successeur selon les capacités backend et supprimer
un prédécesseur. L'API lit séparément
prédécesseurs et successeurs dans le périmètre canonique des items lisibles ; les
successeurs sont présentés sans menu de modification ou de suppression ; l'ajout d'une
relation vers un successeur réutilise le POST canonique de ce successeur. Un composant partagé
n'infère pas son contexte de la route et n'élargit pas les droits métier du backend.

## Profil temporel de charge R2.3

`EmployeeProjectWorkloadV1View` calcule la charge depuis les bornes `start_date`/`end_date` et la `quotity` des `Participant`, sans utiliser les dates Project. Il construit des intervalles inclusifs uniquement aux événements de début et de fin, additionne les quotités actives et agrège par Project les participations qui se chevauchent. Les segments consécutifs de composition identique sont fusionnés.

Une requête bornée exige `start` et `end`. `range=all` est explicite, incompatible avec ces paramètres et conserve les bornes ouvertes sous forme `null`. Les références Project incluent `can_view`, mais le graphique ne crée actuellement aucun lien Project.

`EmployeeProjectWorkload` gère les presets et le chargement local. Le preset un an couvre aujourd'hui −3 mois / +9 mois ; cinq ans couvre −1 an / +4 ans. Les boutons précédent/suivant déplacent une fenêtre bornée de six mois et Aujourd'hui remet son offset à zéro. Le mode Tout n'a pas de navigation temporelle.

`WorkloadTimeline` est le renderer neutre partagé. Son SVG dessine un profil compact en escalier, une ligne de seuil à 100 % et une échelle qui peut dépasser ce seuil. Seule la partie excédentaire utilise le token destructif. `ProjectWorkloadTimeline` adapte les segments et le vocabulaire Project sans déplacer la logique métier dans le renderer.

## Limites et prochaine évolution

## Contrats Employee R2.4b

L'API Contract résout d'abord l'Employee visible, puis obtient directement ses Contracts par leur relation à cet Employee. Le contexte Project résout le Project visible, les Funds visibles et les Participants ; aucune permission Project n'est propagée au contexte Employee.

La classification temporelle est calculée côté Django avec la priorité future (`start_date > today`), past (`end_date < today`), puis current. Les bornes nulles restent ouvertes. L'ordre place les contrats courants par échéance croissante, les futurs par début croissant et les passés du plus récent au plus ancien. Le booléen historique `is_active` devient `requires_follow_up` dans le contrat API.

Le sérialiseur charge `contract_type`, `fund`, `project`, `funder` et `institution` avec `select_related`. Le Fund fournit son rendu historique, sa référence et ses relations. `Fund_Institution` représente le financeur ; `project.Institution` est l'Institution gestionnaire. Leur `can_view` correspond à `common.display_infos` et ouvre depuis R2.24b les fiches React, sans retirer le parcours Django historique. Les liens Employee, Project et Fund exigent aussi leur visibilité indépendante et une route existante.

`ContractSection` rend la liste et la sélection sans ouvrir de Sheet. Le détail est chargé à la sélection et rendu par `ContractDetail`, partagé entre Employee et Project. `ExpenseSection` vient sous ce détail ; le Sheet ne sert qu'aux écritures Contract. Les montants Contract sont calculés par le modèle et relus après mutation Expense. `Contract.is_active` signifie seulement « Suivi RH », distinct de la classification temporelle.

## Financement Employee R2.5

`EmployeeContributionListV1View` résout l'Employee avec son scope v1 puis charge directement `Contribution.objects.filter(employee=employee)`. Les relations Fund, Project, Cost Type, Employee Type et Contract Types sont descriptives ; aucune navigation autonome n'est inventée. La temporalité current/future/past repose exclusivement sur les bornes de Contribution et `timezone.localdate()`.

`EmployeeContributionWorkloadV1View` additionne en `Decimal` les quotités des Contributions actives aux frontières de leurs propres dates. Les bornes nulles restent ouvertes, les chevauchements sont agrégés et chaque segment conserve sa composition Contribution/Fund/Project. Les dates du Fund et du Project ne participent pas au calcul.

`EmployeeBudgetListV1View` applique le même gate Employee puis charge directement `Budget.objects.filter(employee=employee)`, sans périmètre autonome Budget. Pour `Budget` et `Contribution`, `expense` est la somme algébrique réelle des écritures : une valeur positive consomme le budget et une valeur négative représente un remboursement ou une contre-écriture. `BudgetAbstract` définit donc `available=amount-expense` et `consumption_ratio=expense/amount`. `EmployeeBudgetV1Serializer` expose cette dépense nette signée sous le champ historique `consumed` et réutilise les calculs du modèle. Un ratio impossible à calculer reste `null`.

`EmployeeFunding` contient deux `PersistentCollapsibleSection`, Contributions et Budgets affectés, ouvertes par défaut et persistées par type de section. `EmployeeContributionWorkload` adapte les données au renderer neutre `WorkloadTimeline`. `EmployeeBudgets` affiche les trois montants et une barre de consommation financière ; son erreur et son état vide restent locaux sans masquer les Contributions.

### Project Funding R2.12a

`/app/projects/:id/funding` garde l'en-tête et la navigation Project. Les endpoints
`/api/v1/projects/:id/funding/` et `/funds/:fund_id/` vérifient le périmètre Project,
puis le périmètre Fund ; ils fournissent la matrice Cost_Type × Fund, les totaux
persistés, le détail Fund et les capacités des trois ressources mutables. React
formate les montants et garde la sélection du Fund ; il ne calcule pas les agrégats.
Le catalogue Cost_Type et les deux catalogues d'institutions restent des données
métier, sans traduction React de leurs noms. Les dates d'un nouveau Fund proviennent
du Project mais ne sont pas liées ensuite ; l'option explicite de report de la date
de fin appelle aussi le contrôle `change_project` côté serveur.

`Fund`/`Fund_Item`/`Expense_point` utilisent la dépense agrégée négative : disponible
= montant + dépense. `Expense` individuel reste positif pour une dépense ordinaire.
`BudgetAbstract` et ses descendants Budget/Contribution utilisent au contraire leur
dépense nette signée propre, disponible = montant − dépense. Cette différence
historique est assumée ici ; aucune conversion de données ou harmonisation n'est
effectuée. Les écritures v1 passent par `save()`/`delete()` et les signaux existants.
La suppression d'un `Expense_point` appelle explicitement `Fund.calculate(force=True)`
car aucun signal `post_delete` historique ne déclenche ce recalcul. Le mode
`EXPENSE_CALCULATION` reste évalué par le backend : `s` manuel indépendant, `e`
dérivé des Expense et non modifiable directement, `h` mixte. Les Expense détaillées
restent hors contrat R2.12a. Lors de la suppression d'un Fund, les Expense liées
puis les Expense_point sont supprimées avant le Fund : sinon le signal de suppression
des Fund_Item peut recréer une ligne à partir d'un Expense_point encore présent.
Pour la même raison, la suppression isolée d'un Fund_Item est refusée tant qu'un
Expense_point du même Fund et Cost_Type existe ; elle ne retourne pas un faux succès.
Dette historique hors R2.12a : lorsque le dernier Expense_point disparaît,
`Fund.calculate()` remet `expense` à zéro mais ne remet pas `expense_f` à zéro.
R2.12a n'expose pas `expense_f` et ne modifie pas le modèle ou les données ; ce
cache Focus devra être vérifié dans un lot financier ultérieur.

### Expense individuelle R2.12b

L'API Expense est centrée sur le Fund (`/api/v1/funds/:id/expenses/`) ; le contexte
Contract utilise une collection séparée bornée par l'Employee et le Contract visibles.
Les deux collections fournissent pagination, filtres serveur et capacités, et alimentent
le même `ExpenseSection` React dans Funding et sous le Contract sélectionné. Les écritures restent
contrôlées par les rules Expense/Contract côté backend. La rule `expense.change_expense`
lit `expense.fund_item.project` (le FK `fund_item` pointe directement vers Fund).

`Contract_expense` est un enfant multi-table de `Expense`. L'affectation d'une Expense
existante crée seulement l'enfant sur la même clé parent ; la désaffectation emploie
`delete(keep_parents=True)`. Le parent, son identifiant et son unique contribution à
`Fund.calculate_expense()` restent stables. Une Expense liée à Contract exige un
Cost_Type RH selon la hiérarchie historique ; Contract et Budget sont deux liens
indépendants, chacun limité au Fund de l'Expense. Une dépense individuelle conserve
son signe saisi ; les `Expense_point` reçoivent l'opposé des sommes individuelles.
Les statuts Engaged/Realised/Projected sont tous agrégés de la même manière.

Le mode `s` garde Expense_point comme source des montants Fund et autorise seulement
les Expense individuelles spécifiques à Contract ou Budget. Les modes `e` et `h`
autorisent le CRUD général ; `e` garde les points en lecture seule, `h` conserve leur
édition manuelle. La synchronisation v1 est `POST /api/v1/funds/:id/expenses/sync/` :
elle exige `fund.change_fund` objet et `e`/`h`, appelle
`fund.calculate_expense(force=True)` puis remet à jour les totaux en cache. React
confirme l'écrasement possible des ajustements manuels et rafraîchit collection,
détail Fund et matrice Project.

### Project Budgets & Contributions R2.14

`Budget` et `Contribution` conservent leur héritage `BudgetAbstract`. Les collections et détails v1 sont bornés par `Project.get_instances_for_user("view", …)` puis les Funds visibles ; les capacités et les contrôles POST/PATCH/DELETE partagent `project.change_project` objet. Le sérialiseur commun valide les champs du socle par `full_clean()`, avec dates seulement pour Contribution et identité Fund/Cost_Type verrouillée après création comme dans le formulaire historique. Les mutations appellent `save()`/`delete()`.

La route React Project `/budgets` rend deux sections et Sheets distincts via un composant commun correspondant au socle du modèle. Seul Budget possède une sous-collection Expense : elle réutilise l’API et `ExpenseSection` existants, filtre sur `Expense.budget_item`, impose le Fund du Budget et garde son identifiant fixe à l’écriture. Après mutation, l’API recalcule via les signaux et `Budget.calculate_expense()` historiques ; React relit Expense puis Budget. Le modèle fournit `available = amount - expense` et `consumption_ratio = expense / amount`, sans calcul React ni agrégation entre Budgets. Contribution n’expose aucune sous-collection Expense.

### Contracts Project et Employee R2.15

Les endpoints Contract partagent la sérialisation et l'écriture, mais résolvent séparément le contexte Project ou Employee. Project limite la liste au Fund du Project visible et aux Employees participants ; `project.change_project` global ou objet donne les trois mutations dans ce seul contexte. Employee conserve ses permissions Contract historiques, sans hériter des droits Project. Un calcul contextuel unique fournit les capacités et contrôle POST/PATCH/DELETE. La création vérifie côté serveur le Fund et la participation ; les relations Employee/Fund sont fixes après création, comme dans le formulaire historique. `full_clean()` puis `save()`/`delete()` conservent les hooks du modèle.

La sous-collection Expense Project/Contract réutilise l'API Expense et impose le Contract et son Fund. `ContractSection` partage la liste sélectionnable, le menu, le formulaire et la confirmation entre les deux fiches ; `ContractDetail` partage l'encart informatif, et `ExpenseSection` reste la seule interface Expense. Le Sheet Contract est réservé à la création et à l'édition.

### Présentation Project Funding R2.12c

Le détail visuel du Fund sélectionné conserve une seule synthèse financière par
Cost_Type, suivie des Expense individuelles. Le bloc « Détail : Fund » redondant,
les trois tableaux séparés et la matrice Project repliable ne sont plus affichés.
La synthèse joint pour l'affichage les Fund_Item et Expense_point existants,
ainsi que les lignes de synthèse exposées par l'API, sans créer d'objet absent.
Pour chaque côté, date et montant `—` signifient absence d'objet ; `0,00 €`
représente toujours une valeur réelle. Disponible et totaux viennent du backend,
avec le montant signé de l'Expense_point en repli pour une ligne sans Fund_Item
ni synthèse. Le menu global de création et les deux menus Edit/Delete par objet
consomment les capacités backend ; Sheets, confirmations et règles `s`/`e`/`h`
restent inchangés. Aucun changement de contrat API ou de calcul métier.

## Exports Project/Employee R2.13a

Les headers Project et Employee injectent leurs actions autorisées dans le
`EntityActionMenu` commun. Project réutilise son `ProjectSheet` pour Modifier ;
Employee n'expose pas Modifier tant qu'un lot dédié n'a pas créé son contrat
d'écriture. Ce choix ne restreint pas le composant de menu. Les capabilities
`can_export_word` et `can_export_pdf` sont calculées séparément côté Django
depuis les permissions historiques de chaque modèle de rapport.

React configure le template et, pour Employee seulement, une période facultative
dans un `ReportExportDialog` commun. `GET` puis `POST`
`/api/v1/reports/<entity>/<id>/<format>/` exposent les templates du type et
retournent directement le fichier. Le backend vérifie visibilité canonique de
l'entité et permission de rapport sur les deux méthodes, valide la période et
appelle `render()` du modèle historique correspondant. React ne génère pas de
rapport et ne traduit pas les noms de templates. Les quatre anciennes URL de
rendu direct réutilisent le même contrôle de visibilité et de permission ; elles
valident aussi la période Employee avant d'appeler le renderer historique.

## Settings Project R2.13b et persistance métier

Le core Settings Django reste la source des clés, noms, descriptions, types,
valeurs par défaut, choix et validations. L'API Project Settings dérive ses
métadonnées des helpers `LMProjectSetting` et lit les valeurs effectives sans créer
de ligne. Le PATCH valide la valeur puis appelle `save()` sur l'instance, qui
exécute les validations et hooks existants. La capacité `can_change_settings`
combine permission globale `settings.change_lmprojectsetting` et droit canonique
de modification du Project, sous réserve de sa visibilité. React reçoit les
métadonnées et rend les contrôles par type dans un `SettingsSheet` réutilisable ;
il ne duplique ni définitions ni validations métier. Le changement du mode de
calcul ne convertit aucune donnée. À la fermeture, Project et le panneau actif
sont relus.

Règle transversale de persistance : toute mutation d'un modèle métier passe par
les méthodes d'instance `save()` ou `delete()` pour conserver validations, hooks
et signaux. `QuerySet.update()` et les opérations bulk sont exclues de ces
mutations sauf preuve explicite que leur contournement est sans effet métier.

## Planning Employee R2.13c — édition partielle

Chaque item de la liste Employee expose `can_change`, calculé avec
`request.user.has_perm("endpoints.change_milestones", item)`. Le prédicat historique
combine l'affectation soumise à `EMPLOYEE_EDIT_MILESTONE` et le droit de modifier
le Project. React ne lit jamais le Setting ni ne recalcule cette règle. Un lecteur
sans profil Employee lié obtient `false` sans erreur.

`PATCH /api/v1/employees/:employee_id/milestones/:item_id/` résout d'abord
l'Employee visible et l'item affecté à cet Employee, revérifie la rule, puis
n'accepte que `desc`, `quotity` et `status`. L'instance est validée et sauvegardée
par `save()` ; la cohérence completion/status est la même que dans l'API Project.
La création, la suppression et les dépendances n'ont pas de mutation dans ce
scope. Le `MilestoneDetailSheet` commun conserve son détail ; seul Employee lui
injecte le formulaire partiel explicite. La liste et le Gantt consomment la même
ressource rafraîchie ; le Gantt ne propose aucune édition directe. Le CRUD Project
et son formulaire complet restent inchangés.

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

`EmployeeLeaves` propose Calendrier/Tableau avec préférence persistée. Le calendrier demande toujours une fenêtre bornée et fournit les quatre scopes communs 15 jours, Mois, 2 mois et Année avec navigation temporelle. Le tableau consomme le contrat Leave, les événements calendrier consomment le contrat Calendar ; seul un événement `kind="leave"` ouvre le Sheet Leave.

R2.28 ajoute les contextes globaux existants `CalendarType.MAIN` et `CalendarType.PROJECT_ALL` aux APIs React en lecture seule. Le premier borne le producteur Leave aux Employees visibles puis applique les filtres Employee canoniques et les filtres plugins. Le second agrège les Projects visibles et leurs éléments Planning dans la fenêtre demandée, avec les filtres Project canoniques et les événements plugins du contexte Project global. Les filtres métier sont évalués par le backend ; l'URL React conserve les filtres séparément par onglet. La page `/app/calendars` présente ainsi le calendrier général des absences et le Planning/Gantt global, sans nouveau moteur ni édition globale.

Employee, Project, Team et Global utilisent `projectCalendarScopes`, `projectDayGridViews` et `projectResourceViews` comme définition unique des huit vues FullCalendar, des bornes API et de la navigation. `SharedCalendar` rend les vues ordinaires et Resources ; `EmployeeCalendar` reste un adaptateur mince pour le workflow Employee. L'ancien renderer React cinq ans a été supprimé en R2.16c. L'adaptateur `LabsManagerCalendarEvent → EventInput` traduit `all_day` en `allDay`, conserve `description`, `source`, `kind` et `metadata` dans `extendedProps`, et transmet `display="background"` au moteur. Les plugins `daygrid`, `timeline`, `resourceTimeline`, `interaction` et le thème classic sont enregistrés par ce composant avec la clé AGPL existante.

R2.16 extrait dans le domaine Leave un producteur commun de `LabsManagerCalendarEvent`, paramétré par `CalendarContext(EMPLOYEE|PROJECT)`. Le producteur borne les Leave à l'Employee ou aux Participants du Project, préserve les métadonnées de demi-journée et ajoute `employee_id` pour la resource FullCalendar. Les APIs autorisent d'abord leur objet racine, puis passent ces `core_events` à `CalendarService`, qui applique les filtres plugins et ajoute leurs événements. Les plugins ne produisent pas de Leave. Project expose une seule collection Calendar bornée pour les trois vues, plus les filtres et Participants/capacités. Ses mutations Leave contextuelles réutilisent les sérialiseurs Employee et contrôlent Participant + `staff.change_employee` ; elles évitent d'exiger l'accès indépendant à la fiche Employee. Les vues Resources utilisent `schedulerLicenseKey='AGPL-My-Frontend-And-Backend-Are-Open-Source'`, conformément à l'AGPLv3 du dépôt. R2.16a partage la définition des périodes 15 jours, Mois, 2 mois et Année entre DayGrid et Resource Timeline ; cette définition fixe aussi les bornes API et la navigation, sans autre pipeline d'événements.

R2.6a.2 ajoute `LabsManagerCalendarFilter`, contrat neutre contenant `id`, `title`, `type`, `source`, `choices` et `default`. `CalendarEventMixin.get_calendar_filters(context)` résout les définitions statiques ou dynamiques, puis `CalendarService.get_filters(context)` agrège les filtres des plugins actifs avec la même isolation que les événements. La façade Django historique adapte ce contrat ; elle ne maintient pas un second moteur de résolution.

React charge les filtres applicables depuis l'endpoint Employee et rend génériquement `select`, `checkbox`, `radio`, `input-text` et `input-color`. Leurs identifiants restent opaques au frontend. Les valeurs survivent à la navigation temporelle locale et sont transmises aux requêtes bornées `/calendar/`. FrenchHolliday fournit ainsi son choix dynamique de zone sans branche spécifique dans React.

La présentation textuelle des demi-journées est centralisée : Matin, Après-midi, À partir de midi, Jusqu'à midi ou Midi → midi selon les bornes. `eventDrop` et `eventResize` (y compris depuis le début) appellent le PATCH Leave pour les seuls événements `core/leave` modifiables, conservent ST/MI/EN et rétablissent l'événement si l'écriture échoue. Les vues DayGrid affichent tous les événements sans lien de débordement `+X`.

GenericInfo a inauguré les mutations Employee en R2.7 ; Leaves, Planning partiel et Contracts disposent désormais de leurs contrats de mutation propres. Notes ne dispose encore d’aucun contrat métier React.

## Roadmap après clôture R2.6a.2

- **R2.7** établit le socle des mutations React avec `GenericInfo` comme premier objet simple : permissions, validation, erreurs, feedback et rafraîchissement. `Note` reste hors périmètre de ce lot.
- **R2.8** implémente Employee uniquement : Employee API v1 → EmployeeGanttAdapter → contrat `LabsManagerGantt` (`items`, identité, parent, nature, dates et état) → LabsManagerGantt → SvarGanttAdapter → SVAR OSS. En parallèle, CalendarService fournit `LabsManagerCalendarEvent[]` et les filtres plugins du contexte `employee-gantt`. L'endpoint Employee Calendar existant reçoit `context=employee-gantt` et ne mélange pas les Leave de l'Agenda à ce contexte. Les filtres restent limités aux événements Calendar. Les événements temporels ordinaires sont des lignes ; `display="background"` reste omis car l'API OSS publique ne permet pas de placer une plage colorée de fond proprement. Les bornes ouvertes sont projetées jusqu'au bord de la fenêtre affichée, sans changer les valeurs métier. Une tâche utilise sa période, un jalon sa date de fin. Le Gantt est strictement en lecture seule.
- R2.11-refactor-2 conserve le contrat de données des Tasks/Milestones et introduit un serializer et des helpers de queryset Planning communs. R2.11c fournit au même contrat un scope Project autorisé avant filtrage et sérialisation, avec mutations contrôlées par `change_project` et affectations limitées aux Participants. `PlanningGanttAdapter` accepte les jalons de ce scope et des participations facultatives, sans adapter Project parallèle. Le domaine transforme ses données ; le contexte choisit les contributions ; le Gantt Core rend son contrat sans connaître les producteurs. R2.28 réutilise ce contrat pour agréger les Projects visibles dans une fenêtre bornée. `PlanningGanttView` partage la toolbar, la fenêtre et le renderer SVAR entre le Project et la page globale ; l'adapter accepte aussi les Projects visibles sans jalon.
- **R2.9** introduit `MilestoneDependency` entre deux instances du modèle commun Task/Milestone, avec unicité SQL, auto-dépendance interdite et cycles vérifiés côté backend. Le Sheet Employee utilise une API métier : recherche Project puis planning item, tous deux bornés par `Project.get_instances_for_user("change")` pour les mutations. L'incohérence temporelle est calculée côté backend et n'empêche aucune écriture. Le contrat LabsManagerGantt ajoute les dépendances par identités métier ; SvarGanttAdapter ne rend que les liens dont les deux extrémités figurent déjà dans le scope Employee, en lecture seule. Aucun scheduling, type FS/SS/FF/SF, lag ou calendrier ouvré n'est ajouté.
- **R2.10** ajoute POST/PATCH/DELETE Leave sous l'Employee de l'URL, avec capacités `change_employee` publiées séparément pour les deux vues et catalogue MPTT de Leave_Type. La validation métier compare des intervalles de demi-journées et est réévaluée lors de l'écriture. `EmployeeLeaves` partage un Sheet view/create/edit entre Tableau et Calendrier ; CalendarService reste le seul agrégateur des événements. Depuis R2.16c, les quatre scopes FullCalendar communs fournissent une sélection à fin exclusive convertie en dates Leave inclusives dans l'UI. Le workflow demande/approbation reste ultérieur.


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
`/app/projects/:id` a d’abord été une route transitoire pour la navigation et la création ;
R2.11b lui ajoute la fiche métier.

## R2.11b — fiche Project et vue d’ensemble

Le GET du détail Project reste soumis à `Project.get_instances_for_user("view")` et
précharge GenericInfoProject, Institution_Participant et Participant. La réponse contient
les capacités Project et celles de chaque collection ; les endpoints enfants sont
contextuels à `/api/v1/projects/<id>/` et réutilisent le même calcul de capacités pour
l’affichage et les mutations. Le catalogue de types GenericInfo et d’institutions est
fourni par `overview-options`. La création d’un Participant valide aussi la visibilité
de l’Employee sélectionné. Les données financières ne sont pas incluses.

La fiche React partage sa structure de navigation avec Employee ; seule la Vue d’ensemble
est active. Elle réutilise le Sheet Project pour les champs racine et extrait la section
GenericInfo commune aux contextes Employee et Project. Institutions et Participants ont
leurs Sheets et suppressions confirmées. Le sélecteur Employee partagé sert aux
participants ; les liens vers les fiches Employee sont affichés selon `can_view` renvoyé
par l’API.

Le correctif UX de R2.11b reprend la grille trois colonnes et les séparateurs légers
d’Employee Overview. Un hook de sélection d’élément et un menu d’actions communs servent
les listes compactes Institutions/Participants ; GenericInfo réutilise le même hook dans
son composant partagé.

## Shared Planning Core R2.11-refactor-2

`Milestones` représente les Tasks et les Milestones. L'API Employee conserve son gate
`Employee.get_instances_for_user("view")`, puis borne le queryset par affectation à
l'Employee ; les filtres facultatifs `search` et `kind` s'appliquent après ce scope.
`planning_serializer_context` calcule l'état temporel selon la préférence du lecteur,
les droits de consultation indépendants des relations et les dépendances visibles dans
le queryset filtré. `PlanningMilestoneV1Serializer` définit le même contrat de lecture
pour tout scope autorisé. Aucun nouveau droit de mutation n'est déduit de ce contrat.

Le frontend passe la même collection Planning à `PlanningMilestoneTable` et à
`PlanningGanttAdapter`/`LabsManagerGantt`. La liste groupée conserve ses cinq états et
affiche les Employees affectés ; le Gantt conserve ses identités et liens. Les lignes
de participation Employee sont un apport facultatif à l'adapter. Le panel Gantt Employee
reste responsable de son contexte Calendar, dont les filtres plugins ne filtrent que les
événements Calendar. Les paramètres Planning sont prêts côté API/client, sans contrôle
UI nouveau dans Employee ; un futur contrôle doit alimenter la requête commune utilisée
par Tableau et Gantt. R2.11c ajoute le scope et l'UI Project, avec une collection
commune filtrée par recherche, type et Employee pour Tableau et Gantt.

Le Sheet de consultation conserve les dépendances ; le Sheet de formulaire Project
porte le CRUD Task/Milestone. Le backend valide que chaque Employee affecté appartient
aux participants du Project,
indépendamment de la permission `change_project`.

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
son admin est spécialisé. Project suit à son tour cette stratégie en R2.11b avec
`project.0008`, son mapping propre et le même registre React ; les autres usages FAIcon
restent en place.

`GenericNotes` reçoit une référence d'objet parent (`scope`, ID) et ne contient aucune
règle de droit Project ou Employee. L'API Notes v1 autorise seulement les modèles
parents déclarés, borne leur visibilité puis filtre les notes `creator` avant la
sérialisation. Son calcul de capacités sert aussi aux contrôles POST/PATCH/DELETE.
`staff.changenote_employee` conserve la mutation des notes Employee pour soi-même
et la hiérarchie historique, indépendamment de `staff.change_employee`.
Le champ de contenu reste `SanitizedProseEditorField` ; l'asset WYSIWYG Django
sert l'éditeur React, tandis que le backend nettoie aussi le HTML avant lecture.
Le titre et la visibilité sont des mutations distinctes du contenu autosauvegardé.
Les anciennes routes Notes, l'admin et les exports Project/Employee filtrent aussi
les notes privées afin que la migration de l'UI n'ouvre pas un autre chemin de lecture.

Les listes Employee et Project conservent les critères, le tri et la pagination dans
les paramètres d'URL. Leur galerie de filtres déclaratifs partage `FilterBar` et
`EntitySearch` ; la recherche Project dans Employee utilise la collection Project
existante. L'API Employee filtre toujours après le périmètre visible : `status`
interroge tout l'historique `Employee_Status`, `current_status` son manager
temporel `.current`, `team` les leaders et TeamMate, et `project` les Participant.
Les choix de statut et de Team sont bornés aux Employees visibles.
Les exports des listes Employee et Project appellent `get_queryset()` puis
`filter_queryset()` des vues de liste v1 elles-mêmes : visibilité, filtres et tri
restent dans un seul pipeline. La pagination s'applique uniquement à la réponse
JSON des listes ; les exports non paginés passent respectivement par
`EmployeeResource` et `ProjectResource`, qui héritent de `labResource`.
Pour Project, le même scope `Fund.get_instances_for_user("view", …)` que la liste
alimente `ProjectResource` via `list_funds` préchargé. Le widget Fund et les six
agrégats financiers utilisent uniquement cette collection dans les exports
utilisateur. L'ancien export Project applique aussi ce scope ; le mode complet
de la Resource exige un choix explicite d'un appelant de confiance.
Depuis R2.18, Contract est un parent déclaré : sa visibilité suit les contextes
Contract existants et ses mutations Notes utilisent `expense.change_contract`.
Le compteur de notes visibles est agrégé côté backend pour la liste partagée
Project/Employee ; la ligne ouvre le même `GenericNotes` en Sheet avec sauvegarde
finale avant fermeture.

R2.20 ajoute Team comme contexte React sans nouveau moteur métier. La liste et
l'export Team appliquent le même périmètre visible, les filtres et le tri ;
`TeamResource` consomme les TeamMate préchargés. La fiche expose les capacités
issues des permissions Team historiques et sert Information, Projects pilotés
par un membre leader/co-leader, Budgets visibles en lecture seule et
`GenericNotes(scope="team")`. Le contexte `CalendarType.TEAM` résout leader et
TeamMate dans le producteur Leave commun ; `CalendarService` conserve les plugins.
Le panneau FullCalendar Project est paramétré par le contexte Team sans recopier
les vues, ressources, Sheet Leave ni interactions. Les mutations Leave gardent
`staff.change_employee` sur l'Employee concerné.

## Préférences génériques R2.21a

`common.favorite` et `common.subscription` conservent le lien générique
`user`/`content_type`/`object_id` partagé avec Django et le reporting. Le service
`common.preferences` borne les types Project, Employee, Team et les deux
Institutions, applique leur visibilité canonique, puis assure une persistance
idempotente. L'API v1 expose un état combiné sur l'objet visible et une liste
Favorites groupée et triée après filtrage ; une relation dont la visibilité est
perdue reste en base mais n'est plus publiée. Les routes HTML historiques
réutilisent le service et gardent leurs réponses. Les URLs de navigation React
ou Django sont résolues côté backend. `ObjectPreferenceActions` rend les deux
actions communes dans les entêtes Project/Employee/Team ; `FavoritesMenu` charge
la liste en une requête lorsqu'il est ouvert. Subscription reste distinct de
Favorite et les réglages détaillés ainsi que la fréquence mail restent legacy.

## Django Admin deep links R2.22

`labsmanager.admin_links_v1.get_admin_change_url(user, obj)` est l’unique producteur des liens Admin v1. Il vérifie l’identité staff et la permission `change_<model>` sur l’objet (ou le statut superuser), puis résout la route Admin ; aucune route non enregistrée n’est publiée. Les serializers et builders métier exposent `admin_url` ou `null`, sans calcul React. `AdminObjectAction` rend le lien commun dans les menus et ouvre un nouvel onglet pour préserver l’état de la SPA. Cette capacité ne modifie aucune permission métier ni le périmètre de visibilité des API.

## Contract Hub R2.23

La route `/app/tools/contracts` est un outil transversal sans création ni suppression de Contract. Liste, détail et export v1 reposent sur `Contract.get_instances_for_user("view", …)` ; `ContractHubFilter` applique les critères après cette portée. Active utilise `is_active`, Ongoing compare les deux bornes de dates à `timezone.localdate()` et Stale délègue à `Contract.staleFilter()`. Les options relationnelles proviennent des Contracts visibles et le statut des choices Django. Le même queryset filtré et ordonné alimente la pagination JSON et l'export non paginé via `ContractResource`. Une annotation de somme des `Contract_expense` alimente liste et Resource sans N+1 ; la propriété historique conserve son comportement pour les autres usages.

Le détail et le PATCH Hub réutilisent le sérialiseur et le formulaire Contract existants, mais contrôlent `expense.change_contract` dans le contexte autonome, sans reprendre les droits Project ou Employee d'un écran parent. Les routes Expense liées au Hub réutilisent `ExpenseSection` et les contrôles de mutation Expense existants après résolution du Contract visible. Le frontend réutilise le catalogue `FilterBar`, les sources Employee/Project, `ListExportDialog`, `ContractDetail`, le Sheet Contract et `ItemActionMenu` ; les query params gardent les mêmes conventions que les autres listes.

## Organisations R2.24b

Institution (`project.Institution`) et Financeur (`fund.Fund_Institution`) partagent une fiche React paramétrée par type, sans fusion de leurs modèles. Les onglets Informations, Contacts, Projets, Contrats et Notes chargent leurs sous-ressources séparément. L'API Organisation reprend `common.display_infos` pour la lecture et les permissions modèle historiques pour les mutations, avec capacités calculées côté Django. Projects, Funds et Contracts associés sont bornés par leurs périmètres visibles respectifs avant d'alimenter les listes et les résumés. Le résumé financier réutilise les champs Fund persistés et `amount + expense` pour le disponible, y compris focus. `MAP_PROVIDER` est résolu depuis `LMUserSetting` et transporté dans les options de la fiche ; React ne possède aucune seconde préférence de carte.

## Impression R2.30

L'impression utilise des renderers React dédiés, enregistrés par clé dans le registre frontend `print/`. `PrintButton` capture l'état fonctionnel et les données déjà chargées ; `PrintProvider` ouvre `PrintShell` au-dessus de la page sans démonter la vue interactive. Le shell reste indépendant des métiers, attend le signal `ready` du renderer, puis autorise `window.print()` uniquement depuis l'aperçu. Calendar instancie `SharedCalendar` en mode print ; le DOM interactif de l'écran n'est pas imprimé. Gantt et Organigramme gardent des renderers statiques indépendants de SVAR et React Flow. Calendar conserve scope, période, événements, ressources et filtres ; Gantt conserve tâches, liens, période et groupes repliés ; l'organigramme transmet le graphe déjà filtré/replié et recalcule un layout ELK statique. Le registre est un point d'extension frontend : de futurs plugins pourront enregistrer un renderer sans modifier le cœur Print. Aucun chargement de code arbitraire ni API plugin Print n'est inclus.

La sémantique des vues Calendar est centralisée : `CalendarPrintView` réutilise `SharedCalendar` en mode print, avec la même clé, la même configuration FullCalendar, les mêmes ressources et événements que l'écran. Le mode print adapte les interactions et la mise en page, sans second renderer Calendar ni liste de remplacement. La visibilité des lignes Resources est un état fonctionnel de `SharedCalendar` partagé avec Print : `period` (défaut), `all` et `today` filtrent uniquement le jeu de ressources déjà autorisé ; seuls les événements explicitement associés à une ressource comptent. Les fonds globaux ne rendent pas toutes les ressources visibles. Le mode `today` demande les événements du jour local au même endpoint Calendar et avec les mêmes filtres, car la fenêtre affichée peut être une autre année. Global obtient ses ressources du même queryset Employee visible et filtré que ses événements, y compris les Employees sans Leave dans la période. Le Gantt statique conserve son bandeau temporel et sa grille ; `ganttScales` fournit les deux niveaux d'échelle à SVAR et à l'axe statique, tandis que les couleurs des barres proviennent des mêmes styles.

## Organigramme R2.26a

La hiérarchie est exposée par `/api/v1/organization-chart/` comme deux collections plates `employees` et `relationships`. Le queryset Employee visible reste l'autorité (`get_instances_for_user("view", user)`), et seules les arêtes dont les deux extrémités sont visibles sont publiées. Le mode courant reprend les relations `Employee_Superior.current` et les Employees actifs ; le mode historique inclut les relations et Employees visibles historiques. Les racines se calculent à partir du graphe filtré, sans racine artificielle. Un cycle détecté avant publication retourne une réponse 409 contrôlée. React Flow rend le graphe, ELK calcule sa disposition ; recherche et repli opèrent sur les identifiants du graphe, sans nouvelle règle de visibilité frontend.

La préférence `LMUserSetting.SHOW_PAST_ORG` conserve sa sémantique historique inversée : `true` sélectionne « organisation actuelle uniquement ». L'API lit et met à jour cette préférence pour l'utilisateur authentifié. R2.30 réutilise le graphe normalisé et ELK dans un renderer d'impression distinct du viewport React Flow.

R2.26a-fix-1 conserve le DAG et sépare le graphe métier du sous-graphe affiché : un Employee est « isolé » uniquement s'il n'a ni parent ni enfant dans le graphe métier sélectionné, avant repli. ELK place les niveaux 0 et 1 avec compaction ; `organizationLayout` empile ensuite les niveaux plus profonds dans des colonnes déterministes ancrées sur le niveau 1, sans créer de nœud ou d'arête métier. Une grille de nœuds Employee isolés suit la hiérarchie. La recherche calcule tous les ancêtres et descendants, mais n'ouvre temporairement que les chemins nécessaires vers les résultats ; la priorité visuelle est résultat, ancêtre, descendant, normal. Les Employees inactifs gardent leurs interactions et capacités.

## Import Hub R2.27

`import.profiles.PROFILES` déclare les Resources historiques et leur permission propre. L'API v1 vérifie ce droit à chaque étape ; le frontend ne connaît que les métadonnées de profil. Les templates exportent un queryset vide par la Resource. Tablib lit CSV/TSV et les feuilles XLS/XLSX ; la feuille choisie est signée dans le token de preview. Le fichier est conservé dans un répertoire temporaire privé sous un nom UUID, limité à 10 Mio, lié à l'utilisateur et au profil par un token signé valable une heure, puis supprimé après confirmation ; les fichiers expirés sont nettoyés lors des nouveaux uploads.

Le dry-run et le commit appellent tous deux `Resource.import_data` sur le même fichier et la même feuille. Le paramètre historique `IMPORT_EXPORT_USE_TRANSACTIONS=True` encadre l'import entier ; le dry-run est annulé, les erreurs non converties annulent le commit, et `rollback_on_validation_errors=True` suit le confirm Django. `SkipErrorRessource` requalifie certaines erreurs en `skip` : l'API les expose comme erreurs de ligne mais les autres lignes peuvent être confirmées, conformément au legacy. La réponse normalise les états et lit les différences HTML comme texte avant React. Les identifiants vides des CSV/TSV sont interprétés comme les cellules vides Excel avant l'appel à la Resource ; aucune règle métier de Resource n'est recopiée. Le fichier d'erreurs conserve les colonnes originales dans leur ordre et ajoute le message et le numéro de ligne, figés dans un fichier temporaire lié au token du preview. Les entrées Admin et le signal `post_import` restent émis au commit réussi.

## Settings Hub utilisateur R2.29a

`/app/settings` est une entrée du menu utilisateur et héberge des sous-routes stables dans un shell à navigation secondaire. Les cinq panneaux de R2.29a chargent leurs données à l'ouverture ; les futurs groupes pourront ajouter des sous-routes sans changer ce shell. Aucune entrée Settings n'est ajoutée à la navigation métier. L'API `/api/v1/settings/user/` ne connaît que l'utilisateur authentifié et expose les métadonnées et valeurs typées de `LMUserSetting` ; les écritures passent par `save()` pour conserver validation et hooks. Le compte réutilise les formulaires et flows django-allauth pour le mot de passe et les e-mails, avec portée utilisateur vérifiée côté API. Favoris et abonnements gardent le service R2.21, y compris le filtrage des objets devenus invisibles. Les réglages Dashboard, Administration, Lists et Plugins restent hors de ce contrat.

## Settings Hub : Administration R2.29c

Les sous-routes `/app/settings/admin/` et tous les endpoints `/api/v1/settings/admin/` exigent `is_staff` ; le backend est l'autorité des accès. Les réglages globaux et plugin passent par `LabsManagerSetting` et `PluginSetting`, avec validation et hooks existants. Le lien User–Employee utilise la relation `Employee.user` unique dans une transaction. Les actions Notifications appellent les fonctions historiques ; la page Plugins lit le registre actif et construit le détail selon `mixin_enabled` (`settings`, `schedule`, `urls`). Le hook HTML legacy `settings_content` n'est pas introduit dans React.

## Settings Hub : listes mutables R2.29b

`/api/v1/settings/lists/` s'appuie sur une allowlist backend de neuf listes héritées des six groupes Settings actifs. Le registre possède le modèle, le ModelForm historique, les colonnes, l'ordre et les permissions globales de chaque liste ; il produit les métadonnées de champs et les capacités pour React. La même autorité contrôle POST/PATCH/DELETE. Le composant React unique ne contient aucun branchement par modèle. Les listes sont lisibles par l'utilisateur authentifié comme dans le legacy ; aucune suppression n'est activée dans les panneaux historiques actifs. Dashboard, Administration et Plugins restent hors périmètre.

## Dashboard Foundation R3.1

`dashboard.Dashboard` conserve plusieurs tableaux personnels ordonnés par utilisateur ; `WidgetInstance` conserve une clé de définition stable, un renderer, un titre/config propres à l'instance et les coordonnées desktop. Une contrainte conditionnelle garantit au plus un default par propriétaire. Les mutations sérialisent l'utilisateur dans une transaction ; supprimer le default promeut le premier tableau restant, supprimer le dernier rétablit l'onboarding. La liste répare un éventuel jeu ancien sans default en choisissant le premier selon `position, pk`.

`DashboardContext` est construit par l'API à partir de la route et de l'utilisateur authentifié, jamais à partir d'un scope envoyé par React. Il porte déjà `user`, `project` ou `employee` et un objet optionnel ; seul le contexte personnel `user` est actif. Les DataSources fournissent les données selon les périmètres métier existants, les renderers frontend dessinent une forme de données, les WidgetDefinitions décrivent disponibilité et tailles, les WidgetInstances représentent les placements persistés. Les définitions et templates sont en code, pas en base. Les templates Employee, Leader, Lab manager et Blank sont copiés en Dashboard + WidgetInstances lors de la création, sans lien vivant ultérieur.

Le registre `dashboard.registry` agrège les définitions core et les contributions des plugins actifs exposant `DashboardPluginMixin` via le registre plugin existant. Les clés sont stables et uniques. Un plugin ne charge aucun bundle frontend distant : un renderer doit être enregistré localement dans le registre React. L'API vérifie définition, source, scope, `allow_multiple`, config et tailles ; les providers restent responsables de la visibilité des données. La page `/app/dashboard` est accessible à tout utilisateur authentifié sans permission métier nouvelle. Le Dashboard ne confère jamais de droit Project/Employee. Le compteur pilote des Projects utilise `Project.get_instances_for_user("view", user)` ; les deux autres widgets sont liens et note sans fausse donnée métier.

React Grid Layout v2 gère les coordonnées desktop et le drag/resize seulement en personnalisation. La sauvegarde se fait en un PATCH batch. Le breakpoint étroit empile les instances selon `logical_order`, indépendant des coordonnées desktop ; il ne réécrit pas le layout desktop. L'interface garde un seul arbre widget pour les futurs modes présentation et impression. Le contrat `printable` et l'ordre logique permettront un branchement ultérieur sur `PrintRegistry` ; aucun rendu print Dashboard n'est activé en R3.1. Les routes legacy `/dashboard/` et leurs utilitaires de calcul restent intactes pendant la migration.

## Dashboard Core R3.2

`WidgetInstance` conserve séparément `source_key` et `renderer_key` ; `definition_key` reste la clé stable de compatibilité et de tailles R3.1. `DataSource` annonce description, scopes, disponibilité/permissions, renderers compatibles, multiplicité, renderer par défaut et champs de configuration. L'API valide source, renderer, scope, capacité, unicité et configuration lors de POST/PATCH. Les clés de configuration inconnues sont refusées ; types, défauts, champs requis, bornes et choix sont contrôlés côté backend. Un seul objet JSON suffit : les champs DataSource représentent la sélection métier, ceux du renderer la présentation, et une définition R3.1 peut conserver ses anciens champs. Les clés doivent rester distinctes.

Le provider renvoie un payload normalisé par renderer (`{value,label,context,secondary,tone}` pour KPI ; `{items:[{key,label,secondary,date,status,href,icon,tone,severity,current,total,percent}]}` pour les listes). Pour une source multi-renderer, `__renderers__` associe chaque clé compatible à son payload ; l'API ne transmet au frontend que le payload du renderer choisi. Le détail Dashboard reste une réponse batch pour éviter un appel par widget. Les providers utilisent les permissions métier existantes et bornent les listes. Un plugin peut fournir une DataSource compatible avec un renderer core local sans composant React propre ; une WidgetDefinition est alors synthétisée si absente. Aucun bundle distant n'est chargé.

Le registre React rend KPI, liste compacte, alertes et progression sans connaître les modèles métier. La page garde l'état de chargement batch ; `DashboardWidgetFrame` garde menu, absence de données, erreur source, erreur renderer et définition manquante. `dashboardSize` convertit les dimensions RGL en variantes compact/standard/expanded, également en mobile. Les renderers ne dépendent pas de RGL.

## Dashboard sources métier R3.3

Les providers `dashboard.business_sources` réutilisent les querysets de visibilité Project, Fund, Contract Hub et Employee. Milestones/Tasks sont restreints aux Projects visibles ; Leave est restreint aux Employees visibles. `core.tasks` correspond uniquement aux lignes `Milestones` avec une date de début, sans nouveau modèle. Les filtres de scope, statut et échéance sont appliqués côté backend avant `count()` ou une liste bornée ; les relations de liste sont chargées par `select_related`. Les payloads restent ceux des renderers R3.2. `alert-list` est un rendu, pas un modèle Alert global. Les templates métier sont des déclarations source/renderer/config copiées en instances à la création ; ils ne modifient jamais les dashboards existants.

Le jeu R3.5 reste hors du chemin applicatif : `labsmanager.demo_data` orchestre une commande Django transactionnelle sur une base dédiée. Les scénarios sont datés relativement à T0 et les variations utilisent des flux SHA-256 indépendants par namespace et clé stable. Les relations et agrégats financiers passent par les modèles et signaux historiques ; les dashboards de démonstration sont instanciés à partir du même registre de templates que l'API, sans appel HTTP. Aucun marqueur de donnée demo n'est ajouté aux modèles.

Toutes les sources listent au plus cinq éléments par défaut (`limit` configurable de 1 à 20). Projects démarre sur tous les Projects visibles sans filtre actif/retard ; Milestones sur les jalons ouverts visibles, sans horizon ; Funds sur tous les Funds visibles, sans horizon ; Contracts sur tous les Contracts visibles, sans filtre actif/courant/stale ; Employees sur tous les Employees visibles sans mouvement ; Leaves sur les absences des 30 prochains jours ; Tasks sur les tâches ouvertes affectées à l'utilisateur. Les templates surchargent explicitement ces défauts sans déduire un template du rôle utilisateur.

## Dashboard présentation et impression R3.4

`DashboardMode` distingue view, edit, presentation et print. La route authentifiée `/app/dashboard/:id/present` reste hors `AppShell` et relit le même détail propriétaire et catalogue que la page normale ; elle rend `DashboardGrid` sans interactions de modification, avec les mêmes coordonnées et données. Le retour conserve l'identifiant du tableau dans l'URL. Le mode print capture le détail déjà chargé et les définitions du catalogue dans `PrintProvider`, puis `DashboardPrintView` est rendu par le `PrintRegistry` central sans nouvel appel métier. Le shell attend le signal ready avant d'autoriser l'impression.

L'impression A4 paysage trie les instances par `logical_order`, indépendamment des coordonnées écran, et les dispose sur une ou deux colonnes selon leur largeur. Les définitions `printable=false` sont omises ; une définition disparue garde un placeholder court. `DashboardWidgetFrame` partage titre, états et renderer entre modes mais masque les contrôles en présentation et print. Le registre frontend peut fournir un `printComponent` local optionnel par renderer ; sinon le renderer normal est réutilisé en mode print. Aucun chargement de code plugin distant n'est introduit.

## Dashboard Project et finances R3.6

Un Dashboard Project est une instance du même modèle, détenue par un User et liée à un contexte métier Project ; il existe au plus une instance par paire owner/contexte. Depuis R3.6a, `Dashboard.owner` et le contexte sont distincts : le contexte est stocké par `ContentType` et identifiant d’objet, avec `GenericForeignKey`, tandis que deux champs nuls désignent un Dashboard personnel. Le runtime `DashboardContext(context_type, user, context_object)` dérive le type du modèle ; `scope`, `object`, `project` et `for_project` restent des accès de compatibilité pour les sources/plugins R3.6. La résolution API ne prend en charge que `user` et `project` à ce stade, et vérifie `Project.get_instances_for_user("view", …)` avant lecture ou mutation ; le stockage peut accueillir d’autres modèles sans nouvelle colonne. L’ancienne cascade Project est conservée par un signal `post_delete`. Les sources core et plugins traversent le même registre et déclarent leurs scopes ; les sources métier appliquent les filtres Project en plus de leurs règles de visibilité canonique. Un widget personnel peut sélectionner tous ses Projects visibles ou un Project visible précis via config validée côté API.

La source `core.expense-trend` lit `AmountHistory` des seuls `Expense_point` liés aux Funds visibles, sans recomposer les permissions dans le renderer. `Expense_point.amount` et `delta` portent une dépense signée ; la série de consommation prend leur opposé. `value_date` est la date effective, `created_at` le repli. Les variantes cumulée/période et les regroupements sont calculés côté backend avant le contrat de séries générique du renderer SVG `line-chart`. Le KPI d’avancement agrège les Funds éligibles par montant dépensé sur dépense théorique linéaire, avec le repère 1 fixe au milieu de la jauge. L’entrée Admin du menu utilisateur suit uniquement la capability `can_access_admin` fournie par `/me/` et le chemin relatif `admin_url` de Django.

## Dashboard plugin de référence R3.7

`FrenchHollidayPlugin` démontre le contrat `DashboardPluginMixin` sans import du plugin dans le cœur Dashboard : sa `DataSource` déclare `supported_scopes=("user", "project")`, les renderers core `kpi`/`compact-list` et une configuration bornée. Le registre du plugin actif et la `WidgetDefinition` synthétisée par le registre Dashboard suffisent au catalogue et aux instances ; le provider lit seulement les données locales existantes et le setting de zone du plugin. Le contexte Project est transmis comme `DashboardContext` déjà autorisé par l'API, sans condition spéciale dans le plugin. La [documentation développeur](DASHBOARD_PLUGIN_EXAMPLE.md) détaille le contrat.

## Global Search R3.8

`global_search` sépare le registre, le contrat `SearchProvider`, le moteur de matching et les résultats normalisés. Un provider représente un seul type de résultat : il déclare ses champs et leur projection ORM, retourne son queryset visible via les règles métier canoniques, puis construit lui-même le titre, l'URL React et la raison du match. Aucun modèle Django ne doit hériter d'un mixin Search. Le moteur applique les termes libres, classe exact > préfixe > contient et fusionne les résultats ; la requête `SearchQuery` porte dès maintenant texte, termes, filtre provider et emplacements réservés pour filtres de champs/AST. Le schéma `/api/v1/search/schema/` reflète les seuls providers actifs et leurs capacités, sans noms de modèles codés dans le frontend.

Les providers core initiaux Employee et Project recherchent leurs champs principaux dans `get_instances_for_user("view", …)` ; les données et `match_reason` ne sont construits qu'après ce bornage. `SearchPluginMixin` utilise le registre plugin actif existant ; désactiver ou décharger un plugin retire immédiatement ses providers du schéma et de la recherche. Depuis R3.10, les `GenericInfo` visibles de ces deux objets entrent automatiquement dans la recherche libre, sans flag `searchable` sur `GenericInfoType` ni clé de champ par type ; le futur opérateur stable reste `info:`. Tout nouveau modèle métier doit considérer explicitement son intégration à Global Search.

## Global Search UI R3.9

La Topbar héberge un déclencheur discret et un aperçu ; la route `/app/search` conserve requête et provider dans l'URL. Le client frontend consomme directement les contrats `/api/v1/search/` et `/api/v1/search/schema/` ; les groupes, libellés et icônes proviennent du schéma actif avec repli pour un provider disparu. Le résultat fournit sa propre URL React, seule autorité de navigation. Le hook de recherche temporise l'aperçu, annule les requêtes dépassées et garde la page indépendante des providers métier. La visibilité demeure exclusivement contrôlée par le backend.

## Global Search métier R3.10

Les providers Employee, Project, Fund, Contract et Team gardent chacun leur périmètre d'objet. Employee utilise son statut actuel et ses GenericInfo ; Project recherche toutes les participations par rôle, ses institutions et ses GenericInfo. Fund recherche `ref`, financeur et gestionnaire, jamais le nom du Project parent. Contract reprend la visibilité du Hub et ne rend l'email de l'Employee recherchable que si cet Employee est lui-même visible ; Team reprend `visible_teams`. La lecture des GenericInfo suit la visibilité de leur parent comme dans les API contextuelles. Les relations déclarées n'entraînent aucune propagation générale des résultats.

Le moteur combine les termes par intersection de correspondances réparties entre axes déclarés, classe exact > préfixe > contient puis applique des poids comparables aux champs principaux, secondaires et relationnels. Les querysets visibles et filtrés donnent des `counts` exacts par provider avant limitation de l'aperçu ; `groups` continue de compter uniquement les résultats effectivement renvoyés. Les relations sont préchargées pour la projection et la raison du match. La normalisation sans accents n'est pas introduite ici.

## Global Search : langage avancé R3.11

`global_search.language` tokenize la saisie avec positions, puis un parser récursif construit `TextNode`, `KeyNode`, `GenericInfoNode`, `AndNode`, `OrNode` et `NotNode` ; la priorité est NOT > AND > OR. Le texte libre sans opérateur garde le moteur R3.10. Une chaîne quotée est recherchée comme phrase contiguë ; les espaces non quotés restent du texte libre multi-termes. `provider:value` restreint le type de résultat, `field:value` cible tous les providers déclarant ce champ, et `info:"TYPE"="value"` compare nom du type et valeur sans tenir compte de la casse. Les clés sont résolues par le registre actif, avec priorité à la clé provider en cas de collision ; une clé inconnue donne un 400 structuré, tandis qu'un type GenericInfo inconnu donne zéro résultat.

L'engine compile l'AST en conditions ORM par provider, appliquées après `visible_queryset(user)` ; les branches de champs non supportés sont écartées, et NOT ne s'applique jamais à un univers non autorisé. Les providers gardent leurs requêtes et projections métier, sans parser. Le scoring et la raison du match sont calculés sur un ensemble borné de candidats filtrés ; `counts` provient du queryset visible après toute l'expression. La réponse API garde `q` et signale les erreurs par `error=invalid_search_query`, `message`, `position` et `expected`. L'interface affiche ce message et conserve la saisie, sans suggestions syntaxiques avant R3.12.

## Global Search : autocomplétion R3.12

`GET /api/v1/search/autocomplete/?q=...&cursor=...` s'appuie sur le tokenizer R3.11 en mode tolérant pour identifier le contexte au curseur et la plage à remplacer, même dans une requête incomplète ou éditée au milieu. Les positions de l'API sont en unités UTF-16, comme `selectionStart` du navigateur ; le backend les convertit avant/après l'analyse Python. La validation normale de Search reste stricte. Les clés proposées viennent exclusivement du registre des providers actifs et de leurs champs ; `info:` dépend de `supports_generic_info`. Les types GenericInfo viennent des catalogues existants : Employee global pour un utilisateur authentifié, Project seulement si au moins un Project est visible. Les valeurs GenericInfo ne sont pas suggérées.

Les providers déclarent `autocomplete` pour leur valeur principale et `suggestable_fields` pour les champs dont ils proposent des valeurs. Le contrat de base filtre toujours `visible_queryset(user)` avec `field_query`, borne les candidats en SQL, puis projette `suggestion_values` ; chaque provider peut adapter ces valeurs ou contribuer des types GenericInfo. Le schéma annonce cette capacité sans précharger les valeurs. `SearchAutocompleteInput` sert Topbar et SearchPage ; son seul panneau de suggestions prend priorité sur l'aperçu des résultats, remplace la plage renvoyée par l'API et conserve le curseur/focus. Les requêtes sont temporisées et annulées lorsqu'elles sont dépassées. Aucun second parser React n'est introduit.
