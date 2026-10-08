# État de la migration React

## État courant

LabsManager conserve Django comme backend et l'interface historique pendant la migration progressive. La SPA React/TypeScript est montée sous `/app/`, utilise les sessions Django et le cookie CSRF, et appelle les contrats stables sous `/api/v1/`. Le backend reste l'autorité pour les permissions et les périmètres objet.

Les fondations R0, UX1, AUTH1, R1, R1.1, UX2 et UX2.1 sont en place. La liste Employee est utilisable avec recherche, tri, pagination, sélection de ligne et filtres déclaratifs Activité/Supérieur. Son menu de ligne donne accès au même Sheet d'édition que la fiche selon la capacité serveur ; validation navigateur attendue. La topbar contextualisée, l'identité Employee retournée par `/api/v1/me/`, le menu utilisateur et l'i18n navigateur français/anglais sont également en place.

R0, UX1 et AUTH1 ont été validés techniquement et dans le navigateur. R1 a reçu un retour fonctionnel positif sur la VM, R1.1 a été validé fonctionnellement, et UX2/UX2.1 sont validés. Le code de R2 à R2.5b et ses validations ciblées sont présents ; ce document ne revendique pas une validation navigateur globale supplémentaire qui n'aurait pas été consignée.

La fiche Employee React est désormais structurée par une navigation locale et de vraies sous-routes. Le contexte et l'en-tête Employee sont communs ; chaque panneau charge uniquement ses données métier lorsqu'il est affiché.

| Route | État fonctionnel |
|---|---|
| `/app/employees/:id` | Vue d’ensemble migrée ; GenericInfo CRUD R2.7 et exports Word/PDF R2.13a validés ; édition Employee implémentée, validation navigateur attendue |
| `/app/employees/:id/projects` | Projets migrés en lecture seule |
| `/app/employees/:id/contracts` | R2.15 validé ; proposition de synchronisation Employee R2.15a à valider au navigateur |
| `/app/employees/:id/funding` | Contributions et Budgets affectés migrés en lecture seule |
| `/app/employees/:id/leaves` | Absences : calendrier et tableau, CRUD R2.10 validé fonctionnellement |
| `/app/projects` | Liste Project R2.11a validée ; filtre Participant par recherche Employee ajouté ensuite |
| `/app/projects/:id` | Fiche Project, menu/export R2.13a et Project Settings R2.13b validés |
| `/app/projects/:id/tasks` | Planning Project R2.11c : Tableau/Gantt, filtres et CRUD ; R2.11 validé fonctionnellement |
| `/app/projects/:id/calendar` | R2.16/R2.16a implémentés : Calendrier, Liste, Ressources et quatre périodes ; validation navigateur attendue |
| `/app/projects/:id/funding` | R2.12a/b/c validés au navigateur : synthèse Fund unifiée et Expense individuelles |
| `/app/projects/:id/budgets` | R2.14 validé fonctionnellement : Budgets, sélection et Expense contextualisées sous la liste |
| `/app/projects/:id/contributions` | R2.14 validé fonctionnellement : Contributions et CRUD sans Expense |
| `/app/projects/:id/contracts` | R2.15 validé ; proposition de synchronisation Employee R2.15a à valider au navigateur |
| `/app/organizations/institutions` et `/app/organizations/funders` | R2.24b validé fonctionnellement ; présentations Informations/Projets/Contrats en attente de contrôle navigateur |
| `/app/employees/:id/notes` | GenericNotes R2.17 migré ; validation navigateur historique encore indiquée ci-dessous |
| `/app/tools/organization-chart` | R2.26a : organigramme interactif implémenté ; validation navigateur attendue, impression différée à R2.26b |
| `/app/settings` et `/app/settings/{user,interface,notifications,common,stale}` | R2.29a validé au navigateur |
| `/app/settings/lists/{fund,contract,leaves,project,staff,organization}` | R2.29b validé fonctionnellement |
| `/app/settings/admin/{general,users,notifications,plugins}` et détail plugin | R2.29c implémenté ; validation navigateur attendue |

## Employee migré progressivement

### Vue d'ensemble

La Vue d'ensemble contient directement la section fonctionnelle **Informations générales**, sans répéter le titre « Vue d'ensemble » et sans collapse inutile. Elle réunit :

- identité, dates, email et `GenericInfo` dynamiques ;
- indicateurs calculés côté Django : quotités contrat, projet et contribution, et nombre de jalons actifs ;
- statuts courants et historique ;
- hiérarchie directe courante et historique ;
- copie accessible des valeurs via `CopyableValue` ;
- liens vers une fiche Employee seulement lorsque cette ressource est consultable indépendamment.

Les chargements et erreurs des sous-ressources restent locaux. Le détail principal distingue notamment ressource absente, accès interdit et erreur réessayable. La fiche permet désormais de modifier dates, email et activité dans un Sheet, selon une capacité fournie par l'API ; les noms restent immuables après création comme dans le formulaire historique. Le PATCH accepte `is_staff` ou le droit global/objet `staff.change_employee`, avec la même règle pour l'action React et la mutation. Validation navigateur attendue.

### Projets

Le panneau Projets contient deux grandes sections internes persistantes : **Jalons et tâches** et **Participations projets**. Elles utilisent `PersistentCollapsibleSection`, avec une clé `localStorage` stable par type de section, commune à tous les Employee, un état ouvert à la première utilisation et toute la ligne de titre comme déclencheur accessible.

Le tracker Jalons et tâches est alimenté par `GET /api/v1/employees/<id>/milestones/`. La classification est calculée par Django pour l'utilisateur courant, dans l'ordre completed, overdue, due soon, planned, in progress. Le seuil « échéance proche » vient de `NOTIFICATION_ENDPOINTS_MILESTONES_STALE` via `LMUserSetting`. L'interface groupe les éléments en En retard, Échéance proche, En cours, Planifiés et Terminés ; le groupe Terminés est replié initialement. `MilestoneDetailSheet` affiche le détail et, depuis R2.13c, l'édition partielle selon la capacité de chaque item.

Les règles de représentation sont conservées : `start_date is None` désigne un jalon, une date de début désigne une tâche/activité ; `type="q"` affiche `quotity` comme progression, tandis que `type="o"` n'affiche aucune progression chiffrée.

Les participations sont fournies par `GET /api/v1/employees/<id>/project-participations/`. Le profil de charge est fourni par `GET /api/v1/employees/<id>/project-workload/` et calculé depuis les dates et quotités des relations `Participant`, jamais depuis les dates des Project. Le backend construit des segments aux changements de composition, agrège les participations qui se chevauchent pour un même Project et conserve les bornes ouvertes avec `range=all`.

`ProjectWorkloadTimeline` affiche un profil compact en escalier, le seuil de 100 %, la surcharge au-delà de 100 % et la composition par Project via des interactions accessibles. Les fenêtres disponibles sont un an par défaut (aujourd'hui −3 mois / +9 mois), cinq ans (−1 an / +4 ans) et Tout sur requête explicite. Les fenêtres bornées se déplacent de six mois et peuvent revenir à Aujourd'hui ; le mode Tout n'est pas navigable.

La visibilité des jalons, collaborateurs et participations Project est contextuelle à l'Employee visible. Elle permet de comprendre les relations sans accorder un droit autonome sur les ressources liées. Un lien n'est présenté que si le droit indépendant et une route réelle existent ; aucune fausse navigation Project n'est créée.

### Contrats

R2.15 remplace la présentation R2.4b : Employee et Project utilisent `ContractSection`, avec sélection de ligne, détail `ContractDetail` en lecture sous la liste, puis `ExpenseSection`. Le Sheet sert uniquement à créer ou modifier ; les actions de ligne passent par `ItemActionMenu` et `ConfirmDialog`. Les capacités Contract restent propres à l'endpoint Employee ou Project. Les contrats Employee conservent leur tri temporel côté Django. `Contract.is_active` n'exprime que **Suivi RH** ; il n'existe pas d'autre état actif/inactif. Depuis R2.24b, les liens Institution/Financeur consultables mènent aux fiches React.

### Financement

R2.5 remplace les anciens placeholders Contributions et Budget par la route commune `/funding`. La première section affiche les Contributions de l'Employee en cours, futures et historiques, avec Fund, Project, type de coût, description, période, quotité et montant. Les types RH incluent les descendants d'un `Cost_Type.is_hr=True`.

Le profil temporel additionne les `Contribution.quotity` actives à chaque période depuis leurs propres bornes, sans utiliser les dates du Fund ou du Project. Il reprend les fenêtres, la navigation, le seuil 100 %, la surcharge et les interactions accessibles du profil Project.

La seconde section affiche les Budget items explicitement affectés à l'Employee. Le backend fournit le montant budgété, la dépense nette signée, le disponible calculé par `amount-expense` et le ratio signé lorsqu'il est calculable. Une écriture négative augmente le disponible et reste affichée comme remboursement, sans barre positive trompeuse. L'interface conserve aussi le vrai taux au-delà de 100 %, signale sobrement un disponible négatif et n'affiche aucune barre lorsque le ratio n'est pas calculable. Les deux sections sont repliables avec une préférence persistée par type de section.

### Absences et Calendar Core

R2.6a remplace le placeholder Congés par une lecture Calendar/Tableau. Depuis R2.16c, le calendrier utilise les mêmes scopes FullCalendar que Project : 15 jours, Mois, 2 mois et Année, avec précédent, suivant et Aujourd'hui ; chaque requête `/calendar/` est bornée. Le renderer synthétique cinq ans a été retiré. Le tableau `/leaves/` expose Type, Début, Fin, Durée et Commentaire. Les deux modes partagent le filtre de type et les bornes de période, et le mode choisi est persisté.

R2.6a.2 clôt ce périmètre read-only. Les plugins exposent maintenant leurs filtres normalisés depuis `/calendar/filters/`; React rend sans connaissance plugin les types select, checkbox, radio, texte et couleur. Le filtre dynamique de zone FrenchHolliday est transmis aux requêtes calendrier et reste sélectionné pendant la navigation temporelle. Les quatre scopes partagés rendent maintenant les événements via FullCalendar, y compris les événements de fond des plugins, et ouvrent le même Sheet Leave.

Les demi-journées restent explicites à l'écran et dans le Sheet avec les libellés partagés Matin, Après-midi, À partir de midi, Jusqu'à midi et Midi → midi. Les événements de plugins sont transmis comme de vrais fonds FullCalendar et n'ouvrent pas le détail Leave. Les lignes du tableau et les événements Leave sont accessibles au clavier. Le producteur FrenchHolliday renvoie désormais les apostrophes brutes, sans double échappement HTML.

Le backend utilise désormais un Calendar Core commun. Le mixin plugin, `FrenchHollidayPlugin`, la façade historique `/calendar_plugin/` et l'API Employee délèguent au même `CalendarService` ; aucun second moteur d'agrégation n'est maintenu.

## Principe de structuration retenu par R2.4a

- Les sous-routes séparent les grands domaines Employee et portent l'URL, le refresh, l'historique navigateur et le panneau actif.
- Les collapsibles structurent l'intérieur d'un panneau qui contient plusieurs grandes sections, lorsque cela réduit réellement la navigation verticale.
- Un panneau avec une seule grande section ne reçoit pas un collapse artificiel.
- Le header et l'identité Employee restent communs à toutes les sous-routes.

## API Employee v1 disponible

- `GET /api/v1/employees/`
- `GET /api/v1/employees/<id>/`
- `GET/POST /api/v1/employees/<id>/generic-info/`
- `PATCH/DELETE /api/v1/employees/<id>/generic-info/<info_id>/`
- `GET /api/v1/generic-info-types/`
- `GET /api/v1/employees/<id>/statuses/`
- `GET /api/v1/employees/<id>/hierarchy/`
- `GET /api/v1/employees/<id>/milestones/`
- `GET /api/v1/employees/<id>/project-participations/`
- `GET /api/v1/employees/<id>/project-workload/`
- `GET /api/v1/employees/<id>/contracts/`
- `GET /api/v1/employees/<id>/contracts/<contract_id>/`
- `GET /api/v1/employees/<id>/contributions/`
- `GET /api/v1/employees/<id>/contribution-workload/`
- `GET /api/v1/employees/<id>/budgets/`
- `GET /api/v1/employees/<id>/leaves/`
- `GET /api/v1/employees/<id>/calendar/`
- `GET /api/v1/employees/<id>/calendar/filters/`

Ces contrats restent en lecture seule, sauf la collection GenericInfo désormais étendue par R2.7. La résolution de l'Employee cible reste bornée par `Employee.get_instances_for_user("view", ...)`; un objet absent ou hors périmètre produit le même `404`.

## Validation et prochaine étape

R2.6a est implémenté en lecture seule. La validation couvre 78 tests backend combinant toute l'API Employee, Calendar Core, plugin et façade historique ; 30 tests frontend ciblés ; ESLint ; TypeScript ; build Vite ; `manage.py check` et le contrôle de diff. Le build conserve l'avertissement existant sur le chunk JavaScript supérieur à 500 kB.

Le correctif R2.6a.1 ajoute 7 tests frontend ciblés couvrant l'adaptateur et le nouveau renderer, puis repasse ESLint, TypeScript et le build Vite. La suite backend combinée de 78 tests, incluant la régression d'apostrophe, ainsi que `manage.py check` réussissent également. La validation navigateur du rendu FullCalendar a été confirmée par l’utilisateur avec la clôture R2.6a.2.

R2.6a.2 ajoute 11 tests frontend ciblés pour les filtres génériques, les demi-journées et les renderers Calendar, et porte la suite backend Calendar/plugins/API Employee à 83 tests. ESLint, TypeScript, le build Vite et `manage.py check` réussissent ; le build conserve l'avertissement de chunk supérieur à 500 kB. La validation navigateur R2.6a.2 a été confirmée par l’utilisateur avant l’implémentation R2.7.

La roadmap de référence distingue R2.8 Gantt Employee en lecture seule, les futurs Gantt Project/global, R2.9 dépendances déclaratives Task/Milestone sans scheduling automatique et R2.10 mutations Leave. R2.6a.2 n'avait commencé aucun de ces lots.

## Éléments différés

- Création, suppression et mutations Employee hors édition limitée de la fiche.
- Navigation Project autonome et migration du détail Project.
- Panneau Notes.
- Exposition de liens vers une ressource liée tant que son droit indépendant ou sa route React ne sont pas disponibles.
- Intégration du build React au déploiement Nginx/Docker, toujours distincte de la migration fonctionnelle Employee.


## R2.7 — GenericInfo et socle de mutation : terminé et validé

Implémentation CRUD validée : collection enveloppée et capacités contextuelles, catalogue
global des types existants, create et modification de valeur en Sheet, suppression confirmée,
erreurs DRF, verrou de soumission, actualisation locale depuis la réponse serveur et relecture.
Une relecture échouée est signalée séparément du succès de mutation et ne rejoue pas l’écriture.

La rule `change_partial_employee` étend le droit historique de modification à l’Employee lié
pour CREATE seulement. `change_employee` global/objet reste le droit UPDATE/DELETE ;
`common.self_edit` conserve donc les mutations complètes de sa propre fiche. Lecteurs sans
ces droits : aucun contrôle de mutation. Le type est immuable après création et l’Employee
est imposé par l’URL. Doublons de type et valeurs vides/nulles restent autorisés.

La migration staff.0014 convertit les icônes connues en identifiants Lucide. Les inconnues
sont conservées exactement ; CircleQuestionMark est le fallback React. Le legacy Employee
conserve ses textes sans rendu FAIcon ; Project conservait alors son comportement historique.
L’utilisateur confirme la migration `staff.0014` appliquée et vérifiée sur la base de
développement, ainsi que la validation navigateur React et du legacy Django après migration.
Les correspondances vérifiées sont : Badge, matricule Inserm et matricule CHU → Badge ;
ORCID → Contact ; HDR → Search ; CSS/BAP/CNU → Columns3 ; RPPS → Stethoscope.

La validation manuelle confirme les permissions, la création, la valeur vide, les doublons,
la modification, le type immuable, l’annulation/confirmation DELETE, les interactions
hover/clic/clavier et le responsive. **R2.7 est clôturé.** Le futur déploiement production
reste distinct de cette validation en développement.

Le contrôle global `makemigrations --check --dry-run` détecte des écarts préexistants dans
`endpoints.Milestones.start_date` et `project.Participant.employee`. Ces modèles n’ont pas
été modifiés par R2.7 ; aucune migration hors périmètre n’a été créée.

R2.8 est **validé manuellement** : Gantt Employee, switch Liste/Gantt, Calendar, filtres
CalendarEventMixin, ouverture du Sheet Task/Milestone et contrôles navigateur sont OK.
La fiche Project React, la vue globale, Notes et les mutations Leave restent hors périmètre.

### R2.8 — validation terminée

Le switch Liste/Gantt conserve les ressources métier Employee chargées et l'état des filtres
Calendar. Le Gantt regroupe participations, tâches et jalons par Project, réutilise le Sheet
des jalons/tâches, propose 6 mois/1 an/2 ans et suit le thème clair/sombre. Les événements
Calendar ordinaires sont rendus ; les événements de fond sont conservés côté API mais omis
du rendu SVAR OSS (pas de mécanisme public adapté à leurs plages et couleurs avec les
échelles actuelles). Aucun endpoint
métier Gantt ni migration BDD n'a été ajouté.

Tests ciblés : 8 tests API Employee Calendar et 5 tests FrenchHolliday réussis ; 2 fichiers
frontend / 17 tests réussis après correction du scénario de fermeture du Sheet. `manage.py
check`, TypeScript, ESLint et build ont réussi. Le build émet l'avertissement de taille de
chunk >500 kB. Les tests manuels sont globalement positifs ; l'interaction task/milestone
restait à corriger. Le correctif écoute maintenant l'action publique SVAR `select-task`
et transmet l'identité métier au Sheet existant. La vérification navigateur de ce clic
et des cas associés a ensuite été réalisée avec succès ; R2.8 est validé UX.
Le contrôle ciblé du correctif a réussi : **3 fichiers / 18 tests frontend**, dont la
sélection SVAR simulée et l'absence d'action Employee pour Project/Participation.

### R2.9 — dépendances Task/Milestone validées fonctionnellement

Un modèle `MilestoneDependency` relie deux `Milestones` (Task ou Milestone), y compris entre
Projects. La migration additive `endpoints.0006` a été créée pour ce lot ; son état
d'application actuel doit être vérifié par environnement. Auto-dépendance, doublon et cycle sont refusés ; l'ordre temporel incohérent
est seulement signalé. L'API v1 utilise `Project.get_instances_for_user("change", ...)` pour
les deux Projects au POST/DELETE. Le Sheet existant porte le CRUD ; le Gantt Employee affiche
uniquement les liens dont les deux extrémités sont déjà dans son scope, en lecture seule.
La validation fonctionnelle manuelle R2.9 est réussie, y compris la lecture pour un lecteur
seul, les mutations selon `change` et l'ouverture du formulaire d'ajout à la demande.
L'API de lecture accepte un élément visible via Project ou via le contexte Employee et
masque les prédécesseurs non visibles. L'état d'application de `endpoints.0006` sur chaque
environnement reste à vérifier séparément avant déploiement.
Contrôles réalisés : **14 tests backend R2.9** sur PostgreSQL de test ; **23 tests frontend
ciblés** (Gantt, Sheet, page Employee) ; `manage.py check`, TypeScript, ESLint et build OK.
Le build conserve l'avertissement de taille de chunk connu. Le contrôle Django
`makemigrations endpoints --check --dry-run` relève seulement l'écart préexistant sur le
`help_text` de `Milestones.start_date` ; aucune migration hors R2.9 n'a été ajoutée.

### R2.10 — CRUD Leave validé fonctionnellement

La fiche Employee conserve Tableau et Calendrier avec un même Sheet consultation/création/
modification. `change_employee` gouverne les mutations ; les capacités sont exposées par
l'API. Le catalogue hiérarchique Leave_Type est sélectionnable à tous les niveaux. La
validation backend refuse les chevauchements pour un même Employee et type tout en
autorisant deux demi-journées contiguës. Toute suppression passe par confirmation.
À la clôture de R2.10, Mois et Année permettaient une sélection de dates convertie depuis la fin exclusive
FullCalendar ; cinq ans était une synthèse sans sélection. Mois et Année permettaient aussi
le déplacement et le redimensionnement des Leave autorisés, avec conservation des périodes
ST/MI/EN et retour à la position initiale si le PATCH échoue. La vue Année utilise
`dayGridYear` à cette date. R2.16c remplace depuis ces vues par les quatre scopes communs et supprime cinq ans. Les événements Leave continuent
de passer par Calendar Core et CalendarService. Aucune migration de schéma R2.10.
La validation navigateur R2.10 est terminée avec succès ; la lisibilité de la vue annuelle
pourra être améliorée ultérieurement. Les contrôles ciblés figurent dans COMMANDES.md.
Les tests automatisés R2.10 passent (**8 backend, 16 frontend**) sur PostgreSQL de test et
Vitest ; ESLint et le build
Vite direct passent. Le contrôle TypeScript global reste bloqué par trois erreurs
préexistantes de l'évolution Gantt 60/120 mois (types de fenêtre et traduction anglaise),
hors du périmètre R2.10 ; `npm run build`, qui commence par TypeScript, n'est donc pas validé.


### R2.11a — Project List validée, filtre Participant enrichi ensuite

`/app/projects` affiche la liste Project avec recherche, tri initial par nom croissant,
pagination, filtres legacy pertinents, relations compactes et capacités serveur par ligne.
La validation navigateur R2.11a a été confirmée par l'utilisateur. Le filtre Participant
utilise ensuite le même sélecteur Employee que le filtre Supérieur, inclut les Employees
inactifs dans sa recherche et transmet leur identifiant au filtre Project ; elle est
incluse dans la validation fonctionnelle R2.11 confirmée par l'utilisateur.
Le correctif passe les 8 tests backend Project et 32 tests frontend ciblés Project/Employee.
Le filtre visible Active=true est initialisé par le même mécanisme déclaratif que sur la
liste Employee ; il peut être retiré pour retrouver les éléments inactifs. Les deux listes
partagent aussi le badge Actif/Inactif, la sélection de ligne et les en-têtes triables.
La création et l'édition utilisent un Sheet limité aux champs propres à Project ; la
suppression demande confirmation. Après création, l'identifiant retourné par le POST
conduit directement à la route React `/app/projects/:id`, désormais complétée par R2.11b.
Aucune migration de schéma ni dépendance R2.11a.
Les contrôles ciblés passent : 8 tests backend, 50 tests frontend, ESLint ciblé,
`manage.py check` et build Vite direct. Le contrôle TypeScript global conserve les trois
erreurs Gantt/i18n préexistantes.

### R2.11b — ProjectSingle et vue d’ensemble

La fiche Project React affiche l’en-tête (nom, statut, dates), une navigation locale dont
seule la Vue d’ensemble est active, puis quatre blocs : informations du projet,
GenericInfoProject, institutions et participants. Les trois collections enfants sont
préchargées dans le détail API avec leurs capacités propres. Les écritures sont
contextuelles au Project de l’URL et protégées côté backend ; le choix d’un Employee
respecte sa visibilité. Les Sheets gèrent création et modification, avec confirmation
avant suppression. Le composant GenericInfo est partagé avec la fiche Employee.
Les autres sections Project et les données financières restent pour des lots futurs.
Aucune migration de schéma ni nouvelle dépendance. La validation navigateur R2.11b a
été confirmée dans la validation fonctionnelle R2.11 ; les contrôles automatisés sont
consignés dans COMMANDES.md.
Le correctif UX remplace les Cards par trois colonnes légères et déplace les actions
d’élément dans des menus `…`. Le parcours Project R2.11 est validé fonctionnellement.
Le complément R2.11b `project.0008` prépare la conversion des icônes
GenericInfoTypeProject vers Lucide. La migration est créée mais **non appliquée** à la
base de développement ; sa validation navigateur reste à faire après application manuelle.

### R2.11-i18n — normalisation transversale React

Les textes UI statiques du shell, des filtres, des listes Employee/Project et de la fiche
Project utilisent les catalogues FR/EN, y compris les libellés accessibles. Les noms et
valeurs métier provenant de l’API restent inchangés. Les deux catalogues ont les mêmes
clés et interpolations ; la règle permanente est précisée dans ARCHITECTURE.md.
Les libellés dynamiques Calendar/plugins et les erreurs métier Django/DRF restent servis
selon la négociation de langue du backend. Le frontend choisit `fr` si aucune langue
`fr`/`en` n’est annoncée par le navigateur, tandis que Django (`LocaleMiddleware`,
`LANGUAGE_CODE=en-us`) peut alors répondre en anglais : ce décalage reste à traiter
séparément. Les 207 tests frontend et ESLint passent, ainsi que le build Vite direct.
Le contrôle TypeScript ne conserve que les deux erreurs de type Gantt préexistantes
(`EmployeeGanttPanel.tsx:18`, `SvarGanttAdapter.tsx:100`). La validation navigateur
de ce lot reste à faire.

### R2.11-refactor-1 — registre de réutilisation et patterns UX

La méthode « rechercher et réutiliser avant d'implémenter » est inscrite dans
ARCHITECTURE.md. REUSABLE.md devient le sixième document canonique à consulter au
début de chaque lot ; il recense les briques frontend/backend/API déjà établies,
leurs frontières métier et les patterns UX de menus contextuels, suppression
confirmée, Sheets, listes, filtres et i18n. L'inventaire relève des opportunités
et écarts existants à examiner dans les lots concernés, sans harmonisation
transversale immédiate. Aucune micro-factorisation n'a été jugée suffisamment
évidente et locale : ce lot est documentaire, sans modification du code
applicatif, des permissions, des contrats, de l'UX ou des dépendances.
Contrôles documentaires : liens du registre résolus et `git diff --check` réussi.

### R2.11-refactor-1b — menu contextuel canonique

`ItemActionMenu` fournit désormais le menu standard `…` Edit/Delete de GenericInfo,
Institutions et Participants. Son contrat expose le déclencheur et le `finalFocus`
Base UI pour préserver le passage du menu au Sheet ou au dialogue de confirmation.
`GenericInfoSection` conserve les capacités métier, mutations, overlays et choix du
focus de repli après suppression ; son DropdownMenu local a été retiré. Aucun
changement de permission, de contrat API ou de fonctionnalité métier. La validation
navigateur ciblée du focus et des interactions reste à réaliser.
Contrôles : 54 tests frontend ciblés réussis, ESLint ciblé, TypeScript, build Vite
direct et contrôle du diff réussis. Le build conserve l'avertissement connu de
taille de chunk.

### R2.11-refactor-2 — Shared Planning Core

La liste Tasks/Milestones Employee utilise désormais `PlanningMilestoneTable`, composant
commun prévu pour le futur scope Project, et montre les Employees affectés sous chaque
item. Le serializer et les helpers Planning backend partagent qualification temporelle,
préchargement, filtres facultatifs `search`/`kind` et contrat de lecture ; le gate Employee
reste appliqué avant le queryset. Le même tableau de jalons alimente liste et Gantt.
`PlanningGanttAdapter` convertit ce contrat avec participations facultatives ; le panel
Employee conserve son orchestration Calendar/plugins. Le bouton de suppression des
dépendances devient un `ItemActionMenu` Delete seul, suivi du `ConfirmDialog` existant.
Les filtres Planning `search` et `kind` sont acceptés par le backend et sérialisables par
le client ; aucun contrôle UI Planning nouveau n'est activé dans Employee. Les filtres
Calendar/plugins existants ne changent pas et portent toujours sur les événements.
Aucun endpoint ou écran Project Planning, ni CRUD Task/Milestone React, n'est ajouté ici.
Le futur CRUD Project devra borner les Employees affectables aux participants du Project
côté backend. La validation navigateur ciblée Employee reste à faire.
Contrôles ciblés : 21 tests backend Planning/Employee/dépendances réussis ; 38 tests
frontend Planning/Gantt/i18n réussis, puis 2 tests de sérialisation des filtres ;
`manage.py check`, ESLint ciblé, TypeScript et build Vite direct réussis. Le build
conserve son avertissement de taille de chunk connu.

### R2.11c — Project Planning

La section Jalons et tâches de Project est active. L'API Project autorise la visibilité
du projet avant de filtrer et sérialiser la collection Planning commune ; les capacités
et contrôles POST/PATCH/DELETE reposent sur `change_project`. Le formulaire limite les
Employees affectables aux Participants, contrainte également validée côté backend.
Le même `PlanningMilestoneTable` et le même contrat alimentent Employee et Project ;
la bascule Tableau/Gantt Project utilise une seule collection filtrée par recherche,
type et Employee. Consultation et dépendances réutilisent le Sheet existant ; création
et édition utilisent un Sheet avec choix explicite Tâche/Jalon. Le passage à Jalon
efface `start_date`. Suppression avec `ItemActionMenu` et `ConfirmDialog`.
Le Gantt reste un renderer neutre ; Planning produit ses éléments via son adapter et
la page Project choisit la contribution affichée. Aucun Fund ni Calendar Project ajouté.
Contrôles : 3 tests backend ciblés, 31 tests frontend ciblés, `manage.py check`,
ESLint ciblé, TypeScript, build Vite et contrôle du diff réussis. R2.11c a ensuite
été validé fonctionnellement au navigateur ; le build conserve
l'avertissement connu de taille de chunk.

### R2.11c-fix-1 — détail Planning, dépendances et formulaire

Le Sheet Planning partagé rend le Project navigable lorsque le contrat donne
`project.can_view`. Depuis Employee, les prédécesseurs sont consultables sans contrôle
d'ajout ou de suppression, même si l'utilisateur possède des droits Project. Depuis
Project comme depuis Employee, les lignes de successeurs ne proposent ni édition ni suppression ;
Project conserve la gestion des prédécesseurs selon les capacités backend. L'API lit ces deux
directions depuis la base et masque les items hors du périmètre visible.
Le formulaire Planning emploie une même ligne checkbox/libellé pour « Terminé » et
les Participants affectables, sans changer les règles d'affectation ni le payload.
Contrôles : 18 tests backend dépendances et 42 tests frontend ciblés réussis ;
`manage.py check`, ESLint ciblé, TypeScript et build Vite réussis. Le build conserve
son avertissement connu de taille de chunk. Ce correctif est inclus dans la
validation fonctionnelle R2.11 confirmée par l'utilisateur.

Le complément « Ajouter un successeur » est disponible depuis Project lorsque
`can_add` autorise la modification du Project courant. La sélection est bornée aux
Projects modifiables ; le POST existant vérifie `change` sur les deux Projects et
conserve ses validations de cycle et de doublon. Employee reste sans mutation et les
lignes de successeurs n'ont toujours pas d'action de suppression.
Contrôles du complément : 18 tests backend dépendances et 15 tests frontend ciblés
réussis ; contrôle Django, ESLint ciblé, TypeScript et build Vite réussis.

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


### Inventaire des fichiers R2.7

Les modifications préexistantes des lots antérieurs sont conservées. Les fichiers déjà
présents mais non suivis par Git sont classés « modifiés », pas « créés par R2.7 ».

Fichiers existants modifiés (22), chemins relatifs à la racine de distribution :

```text
backend/staff/models.py
backend/staff/rules.py
backend/staff/api_v1.py
backend/staff/serializers_v1.py
backend/staff/forms.py
backend/staff/admin.py
backend/labsmanager/urls_v1.py
backend/labsmanager/serializers.py
backend/settings/views.py
backend/templates/employee/employee_info_table.html
backend/labsmanager/tests/test_api_v1_employees.py
frontend/src/api/employees.ts
frontend/src/api/errors.ts
frontend/src/pages/EmployeeOverview.tsx
frontend/src/pages/useEmployeeResource.ts
frontend/src/pages/EmployeeDetailPage.test.tsx
frontend/src/i18n/i18n.ts
docs/react-migration/ARCHITECTURE.md
docs/react-migration/DECISIONS.md
docs/react-migration/STATUS.md
docs/react-migration/MATRIX.md
docs/react-migration/COMMANDES.md
```

Fichiers créés (15) :

```text
backend/staff/permissions_v1.py
backend/staff/migrations/0014_genericinfotype_icon_lucide.py
backend/labsmanager/tests/test_api_v1_generic_info.py
backend/labsmanager/tests/test_generic_info_icons.py
frontend/src/api/useMutation.ts
frontend/src/api/useMutation.test.tsx
frontend/src/api/errors.test.ts
frontend/src/components/common/ConfirmDialog.tsx
frontend/src/components/common/ConfirmDialog.test.tsx
frontend/src/pages/EmployeeGenericInfo.tsx
frontend/src/pages/EmployeeGenericInfo.module.css
frontend/src/pages/EmployeeGenericInfo.test.tsx
frontend/src/pages/GenericInfoFormSheet.tsx
frontend/src/pages/genericInfoIcons.ts
frontend/src/pages/useEmployeeResource.test.tsx
```

Aucun fichier supprimé, aucune dépendance ajoutée, aucun commit ni changement R2.8.

### R2.12a — Project Funding Core

La sous-route Project Financements est active. La synthèse consolidée repliable
présente Cost_Type × Fund et les totaux par type, Fund et Project, puis la liste
sélectionnable des Funds et le détail du Fund choisi. Fund, Fund_Item et
Expense_point disposent de Sheets de création/édition, menus `…`, confirmations de
suppression et capacités vérifiées par l'API. Les situations de dépense sont en
lecture seule en mode `e`, modifiables selon les droits en modes `s`/`h`.
La suppression d'une ligne Fund_Item encore couverte par un Expense_point est
refusée explicitement pour éviter sa recréation immédiate par les calculs historiques.
La sélection reste en place lors du repli et des actualisations. La mise à jour de
la date de fin du Project est une option explicite, contrôlée par `change_project`.
La convention de signe historique est conservée ; Budget/Contribution gardent
leur convention différente. Le détail des Expense, leur CRUD, Budget et
Contribution autonomes restent pour R2.12b ou des lots ultérieurs.
Le cache historique `Fund.expense_f` peut rester obsolète après disparition du
dernier Expense_point ; il n'est pas exposé par R2.12a et reste une dette à traiter.
Aucune migration ni dépendance ajoutée. Les contrôles automatisés R2.12a sont
consignés dans COMMANDES.md : 19 tests backend et 50 tests frontend ciblés réussis,
contrôles Django/TypeScript/ESLint et build Vite réussis. **Validation navigateur
R2.12a attendue** lors de la livraison initiale ; elle a depuis été validée au navigateur.

### R2.12b — Expense individuelles Fund/Contract

L'API v1 fournit une collection Expense paginée et filtrée par référence,
description, Cost_Type et dates, avec deux scopes serveur distincts : Fund et
Employee/Contract. Le même `ExpenseSection` React est utilisé dans Project Funding
et sous le Contract sélectionné. CRUD, choix indépendants de Contract et Budget, promotion
et désaffectation multi-table à PK stable, contrainte Cost_Type RH pour Contract,
montants signés et statuts historiques sont pris en charge. La rule
`expense.change_expense` lit maintenant le Fund réel via `fund_item`.

En mode `s`, seules les Expense liées à un Contract ou Budget sont créables ; les
situations manuelles restent la source des montants Fund. Les modes `e` et `h`
autorisent le CRUD général et la synchronisation confirmée. Celle-ci dépend de
`fund.change_fund` objet, appelle `calculate_expense(force=True)` et actualise les
totaux. Les mutations déclenchent la relecture de la collection, du détail Fund
et de la matrice Project. Les capacités d'écriture sont calculées et revérifiées
par le backend ; les noms métier ne sont pas traduits par React.

Aucune migration de schéma ni dépendance. R2.12b a été validé au navigateur ;
les résultats automatisés figurent dans COMMANDES.md.

### R2.12c — Synthèse financière Fund unifiée

Dans Project Funding, le Fund sélectionné affiche désormais une seule synthèse
financière par Cost_Type, puis les Dépenses individuelles inchangées. Le bloc
« Détail : Fund » et les tableaux séparés Synthèse par type, Fund_Item et
Expense_point ont disparu ; la matrice Project est rétablie au-dessus de la liste
seulement lorsque plusieurs Funds sont visibles. Elle est repliée par défaut,
ouvrable explicitement sans persistance, et ne modifie pas le détail Fund.
Les lignes de ce dernier montrent côte à
côte les objets réels et le disponible fourni par l'API. Date et montant `—`
désignent un objet absent ; un montant réel nul reste `0,00 €`.

Le menu global `…` du titre propose les créations selon les capacités backend ;
chaque Fund_Item et Expense_point garde son propre `ItemActionMenu`, Sheet et
confirmation de suppression. Les modes `s`/`e`/`h`, le calcul financier, les
permissions et les API restent inchangés. Aucune migration ni dépendance. La
validation navigateur R2.12c a été confirmée ; les contrôles automatisés sont
consignés dans COMMANDES.md.

### R2.13a — Menu d’entité et exports Project/Employee

Les headers Project et Employee utilisent le même `EntityActionMenu`. Project
propose Modifier via le `ProjectSheet` existant, puis Export Word/PDF selon des
capacités séparées. Dans R2.13a, Employee proposait uniquement Export Word/PDF :
l'édition Employee React et son API PATCH étaient différées vers un lot dédié,
sans limitation du composant commun. Elles ont depuis été ajoutées à la fiche.

Un `ReportExportDialog` centré commun charge les templates du type demandé,
pré-sélectionne le premier, et ajoute les dates facultatives uniquement pour
Employee. L'API v1 revérifie visibilité et droit de rapport avant de déléguer
aux renderers Word/PDF historiques ; les quatre URL de rendu direct héritées
appliquent désormais ces mêmes contrôles. React télécharge directement le fichier.
L'API et les tests automatisés sont en place. R2.13a a été validé au navigateur ;
pas de migration de schéma ni nouvelle dépendance.

### R2.13b — Project Settings et infrastructure réutilisable

Le menu d'entité Project propose « Paramètres du projet » selon la capacité
`can_change_settings` calculée côté backend (permission globale Settings ou droit
de modification Project). Un Sheet générique lit les trois définitions
`LMProjectSetting` du core Django, affiche leurs noms, descriptions, types et choix,
et enregistre immédiatement chaque modification. GET expose les valeurs par défaut
sans créer de lignes ; PATCH crée la ligne au premier changement via `save()` et
ses validations/hooks. Les booléens et les choix sont validés côté serveur.

La fermeture après mutation recharge le Project et le panneau Planning ou Funding
actif. Changer `EXPENSE_CALCULATION` ne convertit aucune donnée ; les capacités et
calculs Funding sont relus. Aucun changement des règles Employee Planning, aucune
migration de schéma ni dépendance. Tests automatisés en place ; R2.13b a été
validé au navigateur.

### R2.13c — Édition limitée du Planning Employee

La liste Employee publie `can_change` par tâche/jalon via la rule
`endpoints.change_milestones`. Le même `MilestoneDetailSheet` reste en consultation
par défaut ; Modifier ouvre seulement les champs description, progression
(`quotity` pour le type quantifiable) et terminé (`status`). Le PATCH Employee
refuse tout autre champ et sauvegarde l'instance après validation. Le comportement
historique de cohérence entre progression et terminé reste celui du Planning
Project. Après succès, la liste et le Gantt sont actualisés ; ce dernier reste
sans drag/drop ni resize. Création, suppression et dépendances restent en lecture
seule depuis Employee. Project Planning conserve son CRUD complet. Tests
automatisés en place ; validation navigateur R2.13c attendue.

### R2.13d — Boutons d'action explicites React

La passe transversale harmonise les actions explicites Ajouter/Créer, Modifier et
Supprimer avec `Plus`, `Pencil` et `Trash2` accompagnés d'un libellé traduit.
L'édition Employee du `MilestoneDetailSheet` se trouve désormais à droite dans
l'en-tête du Sheet. Les menus contextuels, capacités, mutations, confirmations et
parcours métier restent inchangés. Tests frontend automatisés exécutés ;
validation navigateur R2.13d attendue.

### R2.14 — Project Budgets & Contributions

Les sous-routes Project `/budgets` et `/contributions` sont deux entrées de navigation indépendantes, chacune avec sa liste et son Sheet de détail. Le socle `BudgetAbstract` partage champs, formulaire, Sheet et contrôle de mutation ; les dates restent propres aux Contributions. L’API Project borne les objets au Project et aux Funds visibles et expose les capacités issues de `project.change_project`. `full_clean()` conserve la validation historique de `emp_type` et `employee` selon le Cost_Type RH ; le modèle ne contrôle pas actuellement `contract_type` dans `clean()`. Les mutations passent par `save()`/`delete()`.

La sélection d’un Budget affiche `ExpenseSection` sous la liste, hors du Sheet de détail : Fund et Budget sont imposés par le contexte, les dépenses et le disponible sont relus après mutation. Contribution ne présente aucune Expense. La convention historique `available = amount - expense`, avec dépense nette signée, est conservée ; aucune agrégation, ventilation, version ni procédure d’approbation n’est ajoutée. La suppression d’un Budget entraîne historiquement celle de ses Expense liées (`on_delete=CASCADE`) et le dialogue le précise. R2.14 a été validé fonctionnellement au navigateur par l'utilisateur. Aucune migration de schéma ni dépendance.

### R2.15 — Contracts Project et Employee

La section Project borne les Contracts à son Project, aux Funds visibles et aux Employees participants ; un leader Project peut les gérer via `project.change_project`, sans autorité RH Employee. La fiche Employee conserve ses permissions Contract distinctes. L'API expose les capacités propres à chaque contexte et vérifie les mêmes droits sur POST/PATCH/DELETE. Les options et écritures valident Fund et Participant côté serveur. Le détail partagé affiche les relations et les montants calculés par le modèle ; les Expense du Contract sélectionné restent sous le détail, avec Contract et Fund imposés par l'API. R2.15 a été validé fonctionnellement par l'utilisateur.

### R2.15a — Proposition de synchronisation de la date de fin Employee

Après création ou modification d'un Contract, l'API propose facultativement sa `end_date` pour `Employee.exit_date` (nom réel du champ) si elle diffère, qu'aucun autre Contract du même Employee ne finit plus tard et que l'utilisateur possède `staff.change_employee`. La proposition n'écrit rien : une confirmation explicite commune aux fiches Project et Employee appelle une mutation dédiée qui revérifie droit et pertinence avant `Employee.save()`. Refuser conserve la date actuelle ; le Contract reste enregistré. Tests ciblés réalisés ; validation navigateur R2.15a attendue.

### R2.16 — Calendar Project

La sous-route Project Calendar propose Calendrier, Liste et Ressources. Les trois modes consomment le même flux borné `LabsManagerCalendarEvent[]` : Leave des Employees participants produits par le domaine Leave, puis événements additionnels des plugins via `CalendarService`. Employee utilise désormais le même producteur Leave. Le mode Ressources utilise FullCalendar Scheduler avec les Participants comme ressources et la clé AGPL. La liste réutilise le tableau Leave ; le détail et la création réutilisent le Sheet Leave. La lecture dépend de la visibilité Project ; les mutations contextuelles vérifient Participant et `staff.change_employee`, sans exiger la visibilité autonome de la fiche Employee. Aucun plugin Leave ni migration de schéma. Tests ciblés réalisés ; **validation navigateur R2.16 attendue**.

R2.16a ajoute aux vues Calendrier et Ressources les périodes 15 jours, Mois, 2 mois et Année. Une définition partagée fixe les vues FullCalendar, les bornes transmises à l'API et le pas de navigation ; chaque changement de période recharge uniquement sa fenêtre. Le correctif manuel des événements plugins Project reste inchangé. Tests frontend ciblés réalisés ; **validation navigateur des quatre périodes encore attendue**.

FullCalendar 7.1.0 fournit déjà la vue `timeline` via `@fullcalendar/react-scheduler/timeline` ; ce plugin est enregistré pour le calendrier Project sans nouvelle dépendance.

R2.16b affiche l'Employee des Leave dans les vues Project sans ressources et ouvre le Sheet Leave après une sélection de plage sur une ligne Resource autorisée, pour les quatre périodes. Les dates de fin exclusives FullCalendar sont converties en dates Leave inclusives. **Validation navigateur R2.16 encore attendue.**

R2.16c supprime les vues Employee historiques Mois/Année/cinq ans et le renderer React cinq ans. Employee et Project consomment désormais `projectCalendarScopes`, `projectDayGridViews` et FullCalendar pour les mêmes quatre périodes ; Employee conserve son Sheet, les capacités et les interactions Leave. L'ancien choix cinq ans mémorisé revient au Mois. Tests frontend ciblés réalisés ; **validation navigateur R2.16 encore attendue**.

R2.16d rend le nom d'un Project cliquable dans les participations de la fiche Employee lorsque la visibilité autonome Project le permet. L'API ajoute `project.can_view` à cette référence contextuelle sans changer les règles de permission ; une participation reste visible même si sa fiche Project ne l'est pas. **Validation navigateur R2.16 encore attendue.**

### R2.17 — Generic Notes

Project et Employee disposent du même panneau `GenericNotes` : onglets, création, renommage, visibilité, suppression confirmée et édition WYSIWYG avec autosave. L'API v1 générique borne les parents autorisés, filtre les notes privées et expose les capacités qu'elle contrôle aussi à l'écriture ; les anciennes routes Notes sont également filtrées pour éviter de révéler une note privée. `GenericNote.creator` est immuable ; `visibility` vaut `object` par défaut. La migration `infos.0016` attribue les notes historiques au compte administratif actif `ben_admin` et les laisse visibles aux lecteurs de l'objet ; ce compte doit exister avant application de la migration sur un autre environnement contenant déjà des notes. L'éditeur React réutilise l'asset `django_prose_editor` servi par Django, sans package npm supplémentaire. Team et Institution sont résolus dans l'API ; Team dispose d'un onglet React depuis R2.20. **R2.17 reste à valider au navigateur.**

### R2.18 — Generic Notes sur Contract

Contract est un parent de l'API Notes v1. La ligne `ContractSection` partagée Project/Employee affiche un accès Notes compact avec compteur des seules notes visibles, ou l'icône seule si la création est autorisée ; elle ouvre le même `GenericNotes` en Sheet. Le compteur est agrégé côté backend et la mutation suit `expense.change_contract`, avec les bypass administratifs Notes existants. La fermeture du Sheet sauvegarde le brouillon avant de rafraîchir le compteur. **R2.18 reste à valider au navigateur.**

### R2.19a — Filtres des listes Employee / Project

La liste Employee expose Actif, Nom, Supérieur, Statut historique, Statut actuel, Team et Project. L'API applique les filtres cumulés au périmètre visible, fournit les choix Statut/Team liés aux Employees visibles et utilise Participant pour Project. Le sélecteur Project réutilise `EntitySearch`. Les paramètres d'URL conservent filtres, tri et pagination, y compris lors du retour depuis une fiche ouverte depuis la liste. Les filtres Project existants restent inchangés ; « En retard » signifie actif avec fin au plus tard à l'horizon configuré (3 mois par défaut), y compris les fins déjà dépassées. **R2.19a reste à valider au navigateur.**

### R2.19b — Export des listes filtrées Employee / Project

Les listes Employee et Project proposent un téléchargement CSV, TSV, XLS ou XLSX (par défaut) depuis un Dialog commun. Chaque endpoint d'export hérite du pipeline de visibilité, filtres et tri de sa liste v1, puis transmet le queryset non paginé à `EmployeeResource` ou `ProjectResource`. Le format est validé explicitement et la réponse fournit un MIME et un nom de fichier daté adaptés. Pour Project, `ProjectResource` consomme les Funds visibles préchargés par l'API pour le texte et les six agrégats financiers ; l'export historique utilise également la règle `Fund.get_instances_for_user("view", …)`. Le mode complet de la Resource est explicite, sans endpoint utilisateur qui l'impose. `EmployeeResource` et la protection de `labResource` contre les formules restent inchangées. Certains widgets historiques hors Fund effectuent encore des requêtes par objet. **R2.19b attend la validation navigateur.**

### R2.20 — Team List et Team Detail

La liste Team applique visibilité, filtres cumulés nom/responsable/membre TeamMate, tri et pagination dans l'URL ; l'export CSV/TSV/XLS/XLSX réutilise exactement son queryset non paginé et `TeamResource`. La fiche Team propose Information (composition selon `staff.change_team`), Absences (leader et TeamMate via le producteur Leave et le calendrier partagé ; mutation seulement selon `staff.change_employee`), Projects (membres leader/co-leader, dédupliqués), Budget (intersection de visibilité Project/Fund/Budget, lecture seule) et le panneau `GenericNotes` existant. Les liens Employee ne s'ouvrent que si la fiche Employee est visible. Tests ciblés exécutés ; **R2.20 attend la validation navigateur**.

R2.20a ajoute la création Team selon `staff.add_team` et la portée historique du choix du responsable, avec un Sheet commun à l'édition du nom et du responsable. La section Information est disposée en deux colonnes adaptatives ; les TeamMate affichent dates et état actif calculé par le modèle, et se modifient dans un Sheet commun à l'ajout. Les droits de ligne sont fournis par l'API à partir de `staff.change_team`. **R2.20 reste non validé jusqu'au contrôle navigateur de R2.20a.**

### R2.21a — Favorites et Subscriptions

Les modèles génériques historiques restent la source commune du legacy, de l'API v1 et du mail. `common.0011` conserve le plus ancien enregistrement de chaque doublon éventuel, puis impose l'unicité utilisateur/type/objet ; aucun doublon n'a été trouvé sur la base de développement lors de l'inspection. Le service commun résout les cinq types autorisés, vérifie leur visibilité et assure les écritures idempotentes. L'API v1 expose état combiné et menu Favorites groupé, trié et filtré. Project, Employee et Team utilisent les mêmes actions étoile/cloche ; les Institutions restent liées aux fiches Django. Les routes HTML historiques restent disponibles et utilisent le service ; les anciens viewsets REST ne listent plus les relations cachées et sont limités à lecture/suppression. `SubscriptionMail` et les notifications sur abonnement filtrent les objets devenus invisibles ; les agrégats financiers mail utilisent les Funds visibles. Fréquence et contenu du rapport restent inchangés pour les objets visibles. **Migration à appliquer en développement avant validation navigateur ; R2.21a non validé fonctionnellement.**

### R2.22 — Liens directs Django Admin

Les objets métier déjà dotés d’un menu d’actions exposent `admin_url` depuis l’API v1. Le lien est calculé sur l’objet par le backend : superuser, ou staff avec `change_<model>` objet, et seulement si la route Django Admin existe. `ItemActionMenu`, `EntityActionMenu` et les menus spécifiques Employee/Project ouvrent l’Admin dans un nouvel onglet ; `TeamMate`, administré uniquement comme inline, conserve `admin_url=null`. Les Leave sont accessibles depuis leur Sheet et les événements Calendar portent ce lien dans leurs métadonnées. Le menu des GenericNotes utilise également l’action commune. **R2.22 attend la validation navigateur.**

### R2.23 — Contract Hub

`/app/tools/contracts` est l'entrée **Outils > Contrats**. La liste transversale reprend la visibilité canonique `Contract.get_instances_for_user("view", …)`, les neuf filtres cumulables du moteur commun, le tri et la pagination persistés dans l'URL. Active correspond strictement à `Contract.is_active` (suivi RH), Ongoing à `start_date <= today <= end_date` et Stale à `Contract.staleFilter()` ; les trois restent indépendants. Les options sont fournies par le backend à partir des Contracts visibles ou des choices du modèle.

La sélection charge `ContractDetail` et `ExpenseSection` existants ; Modifier réutilise le Sheet Contract seulement si `expense.change_contract` l'autorise dans ce contexte. Le Hub n'expose ni création ni suppression de Contract. L'export CSV/TSV/XLS/XLSX réutilise la liste visible, filtrée et ordonnée sans pagination, ainsi que `ContractResource` ; le total des dépenses est annoté pour éviter une requête par Contract. Le lien Admin reste fourni par `admin_url`. **R2.23 a été validé fonctionnellement avant le correctif Notes ci-dessous.**

**R2.23-fix-1 — parité de visibilité :** `Contract.get_instances_for_user("view", …)` reprend l'union des portées Contract déjà consultables depuis Employee (Employee visible) et Project (Project et Fund visibles, Employee participant). Cette même portée alimente liste, détail et export du Hub ; `expense.change_contract` reste indépendant pour Modifier.

**R2.23-fix-3 — Contract Notes :** les lignes du Hub réutilisent l'icône et le Sheet `GenericNotes` de R2.18. Le compteur des seules notes visibles est calculé en une requête groupée pour la page de Contracts ; `can_add` reprend la règle Notes existante. Une validation navigateur ciblée de cet accès direct reste attendue.

### R2.24a — Icônes Organisation/Contact vers Lucide

`InfoTypeClass.icon` est désormais un `CharField` texte ; la migration `infos.0017` modifie séparément les colonnes `icon` de `OrganizationInfosType` et `ContactInfoType`, puis convertit les valeurs Font Awesome observées vers les identifiants Lucide validés dans `lucide-react` 1.47.0. Elle préserve `NULL` et la chaîne vide et échoue sur toute valeur inconnue. Aucun nom de type ni autre donnée métier n'est modifié. **R2.24a a été appliqué en développement selon la confirmation utilisateur.**

### R2.24b — Organisations

Les listes Institution et Financeur et leurs fiches React partagent le même layout : Informations, Contacts, Projets, Contrats et Notes sont des sous-routes chargées à la demande. Les collections v1 bornent la lecture par `common.display_infos`; les mutations utilisent les permissions Django historiques propres à chaque modèle et les capacités sont renvoyées par l'API. Les résumés Project/Contract et leurs listes ne comptent que les Projects, Funds et Contracts visibles. Les montants disponibles Fund suivent la convention historique `amount + expense`, y compris focus ; Current dépend des dates et Active de `Contract.is_active` (suivi RH).

`OrganizationInfos` et `ContactInfo` conservent leurs modèles distincts et partagent `TypedInfoValue` pour la copie et les actions téléphone, mail, lien et adresse. L'adresse suit `MAP_PROVIDER` (`gmap` ou `opensm`) transmis par l'API depuis `LMUserSetting`. `GenericNotes`, Favorite/Subscription, les menus contextuels, les confirmations, les Sheets et les liens Admin existants sont réutilisés. Les favoris des deux types pointent désormais vers leurs fiches React. Une organisation référencée par un Fund ne peut pas être supprimée via l'API v1 afin d'éviter la cascade historique. R2.24b est validé fonctionnellement ; le correctif de layout Informations place identité et résumés côte à côte, puis les informations complémentaires sur toute la largeur. Les onglets Projets et Contrats réutilisent désormais les tables et projections canoniques Project et Contract Hub en lecture seule, sans élargir le scope Organisation. Ces présentations attendent un contrôle navigateur.

Contrôles ciblés : 17 tests backend Organisation/Notes/Favoris et 11 tests frontend Organisation/Favoris/icônes/liens typés réussis ; la suite Contract frontend concernée (15 tests) et les tests de chargement direct des routes réussissent également. TypeScript, ESLint ciblé, `manage.py check`, build Vite et `git diff --check` passent. Le build conserve son avertissement connu de taille de chunk.

### R2.25 — Financial Tools

Les routes Outils `/app/tools/fund-items`, `/app/tools/budgets` et `/app/tools/expenses` exposent des listes transversales en lecture seule, avec `FilterBar`, recherche de relations, tri/pagination persistés dans l’URL, détails en Sheet et export CSV/TSV/XLS/XLSX. Les lignes et exports partagent les mêmes querysets : Projects et Funds visibles pour Fund_Item/Budget/Expense, sans droit `change` requis. Les liens vers les fiches liées suivent leurs droits de consultation indépendants. Le compteur des Contracts RH est groupé sur les Contracts visibles du Fund ; son Sheet est également en consultation seule. Budget réutilise son détail informatif Project, Expense son rendu informatif partagé ; les Resources historiques restent celles des exports. Le premier contrôle navigateur Budget a révélé une réponse sans `contract_types` ; la liste et son Sheet tolèrent désormais cette absence, tandis qu'un test API vérifie que le backend actuel fournit toujours une liste pour ce champ. Aucune création, édition, suppression, migration ou dépendance ajoutée. **R2.25 est implémenté techniquement et attend la validation navigateur.**

### R2.26a — Organigramme interactif

`/app/tools/organization-chart` charge à la demande React Flow et ELK (`@xyflow/react` 12.12.0, `elkjs` 0.12.0). L'API v1 retourne un graphe plat, borné par `Employee.get_instances_for_user("view", user)` : un Employee n'apparaît qu'une fois, ses liens multi-supérieurs sont conservés, les relations vers des objets invisibles sont exclues et un cycle produit une erreur contrôlée. Les racines sont dérivées des liens visibles. Le réglage utilisateur historique `SHOW_PAST_ORG` est conservé : `true` signifie « organisation actuelle uniquement », `false` inclut l'historique. La page permet recherche, surlignage des chemins, repli, navigation vers Employee et déplacement/zoom. Le legacy reste utilisable pendant la validation ; l'impression statique est réalisée en R2.30. **Implémenté techniquement, validation navigateur attendue.**

**R2.26a-fix-1 :** les contrôles et liens des nœuds restent cliquables avec le pan/drag React Flow neutralisé sur ces éléments. La recherche distingue résultat, ancêtres et descendants visibles ; les Employees inactifs historiques sont grisés mais interactifs. ELK dispose les deux premiers niveaux, les niveaux profonds sont empilés par colonnes, et les Employees sans aucune relation du graphe métier sont regroupés en grille sous la hiérarchie. Repli et recherche conservent les chemins multi-supérieurs. **La validation navigateur de ces corrections reste attendue.**

### R2.27 — Import Hub

`/app/tools/import` propose les profils Expense, Employee et Expense Timepoint depuis un registre backend soumis à `common.import`, comme le workflow historique. Les templates vides viennent des Resources ; CSV/TSV/XLS/XLSX sont acceptés, avec choix de feuille Excel. Un fichier temporaire signé et expirant est réutilisé pour dry-run, téléchargement des lignes en erreur et confirmation. La page montre colonnes, compteurs, statuts, différences et messages métier ; le résultat final provient du second passage de la Resource. Les erreurs converties en lignes ignorées par `SkipErrorRessource` permettent historiquement l'import partiel des lignes valides, tandis qu'une erreur globale ou de validation bloque la confirmation. **Implémenté techniquement ; R2.27 attend la validation navigateur.**

L'état « Inchangé » suit le `skip` retourné par la Resource. Le test Expense montre qu'une réimportation de valeurs apparemment identiques est actuellement classée `update` par `ExpenseResource`/`SkipSameValueRessource` ; le Hub ne réécrit pas cette décision historique. Ce classement reste à vérifier avec un fichier représentatif pendant la validation navigateur.

**R2.27-fix-1 :** le profil Expense déclare les fields Resource à montrer dans la preview et le résultat final : identifiant, description, type, montant, Project, Ref, Funder, Institution et date. Les labels proviennent des `column_name` de la Resource ; les valeurs résolues réutilisent son diff, avec les valeurs brutes du fichier en repli, notamment en cas d'erreur. Employee et Expense Timepoint gardent le tableau générique. Validation navigateur encore attendue.

### R2.28 — Calendriers globaux

La navigation principale ouvre `/app/calendars` avec deux onglets : **Calendrier général** pour les absences des Employees visibles et **Calendrier des projets** pour le Planning/Gantt des Projects visibles. Le premier réutilise `CalendarService`, le producteur Leave, FullCalendar et ses quatre scopes ; le second réutilise le serializer Planning, `PlanningGanttAdapter`, `PlanningGanttView` et SVAR avec ses fenêtres 6/12/24/60/120 mois. Les contextes Calendar `MAIN` et `PROJECT_ALL` et les filtres plugins restent actifs selon leur domaine. Les filtres Employee, Leave Type, Project et Milestone Status sont cumulables côté backend ; les périodes, onglets et filtres sont conservés dans l'URL. Les deux onglets sont en consultation seule. Quatre tests backend et 35 tests frontend ciblés passent, ainsi que TypeScript, ESLint ciblé, contrôle Django, build Vite et `git diff --check`. Aucun nouveau moteur, migration ou dépendance. **R2.28 est implémenté techniquement ; validation navigateur attendue.**

**R2.28-fix-1 :** une ligne Project globale sans tâche rendue reste fermée dans l'adaptateur SVAR, qui attend sinon une collection d'enfants alors nulle. La page globale transmet désormais directement la query sérialisée au loader ; la clé JSON interne n'est plus ajoutée à la dernière valeur du filtre plugin. Le test API retourne « Vacances de Noël » en Zone B sur décembre 2026–janvier 2027 avec `display="background"`, aux côtés des jours fériés. Cinq tests API et 14 tests frontend ciblés passent. **Contrôle navigateur du Gantt et du fond des vacances encore requis ; R2.28 partiellement validé.**

### R2.29a — Settings Hub et paramètres utilisateur

Le menu utilisateur ouvre le Settings Hub React, hors navigation métier. `/app/settings` redirige vers `/app/settings/user` ; les sous-routes Interface, Notifications, Favoris et abonnements, et Alertes d’échéance gardent leur état au rechargement. La fiche utilisateur propose profil, changement de mot de passe et gestion des e-mails par des formulaires React reliés aux formulaires et flows django-allauth. Les réglages Interface encore utiles, les 16 préférences de notification utilisateur et les deux horizons Stale Project/Contract restent des `LMUserSetting` personnels ; l’API expose type, valeur, défaut, choix et validation du modèle. Les favoris/abonnements réutilisent le service R2.21 et sa visibilité ; la liste des abonnements a maintenant une route v1. Les paramètres exclusivement liés à l’ancienne interface (STICKY_NAVBAR, PRINT_FULL_BOXES) et les boutons de mail de test ne sont pas portés ; `LAB_THEME` rejoint Interface en R3.14. Le Dashboard Settings, les listes, l’administration et les plugins restent hors de R2.29a ; le legacy est conservé. **R2.29a validé au navigateur par l’utilisateur.**

**R2.29a-fix-1 :** les panneaux Settings utilisent des titres, espacements et séparateurs légers. Le mot de passe s'édite dans la Sheet commune ; les e-mails exposent deux états distincts, Primary/Secondary et Verified/Unverified, avec actions contextuelles selon les capacités allauth. L'API refuse toujours la suppression d'un e-mail Primary. Interface, Notifications et Stale sauvegardent chaque réglage au changement (entiers au blur), avec états Saving/Saved/Error discrets. Favoris et abonnements sont côte à côte sur desktop et empilés sur écran étroit. **R2.29a validé au navigateur par l’utilisateur.**

### R2.29b — Listes mutables LabsManager

Le Settings Hub ajoute six sous-routes Fund, Contract, Leaves, Project, Staff et Organization. Un registre backend explicite décrit neuf listes actives, leurs colonnes, formulaires historiques, ordre et capacités ; `Fund_Institution` et `Institution`, commentées dans les panneaux legacy, ne sont pas reprises. L'API générique fournit metadata, lecture, création, modification et suppression conditionnelle. Les permissions globales propres à chaque modèle contrôlent les écritures ; comme dans les panneaux historiques actifs, aucune des neuf listes n'autorise Delete. Contract Type reste créable mais sans champ modifiable après création, conformément à son ModelForm. Le même composant React rend toutes les listes sans branche métier. Un bloc Organisations dupliqué dans la navigation a été retiré pour éviter deux liens identiques et une référence non résolue ; l'import de styles du nouveau `SidebarGroup` a été rétabli. Six tests API et les tests React ciblés passent. **R2.29a et R2.29b validés fonctionnellement par l’utilisateur.**

**R2.29b-fix-1 :** Cost Type et Leave Type sont les deux seules listes MPTT du registre. Leur colonne `name` déclare le renderer `tree` ; l'API fournit `tree_level` directement depuis `level` et conserve l'ordre `(tree_id, lft)`. Le rendu React indente les descendants et masque le préfixe décoratif aux lecteurs d'écran, sans modifier la valeur métier ni le formulaire parent. GenericInfoType Employee/Project restent des listes ordinaires. **R2.29b validé fonctionnellement par l’utilisateur.**

### R2.29c — Administration générale Settings

La navigation Administration du Settings Hub et les endpoints v1 associés sont réservés à `is_staff`. General expose les cinq réglages globaux actifs : `MAIL_OBJECT_PREFIX`, `EMPLOYEE_CAN_EDIT_SUBORDINATE`, `CO_LEADER_CAN_EDIT_PROJECT`, `AUDIT_LOG_RETENTION` et `NEW_EMPLOYEE_CASSE`, avec autosave et validation du modèle. Users permet de lier, changer ou délier l'Employee d'un User via la relation `OneToOneField` existante ; Notifications réutilise les contrôles et l'envoi synchrones historiques. Plugins expose les quatre interrupteurs globaux actifs, les plugins chargés, leur reload et les erreurs ; le détail est piloté par les mixins enregistrés `settings`, `schedule`, `urls`. Le hook HTML legacy `settings_content` n'est pas migré car aucune implémentation active n'a été trouvée. Dashboard et Audit Log restent hors périmètre, et le legacy est conservé. **Implémenté techniquement ; validation navigateur R2.29c attendue.**

**R2.29c-fix-1 :** Administration > Users conserve la table User–Employee et ajoute une section Invitations fondée directement sur `django-invitations`. Les six colonnes historiques, l'envoi via le formulaire et `send_invitation(request)` du package, et l'action globale `delete_expired_confirmations()` sont exposés par des endpoints v1 réservés à `is_staff`. La suppression historique considère aussi les invitations acceptées comme confirmations expirées ; le dialogue le précise. Aucun token ni workflow d'acceptation n'est géré dans React. **R2.29c reste en attente de validation navigateur.**

### R2.30 — Impression centralisée extensible

Les vues Calendar Employee, Project, Team et globale, les Gantt Employee, Project et global, ainsi que l'organigramme ouvrent un aperçu commun via Imprimer. Le registre frontend contient les renderers Calendar, Gantt et Organigramme ; il est extensible par enregistrement de renderers frontend supplémentaires. L'aperçu conserve la vue source montée, reçoit les données et l'état courants, attend le calcul ELK si nécessaire et n'imprime pas le DOM interactif de l'écran. Calendar réinstancie FullCalendar en mode print ; Gantt et Organigramme utilisent des renderers statiques. Formats par défaut : A4 paysage pour Calendar, A3 paysage pour Gantt et Organigramme. **R2.30 validé fonctionnellement par l'utilisateur avant fix-3.**

**R2.30-fix-1 :** étape intermédiaire ayant ajouté une timeline Calendar statique, ensuite remplacée par le renderer partagé en fix-2. Le Gantt statique conserve ses deux niveaux de dates et leurs séparateurs alignés sur les barres, avec les échelles SVAR 6/12/24/60/120 mois partagées.

**R2.30-fix-2 :** le renderer Calendar statique séparé est remplacé par `SharedCalendar` en mode print : les huit définitions FullCalendar sont identiques pour Project, Team, Employee, Global et Print. Global propose aussi les quatre vues Resources, alimentées par tous les Employees visibles après filtres, même sans Leave dans la fenêtre. Les filtres et événements plugins continuent dans les deux modes ; les couleurs Gantt écran/print sont partagées. **Validé fonctionnellement par l'utilisateur.**

**R2.30-fix-3 :** filtre Resources commun à `SharedCalendar` et Print : événements sur la période par défaut, toutes les ressources déjà visibles, ou événement aujourd'hui. Les associations d'événements explicites seules activent une ligne ; un fond global ne l'active pas. Le mode aujourd'hui charge le jour local via les endpoints Calendar existants avec les mêmes filtres, même si la vue affiche une autre année. **Validation navigateur de ce dernier filtre attendue.**

### R3.1 — Dashboard Foundation

**R3.1 validé fonctionnellement par l’utilisateur.** `/app/dashboard` propose l'onboarding explicite Employee/Leader/Lab manager/Blank et plusieurs tableaux personnels, avec sélection, renommage, ordre, duplication, default et suppression confirmée. Les templates créent de vraies instances indépendantes. Le catalogue pilote comporte Liens rapides, Note et nombre de Projects visibles ; aucun chiffre métier fictif. La grille React Grid Layout 2.2.4 permet déplacement/redimensionnement en mode personnalisation, sauvegarde batch et empilement mobile par ordre logique. Une définition absente reste affichable et supprimable sans casser le tableau. L'API v1 borne tous les accès au propriétaire et valide scope, config, multiples et tailles. Le contrat `DashboardPluginMixin` rejoint le registre plugin existant ; print, présentation et dashboards Project/Employee restent futurs. Les routes Django legacy Dashboard sont conservées.

La migration `dashboard.0001_initial` crée les deux modèles et la contrainte de default. Elle est appliquée à la base de développement et à la base de test ; elle reste à appliquer lors d’un futur déploiement. Sept tests backend Dashboard, neuf tests frontend Dashboard et les 35 tests du routeur passent. TypeScript, ESLint ciblé, contrôle Django et build Vite passent.

### R3.2 — Dashboard Core Renderers, catalogue et configuration

**R3.2 validé fonctionnellement par l’utilisateur.** Le catalogue filtre les DataSources disponibles par contexte et permissions, les regroupe par catégorie, permet une recherche et ouvre une Sheet de configuration avant l’ajout. Une instance persiste `source_key`, `renderer_key`, configuration, titre et layout. `core.projects` se décline en KPI ou liste compacte, avec `active_only` et `limit`, à partir des seuls Projects visibles ; Liens rapides et Note restent compatibles. Une même source peut être ajoutée plusieurs fois si elle l’autorise. Le menu `…` ouvre Configure ou une suppression confirmée ; changer de renderer conserve l’identité de l’instance. Les renderers KPI, liste compacte, alertes et progression utilisent des payloads normalisés et une variante de taille commune. Les sources plugins peuvent utiliser ces renderers core sans composant frontend spécifique. Duplicate Widget, print et présentation restent différés.

La migration `dashboard.0002_widget_source` ajoute et renseigne `source_key` pour les trois pilotes R3.1 ; elle est appliquée sur la base de développement et de test, et reste à appliquer lors d’un futur déploiement. Aucune dépendance ajoutée. Neuf tests backend et seize tests frontend ciblés, TypeScript, ESLint ciblé et `git diff --check` passent.

### R3.3 — Dashboard Business Sources et templates utiles

**R3.3 validé fonctionnellement par l’utilisateur.** Sept sources métier utilisent le pipeline R3.2 : `core.projects`, `core.milestones`, `core.funds`, `core.contracts`, `core.employees`, `core.leaves` et `core.tasks`. Les tâches sont les `Milestones` avec `start_date`, conformément au modèle existant. Chaque provider part du périmètre de visibilité canonique et applique ses filtres déclaratifs ; les listes sont bornées et les renderers restent les quatre renderers core. Les Fonds utilisent la convention historique `available = amount + expense` avec dépense signée. Les catégories, champs de configuration, choix et descriptions sont traduits FR/EN dans React ; les noms métier restent issus de la base.

Les templates Employee (5 widgets), Leader (7) et Lab Manager (7) assemblent ces sources avec des configurations concrètes ; Blank reste vide. Les templates sont copiés à la création et n'altèrent aucun dashboard déjà créé. Liens rapides et Note restent disponibles dans le catalogue. Aucune migration ni dépendance nouvelle. Quatorze tests backend Dashboard et dix-sept tests frontend Dashboard ciblés, TypeScript, ESLint ciblé, contrôle Django et `git diff --check` passent.

### R3.4 — Dashboard Print et présentation

**Validé fonctionnellement par l’utilisateur.** Le Dashboard propose une route de présentation authentifiée sans Sidebar/Topbar, avec le même détail propriétaire, la même grille en lecture seule et un retour au tableau sélectionné. L’impression réutilise `PrintRegistry`/`PrintShell` et capture les WidgetInstances, configs, données et définitions déjà chargées. Le rendu A4 paysage suit `logical_order` sur une ou deux colonnes, omet les widgets `printable=false` et garde un placeholder pour les définitions absentes. Les quatre renderers core et le cadre widget sont partagés ; un renderer local peut fournir un `printComponent` optionnel. Aucune migration, dépendance ou API nouvelle. Cinquante-six tests frontend ciblés, TypeScript, ESLint ciblé, build Vite et contrôle des espaces passent.

### R3.5 — Synthetic Demo Dataset v1

Le backend fournit `generate_demo_data` pour peupler une base de démonstration dédiée avec un laboratoire fictif déterministe autour de T0 : comptes/groupes, Employees/Teams, Projects/participations/planning, Fund Items/Budgets/Expenses, Contracts, Leaves et dashboards personnels Employee/Leader/Lab Manager. Le générateur réutilise les modèles, signaux, fixtures de droits et templates Dashboard existants. `--reset` purge les données opérationnelles dans une transaction et refuse un environnement non DEBUG hors base de test ; sans `--reset`, la présence de données opérationnelles provoque un refus clair. Paramètres, scénarios et identifiants figurent dans `docs/demo-data/DATASET.md`. Trois tests ciblés, le contrôle Django et les contrôles d'espaces passent. Aucune migration, dépendance ou modification frontend pour R3.5. **R3.5 validé fonctionnellement par l’utilisateur sur la base demo dédiée.**

### R3.6 — Project Dashboard et analytics financières

**Implémenté techniquement ; validation navigateur attendue.** L’onglet Dashboard Project réutilise `DashboardPage`, la grille, l’éditeur, l’impression et la présentation existants. Chaque utilisateur dispose d’un Dashboard propre par Project visible, initialisé avec neuf widgets sans modifier ses dashboards personnels. Les mêmes DataSources Project, Milestones, Tasks, Funds, Contracts et Employees acceptent le scope Project ; le catalogue et les mutations vérifient les droits backend. Le contexte `DashboardContext` fournit l’objet Project aux sources plugins déclarant ce scope. La migration historique `dashboard.0003_project_dashboard` a ajouté la relation Project ; elle est appliquée selon la confirmation utilisateur et est corrigée sans réécriture par R3.6a.

`core.expense-trend` lit l’historique `AmountHistory` de `Expense_point` avec `value_date` prioritaire sur `created_at`, en séries mensuelles cumulées ou par période et groupées par total, Fund, Cost Type ou Institution. Il ne charge que les Funds visibles ; une trajectoire linéaire est disponible pour un seul Project. `core.financial-advancement` compare consommation et part de durée écoulée, avec le repère 1 au centre ; le rendu générique `line-chart` est disponible pour le core et les plugins, sans nouvelle dépendance. Le générateur demo crée maintenant des échéances Expense successives par les signaux métier pour alimenter la courbe. Le menu utilisateur affiche Admin uniquement selon la capability `/me/` du backend.

Contrôles ciblés R3.6 : 23 tests backend Dashboard et le test d’intégration du dataset demo, 34 tests Project, 38 tests routeur, 21 tests Dashboard ciblés et 8 tests i18n/renderers réussis. TypeScript, ESLint ciblé, contrôle Django, cohérence des migrations, build Vite et `git diff --check` passent. La validation visuelle des dashboards et des courbes reste à faire.

### R3.6a — Contexte Dashboard générique

**Implémenté techniquement ; migration et validation navigateur attendues.** `Dashboard.owner` reste le propriétaire. Le contexte métier est désormais `context_content_type` + `context_object_id` + `context_object` ; les deux champs nuls désignent un Dashboard personnel. `dashboard.0004_generic_dashboard_context` copie les liens Project de `0003` vers ce contexte, remplace l’unicité owner/Project par owner/contexte, puis supprime la colonne Project. Elle conserve identifiants, widgets, configurations et layouts ; son retour arrière restaure les liens Project et refuse les autres types de contexte pour éviter une perte silencieuse. Le runtime ne résout actuellement que user et Project, avec visibilité Project inchangée ; l’identité générique pourra stocker Employee, Team ou Fund sans colonne supplémentaire. La suppression d’un Project supprime ses Dashboards par signal, comme l’ancienne FK. Le contrat API et le frontend restent inchangés, ainsi que les sources plugins utilisant `DashboardContext`. `0003` n’a pas été modifiée.

Contrôles R3.6a : 25 tests backend Dashboard, dont migration aller/retour, accès Project, contexte plugin et cascade Project, réussis ; `makemigrations --check`, `manage.py check` et `git diff --check` réussis. Aucun build frontend nécessaire : aucun fichier frontend modifié. `0004` n’a pas été appliquée à la base de développement dans cette passe.

### R3.7 — FrenchHollidayPlugin, exemple Dashboard plugin

**Validé fonctionnellement par l’utilisateur.** Le plugin actif déclare `frenchholliday.upcoming-holidays` pour les contextes personnel et Project via `DashboardPluginMixin`. Une source lit les données locales de calendrier et le setting de zone existant ; elle propose KPI et liste compacte, avec horizon et nombre maximal d'éléments bornés par l'API. Elle n'écrit rien et ne déclenche pas `FHP_pull()` pendant le rendu. Le registre actif retire la source quand le plugin est désactivé ; une instance historique garde le placeholder standard et reste supprimable. Aucun renderer React spécifique, changement du cœur Dashboard, migration ou dépendance. Voir [l'exemple développeur](DASHBOARD_PLUGIN_EXAMPLE.md). Vérifier que la migration R3.6a `dashboard.0004` est appliquée avant le contrôle navigateur du Dashboard Project.

Contrôles R3.7 : huit tests backend ciblés et vingt et un tests frontend génériques Dashboard réussis ; contrôle Django, compilation du catalogue gettext français et `git diff --check` ciblé réussis. Un test Calendar existant a été ajusté à la prise en charge Project déjà effective, sans modifier le comportement du plugin.

### R3.7a — Lien Admin du menu utilisateur

Le menu utilisateur résout désormais `admin_url` fourni par `/api/v1/me/` avec `getDjangoUrl()`, comme les deep-links Admin existants. La capability `can_access_admin` et le contrat backend restent inchangés. Le lien utilise ainsi l’origine Django configurée lorsque Vite tourne sur un port distinct ; sans `admin_url`, aucune action Admin n’est affichée. Correctif frontend ciblé ; validation du clic au navigateur attendue.

### R3.8 — Fondation Global Search

**Infrastructure backend implémentée ; validation API manuelle attendue.** Le registre unique agrège les providers Employee/Project et les contributions des plugins actifs. `SearchProvider` déclare champs, queryset visible et destination ; `SearchEngine` applique la recherche libre multi-termes, classe exact > préfixe > contient, fusionne et borne les résultats `SearchResult` avec raison du match. `SearchQuery` réserve filtres structurés et AST sans parser avancé. `/api/v1/search/` accepte `q`, `provider`, `limit` et `per_provider` ; `/api/v1/search/schema/` décrit les providers actifs. Aucune migration ou dépendance ajoutée. GenericInfo, Funds, Contracts, Teams et le langage avancé restent aux lots ultérieurs.

Neuf tests backend ciblés couvrent contrats, registre et collision, plugin actif/désactivé, fusion/score (y compris au-delà de la fenêtre de candidats), permissions Employee/Project, schéma, API et erreurs ; `manage.py check` et `git diff --check` ciblé passent. Aucun test frontend nécessaire, le frontend n'ayant pas été modifié.

### R3.9 — Global Search UI

**Interface implémentée ; validation navigateur attendue.** La Topbar propose une icône discrète, un champ activé au clic ou avec `/`, un aperçu groupé par provider après temporisation, et la navigation clavier. La route `/app/search` conserve `q` et `provider` dans l'URL, charge davantage de résultats et déduit ses onglets du schéma actif. Client API et hook partagés annulent les recherches dépassées ; le frontend suit `SearchResult.url` et ne connaît aucun provider métier en dur. Les permissions restent celles des providers backend R3.8. Les providers supplémentaires, GenericInfo et la grammaire avancée restent à venir. Aucun backend, migration ou dépendance ajouté dans R3.9.

Contrôles R3.9 : 11 tests ciblés Search/API/i18n et 40 tests du routeur réussis, TypeScript, ESLint ciblé, build Vite et `git diff --check` ciblé réussis. La validation de l'UX, des URLs et des différences de visibilité entre comptes reste à réaliser au navigateur.

### R3.10 — Providers métier Global Search

**Validé fonctionnellement.** Employee recherche nom, email, statut actuel et GenericInfo ; Project recherche nom, leaders/co-leaders, tous les participants, institutions et GenericInfo. Fund recherche `ref`, financeur et gestionnaire, sans propagation depuis le nom Project. Contract recherche Employee, email lorsque cet Employee est visible, type et statut dans le périmètre du Hub ; Team recherche nom, leader et membres dans le périmètre `visible_teams`. Les GenericInfo des parents visibles sont incluses automatiquement, sans flag sur leurs types. Le moteur combine les termes entre axes, pondère les champs et déduplique ; l'API ajoute `counts` exacts aux `groups` déjà existants. La page Search affiche ces comptes dans les onglets lorsqu'ils sont disponibles. La destination Fund vise sa ligne Project Funding ; Contract vise le Hub filtré par Employee. Parser avancé, autocomplétion syntaxique et nouveaux types métier restent différés. Aucune migration ni dépendance.

Contrôles R3.10 : 19 tests backend et 27 tests frontend ciblés réussis ; contrôle Django, TypeScript, ESLint ciblé et `git diff --check` ciblé réussis. Validation fonctionnelle confirmée par l'utilisateur avant R3.11.

### R3.11 — Langage avancé Global Search

**Validé fonctionnellement.** Tokenizer positionnel, parser récursif et AST interne pour phrases quotées, providers/champs dynamiques, AND/OR/NOT, parenthèses et `info:"TYPE"="value"`. L'engine applique les conditions ORM aux querysets visibles avant comptes et scores ; la recherche libre R3.10 reste dans son chemin historique. L'API renvoie une erreur 400 structurée pour syntaxe/clé invalide et l'interface l'affiche dans l'aperçu et la page. L'autocomplétion arrive en R3.12 ; aucune migration ni dépendance.

Contrôles R3.11 : 24 tests backend Global Search et 11 tests frontend Search ciblés réussis ; TypeScript, ESLint ciblé, contrôle Django et `git diff --check` ciblé réussis. Validation fonctionnelle confirmée par l'utilisateur avant R3.12.

### R3.12 — Autocomplétion Global Search

**Implémentée techniquement ; validation navigateur attendue.** L'API contextuelle utilise les positions du tokenizer R3.11, tolère les requêtes partielles et retourne la plage à remplacer. Les clés de providers/champs viennent du registre actif, les types GenericInfo des catalogues autorisés, et les valeurs dynamiques des seuls objets visibles. Le même champ React sert Topbar et page Search avec navigation clavier, insertion au curseur, annulation des requêtes dépassées et priorité des suggestions sur l'aperçu. Les valeurs GenericInfo, la recherche floue et les opérateurs supplémentaires restent hors périmètre. Aucune migration ni dépendance.

Contrôles R3.12 : 31 tests backend Global Search et 17 tests frontend Search/API ciblés réussis ; TypeScript, ESLint ciblé, contrôle Django et `git diff --check` ciblé réussis. Validation navigateur encore attendue.

### R3.13 — Home et destinations récentes

**Implémenté techniquement ; validation navigateur attendue.** La migration `common.0012_recentitem` est appliquée en développement et reste à appliquer lors d'un futur déploiement. `/app` affiche le Dashboard personnel par défaut, les autres tableaux, six destinations récemment ouvertes et des accès rapides ; aucun widget, favori ou annonce. Le frontend suit explicitement Project, Employee, Team, Organisation, Fund/Budget sélectionnés, Contract consulté, Calendar et les trois outils financiers. Search, Settings et Dashboard ne sont pas suivis. L'API `/api/v1/recent-items/` valide et revalide les droits, reconstruit les liens métier depuis les helpers partagés avec Global Search et ignore les entrées devenues invisibles ou supprimées. Aucun ContentType, GFK ou nouvelle dépendance.

Contrôles R3.13 : 16 tests backend Recent/Search et 73 tests frontend Home/hook/routeur/Funding/Budgets réussis ; TypeScript, ESLint ciblé, contrôle Django, cohérence des migrations, build Vite et `git diff --check` réussis. La migration est aussi appliquée à la base de test par `--keepdb`.

### R3.14 — Auth React final et thème utilisateur persistant

**Implémenté techniquement ; validation navigateur attendue.** Login ouvre maintenant les pages React de demande et de définition du nouveau mot de passe. L'API réutilise les formulaires, jetons, contrôles de mot de passe et notifications django-allauth ; un pont Django valide le lien d'e-mail et redirige vers React avec le jeton conservé en session, absent de l'URL finale. Le résultat de la demande ne révèle pas si l'adresse existe. Les exigences de mot de passe viennent des validateurs Django. Les anciens templates restent disponibles comme repli.

`LAB_THEME` n'accepte plus que `light`/`dark`, avec défaut `light`. `/me/` amorce le thème de l'utilisateur après connexion ou rechargement ; le menu et Settings > Interface utilisent la même API et reviennent à la valeur antérieure si l'écriture du menu échoue. Aucun choix de thème n'est stocké dans `localStorage` ; les pages anonymes sont claires. La migration de données `settings.0009_reset_lab_theme` supprime uniquement les anciennes lignes `LAB_THEME` ; elle est appliquée en développement et reste à appliquer lors d'un futur déploiement. `REACT_PUBLIC_URL` est la base publique canonique de React (`/app` inclus) pour les liens envoyés par e-mail. R3.14b : le lien e-mail ouvre React, qui échange le jeton par `/api` ; le pont Django répond en JSON et React navigue vers le formulaire sans jeton. La configuration de développement fixe `REACT_PUBLIC_URL` à `http://192.168.1.145:5173/app` ; sans configuration, aucune demande de reset n’envoie de lien. La validation d’un vrai courriel en navigateur reste attendue. Aucune migration de schéma ni dépendance nouvelle.

Contrôles R3.14 : 22 tests backend et 45 tests frontend auth/routeur ciblés réussis ; TypeScript, ESLint ciblé, contrôle Django, build Vite et `git diff --check` réussis. La validation navigateur du courriel réel, du lien de retour vers React et de la persistance entre sessions reste à faire.


### R4.1 — Build Docker et pipeline static React

**Implémenté techniquement ; le routage nginx `/app/` reste pour R4.2.** L’image utilise une étape Node 24.11.1 avec `npm ci` et `npm run build`, puis copie `dist/` dans `backend/data/static/frontend/` de l’image Python. `init.sh` exécute `collectstatic --noinput` au démarrage du serveur sans `--clear` ; le worker partage l’image mais saute cette collecte. Le volume static persistant conserve les fichiers legacy. Vite produit des URL `/static/frontend/` au build et conserve `/app/` en développement. Aucun service, WhiteNoise ni Node runtime supplémentaire.

Contrôles R4.1 : build Vite local, étape Node Docker et image finale réussis ; l’image finale contient React et n’a ni Node ni npm. `collectstatic` testé deux fois avec une source React identique à celle copiée dans l’image : index/assets, admin et legacy présents, nouvel asset mis à jour et ancien fichier préservé. `manage.py check`, syntaxe `init.sh`, configuration Compose et `git diff --check` réussis. La navigation `/app/` via nginx reste à valider en R4.2.

### R4.2 — nginx React principal et port legacy temporaire

Le port `LAB_WEB_PORT` sert `/app/*` directement depuis l'index React publié dans `STATIC_ROOT/frontend/`, `/static/*` depuis le volume partagé, et transmet le reste à Django, notamment API, admin, comptes et routes legacy. `/` redirige vers `/app/`. Le port configurable `LAB_LEGACY_WEB_PORT` (défaut 1338) transmet toutes les pages à ce même Django, tout en servant les mêmes static. Aucun service, backend, volume ou accès direct `/media/` supplémentaire. La validation du déploiement complet et le hardening restent pour R4.3.

Contrôles ciblés Docker : `/app/` et les deep links renvoient l'index React, les assets React et admin sont servis sur les deux ports, API et admin atteignent Django, une route API inexistante conserve sa 404 et `/app/...` sur le port legacy reste une route Django. `nginx -t`, Compose et le contrôle Django réussissent. La configuration locale force HTTPS : les réponses backend ont été vérifiées avec cette redirection suspendue temporairement, puis le réglage initial a été restauré. L'accès HTTP direct aux pages Django exige un réglage de transport adapté ou une terminaison TLS ; R4.3 couvrira la validation du déploiement cible.

### R4.3 — Préparation production, migrations et transport

Les migrations restent une étape explicite avant le démarrage : `init.sh` refuse serveur et worker si le schéma n'est pas à jour, puis le serveur seul publie les static. Les healthchecks ordonnent DB, Gunicorn, worker/proxy. Le premier `migrate` sans `--skip-checks` sur PostgreSQL vierge réussit après suppression de la lecture prématurée du réglage des URLs plugin. Une copie sauvegardée de la base de développement (33 Employee, 20 Project, 14 Fund, 104 Expense, 14 Contract, 12 Leave et 3 Dashboard) a été ramenée à quatre migrations React en attente (`common.0012`, `dashboard.0003/0004`, `settings.0009`) : leur application réussit, les comptes métier restent identiques et une seconde migration est sans effet. Cette simulation n'est pas encore une répétition sur un dump historique de production.

Les ports HTTP directs fixent `X-Forwarded-Proto=http`. Deux listeners nginx distincts (React et legacy), uniquement publiés sur loopback pour un proxy HTTPS externe de confiance, fixent `https` ; Django ne fait confiance à ce header que si le réglage explicite `LAB_TRUST_PROXY_SSL_HEADER` est activé. Gunicorn n'est plus publié sur toutes les interfaces. Le template de configuration reste un profil de développement HTTP ; les clés de démonstration sont refusées lorsque `DEBUG=false`. Les réglages numériques typés rejettent les valeurs invalides et ignorent une variable d'environnement vide. `check --deploy` passe sans avertissement sous un profil HTTPS de test avec clé forte. Sur la copie migrée, l'image Docker sert React, API et legacy ; login/logout, session et CSRF ont été vérifiés. Les deux plugins activés (FrenchHoliday et KioskDashboard externe) ont été collectés ; le démarrage avec plugins désactivés ou sans dossier externe a aussi réussi. Le worker a néanmoins rencontré une ancienne tâche Django-Q de la copie en échec (`NoneType is not callable`), à examiner avant production. Le transport HTTPS a été simulé sur les listeners de confiance, sans véritable terminateur TLS public. La procédure détaillée de sauvegarde, migration, validation et restauration figure dans `COMMANDES.md`. **R4.3 reste à valider sur l'environnement réel de production et son ancien dump.**
