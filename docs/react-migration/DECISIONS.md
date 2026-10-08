# Decisions durables

- Django reste le backend et porte la logique metier.
- `backend/` est le sous-module Django canonique du depot de distribution ; il pointe vers `git@github.com:Bbillyben/labsmanager.git` et suit la branche `dev`.
- `frontend/` et `docs/react-migration/` sont versionnes directement dans le depot racine de distribution.
- PostgreSQL et les donnees existantes sont conserves.
- La migration est progressive, par lots fonctionnels ; aucun Big Bang.
- L'interface Django existante reste fonctionnelle pendant la transition.
- Le nouveau frontend sera React + TypeScript. Le scaffold JSX actuel n'est pas une contrainte de compatibilite.
- Les nouvelles API stables sont versionnees sous `/api/v1/`. Les routes `/api/` actuelles restent compatibles pendant la transition.
- Les apps Django ne sont pas renommees ou reorganisees sans necessite demontree, afin de proteger migrations, ContentTypes et permissions.
- Le backend controle toutes les permissions ; le frontend adapte seulement la presentation.
- L'authentification Django par session et cookie CSRF est privilegiee. Aucun JWT n'est introduit sans besoin explicite. Token et Basic existants seront audites, pas etendus par defaut.
- Aucune migration BDD sans benefice metier ou technique concret.
- Aucun refactoring global preventif ; les abstractions sont creees lorsqu'un lot les justifie.
- Toute dependance Python est epinglee et ajoutee au `requirements.txt` racine installe par Docker, avec mise a jour coherente de `requirements.in`, dans le meme changement que son usage.
- Toute dependance npm met a jour `frontend/package.json` et `frontend/package-lock.json` dans le meme changement.
- Toute action manuelle est documentee chronologiquement dans `COMMANDES.md`, en distinguant bare-metal et Docker.
- Les routes Django historiques sont conservees et `/app/` est reserve au shell React.
- Le build React de production ne sera integre a Nginx/Docker qu'apres validation du shell.
- Le routeur React utilise `/app` comme basename. Les navigations internes utilisent React Router ; les transitions vers l'interface historique et les workflows de compte non migres restent des liens HTML construits depuis l'origine Django publique.
- Le client React appelle l'API avec des URLs relatives, la session Django et le cookie CSRF. Un `401` invalide centralement la session frontend, tandis qu'un `403` conserve sa signification d'interdiction sans deconnexion implicite.
- React porte la page de connexion et la deconnexion via `/api/v1/auth/login/` et `/api/v1/auth/logout/`. Ces POST exigent CSRF et reutilisent django-allauth pour l'authentification par identifiant/email, les backends, la session et les limites de tentatives ; aucune logique de mot de passe ou de compte n'est dupliquee dans React.
- L'inscription et l'invitation restent des workflows Django/allauth. Le changement de mot de passe et les e-mails du compte utilisent Settings React ; la réinitialisation R3.14 utilise React avec jetons, formulaires et validations allauth côté backend.
- En developpement separe, Vite proxifie uniquement `/api`; `VITE_DJANGO_PUBLIC_URL` fournit l'origine des liens HTML vers Django.
- Le socle frontend est teste avec Vitest, jsdom et React Testing Library. Aucun gestionnaire d'etat, cache de requetes, client HTTP tiers ou bibliotheque UI n'est introduit dans R0.
- Un lot UX/UI precedera toute interface metier React significative ; le shell R0 reste volontairement minimal.
- Le shell cible utilise une sidebar principale retractable, une topbar legere et une zone de contenu semantique. La navigation responsive reste une adaptation du meme shell, pas une architecture mobile distincte.
- La strategie de style combine tokens et reset globaux avec CSS Modules par composant. Le theme clair est livre en premier, mais les couleurs semantiques permettent un futur theme sombre sans reecriture des composants.
- `lucide-react` est la bibliotheque d'icones du frontend React. Les imports sont individuels ; une icone seule exige un nom accessible et les actions importantes conservent un texte visible.
- UX1 limite les primitives a `Button`, `IconButton`, `PageHeader`, `StatusBadge`, `Alert`, `LoadingState` et `EmptyState`. Tables, filtres, pagination, formulaires et composants complexes sont differes jusqu'a un besoin metier concret.
- Les futures actions sur objets ne seront pas necessairement repetees dans une colonne historique. Le pattern selection de ligne et barre d'actions contextuelle sera compare aux actions directes et menus par ligne dans Employee R1 ; il n'est pas impose.
- Selectionner une ligne et ouvrir une fiche sont deux interactions distinctes. Un lien explicite vers la ressource doit pouvoir coexister avec une selection destinee aux actions.
- React ne deduit pas une autorisation objet depuis une capacite globale. Avant d'exposer des actions Employee, les permissions et regles objet seront auditees et le contrat backend sera complete si necessaire.
- Un acces contextuel vers l'objet Django Admin pourra etre conserve pour les utilisateurs autorises, sans generer de liens Admin generiques dans UX1.
- La chaine Docker/distribution est adaptee pour utiliser le sous-module canonique `backend/` comme source, tout en conservant les chemins internes historiques dans l'image.
- Le nouveau code Python de l'API v1 utilise des docstrings conventionnelles Google style. Elles documentent les roles et comportements non triviaux, notamment les perimetres de visibilite, le mecanisme d'autorisation reutilise et le traitement des ressources hors perimetre. Les sections `Args:`, `Returns:` et `Raises:` sont ajoutees seulement lorsqu'elles apportent une information utile. Les commentaires inline sont reserves aux raisons, contraintes ou decisions qui ne ressortent pas naturellement du code ; les commentaires redondants qui paraphrasent une instruction sont evites. Cette documentation dans le code est autonome et pourra servir de reference a la future documentation developpeur Read the Docs, sans s'y substituer.
- Une reference minimale a une ressource liee peut etre exposee dans une sous-ressource Employee lorsque la relation elle-meme appartient au perimetre Employee valide. Cette visibilite relationnelle ne vaut pas autorisation autonome sur la ressource liee : les endpoints de son domaine conservent leur propre perimetre objet. Pour `Participant`, l'employe cible est borne par `Employee.get_instances_for_user("view", ...)`, puis ses participations sont exposees sans filtre `Project.get_instances_for_user`; la reference Project reste limitee a l'identite et aux dates.

- R1 utilise un tableau HTML natif local Employee, sans moteur de table ni abstraction générique. Recherche soumise explicitement ; état persistant dans les paramètres API supportés de l'URL, pagination limit/offset. La sélection reste éphémère et est effacée quand la vue change.
- Après retour utilisateur R1, la sélection unique se fait au clic sur la ligne ou par Entrée/Espace lorsque la ligne a le focus. Les liens et contrôles internes sont indépendants ; la zone contextuelle reste limitée à l'ouverture et à la désélection. Son fonctionnement est confirmé avec le retour utilisateur R1.1 ; une généralisation à d’autres domaines reste à décider selon leurs besoins. L'ouverture utilise la fiche Django historique via le helper AUTH1 jusqu'à R2 ; aucune fausse fiche React.

- R1.1 retient un moteur commun de filtres indépendant des métiers, alimenté par un catalogue déclaratif par domaine/table. Définitions, contrôles et sources de données ont des responsabilités séparées ; pas de variables globales préchargées ni callbacks métier arbitraires dans les catalogues.
- Une galerie recherchable, organisée selon les catégories du catalogue, ajoute un filtre sans choisir sa valeur. Une seule instance de chaque filtre ; la valeur se modifie directement dans la barre active, avec suppression individuelle et reset.
- L'URL est l'état persistant des filtres. Les relations utilisent des IDs stables ; les sources résolvent les libellés. Un paramètre vide conserve un contrôle ajouté sans valeur dans l'URL, mais n'est pas transmis à l'API. Les changements de filtres remettent la pagination au début en conservant recherche et tri.
- Les petites nomenclatures configurables et collections contraintes se chargeront intégralement depuis le backend ; Employee/Project utilisent une recherche distante paginée limitée au périmètre normal de visibilité de leur entité. Aucun élargissement d'autorisation pour fournir des options.
- `multiple` est explicite par filtre ; plusieurs valeurs appartiennent à une instance unique, sans répétition de filtres pour simuler AND/OR. L'encodage des multi-valeurs doit être choisi selon le contrat serveur validé. R1.1 ne branche aucun filtre multiple : Employee v1 utilise actuellement des NumberFilter scalaires pour les relations.
- Les ranges déclarent leurs paramètres de borne basse/haute et permettent une ou deux bornes. Comparaisons, inclusion des bornes et OR/IN restent des responsabilités serveur. Les contrôles non nécessaires à Employee R1.1 restent des extensions typées, non exposées dans un catalogue actif.


## UX2 — Design System de référence

- shadcn/ui Base UI/base-nova + Tailwind v4, Lucide ; primitives locales communes, pas de second système Button/Input/Popover. Les composants métier restent spécifiques à LabsManager.
- Teal Light/Dark via tokens sémantiques ; depuis R3.14, `LAB_THEME` est la préférence utilisateur unique du menu et de Settings > Interface, avec bootstrap depuis `/me/` et défaut clair pour les pages anonymes.
- Sections avant Cards, densité modérée/compacte, actions légères ghost. Employee List pilote uniquement ; futurs écrans alignés sur cette base après validation visuelle.
- Actions existantes déplacées dans le menu `⋯` de ligne, espace réservé et accès clavier. Galerie en lignes compactes et recherche distante via Combobox ; contrats R1/R1.1 conservés.

### Navigation locale et sections collapsibles

- Les grands domaines d'une ressource dense sont séparés par de vraies sous-routes. La navigation locale utilise des liens, l'URL est la source du panneau actif et le contexte/header de la ressource reste partagé.
- Les données propres à un domaine sont chargées uniquement lorsque sa sous-route est affichée. Un panneau ne répète pas automatiquement son nom sous la navigation locale : il commence par son premier titre fonctionnel utile.
- `PersistentCollapsibleSection` structure les grandes sections internes lorsque plusieurs blocs d'un même panneau justifient une réduction de la navigation verticale. Une unique grande section n'est pas rendue repliable par principe.
- L'état est persisté dans `localStorage`, avec une clé stable par type de section et jamais par instance de ressource. La première utilisation est ouverte et toute la ligne de titre sert de déclencheur accessible.
- Le dernier bloc d'un panneau n'a pas besoin d'être collapsible uniquement pour respecter la convention.

## UX2.1 et R2 — identité, langue et fiche Employee

- La langue de l'interface React suit les préférences du navigateur avec un repli français et des catalogues `fr`/`en`. La langue métier des rapports reste indépendante.
- `/api/v1/me/` expose une référence Employee nullable pour l'identité et `Ma fiche`; cette référence ne vaut pas permission générale sur les Employee.
- Le détail Employee a un serialiseur dédié afin de conserver la collection légère. Ses indicateurs réutilisent les méthodes de calcul du modèle au lieu de dupliquer les formules dans l'API ou React.
- Initialement livrées en lecture seule, les informations génériques restent une sous-ressource extensible ; R2.7 ajoute les mutations et les identifiants Lucide décrits ci-dessous, sans injection HTML.
- L'état ouvert d'une grande section est mémorisé par type de section, pas par identifiant Employee. L'expansion des éléments historiques reste locale et éphémère.
- La visibilité contextuelle d'une ressource liée explique une relation mais ne vaut jamais permission de navigation. Un lien Employee, Project ou Organization n'est rendu que si le droit de consultation indépendant est établi et qu'une route réelle existe.
- `CopyableValue` est transversal et reçoit séparément la valeur à placer dans le presse-papiers et le rendu affiché. Une valeur absente ne présente aucune action.
- La fiche Employee était strictement en lecture seule jusqu’à R2.6a.2 ; R2.7 introduit uniquement les mutations GenericInfo décrites ci-dessous.

## Employee Projects : lecture contextuelle et édition partielle R2.13c

- La classification des jalons est autoritaire côté Django et dépend de l'utilisateur courant : completed, overdue, due soon, planned, puis in progress. Le seuil due soon vient de `NOTIFICATION_ENDPOINTS_MILESTONES_STALE` via `LMUserSetting`; React n'en recalcule pas la valeur.
- Pour les jalons, l'absence de `start_date` signifie milestone/jalon et sa présence signifie task/activity. `type="q"` utilise `quotity` comme progression ; `type="o"` n'affiche aucune progression numérique.
- La collection de jalons reste contextuelle à l'Employee visible. Les marqueurs `can_view` des ressources liées déterminent seulement si une navigation indépendante peut être proposée ; ils ne filtrent pas les données nécessaires à la compréhension de la charge du subordonné.
- R2.13c ajoute `can_change` par item via `endpoints.change_milestones`. Le scope Employee accepte seulement `desc`, `quotity` et `status` par PATCH, avec `save()` et la cohérence progression/terminé du Planning Project. Le Sheet commun reste en consultation par défaut ; aucune création, suppression ou mutation de dépendance n'est proposée depuis Employee. Project garde son CRUD complet ; le Gantt Employee reflète la relecture sans devenir éditable directement.
- Le profil de charge projet est calculé depuis les dates et quotités des relations `Participant`, jamais depuis les dates Project. Les changements de composition définissent les segments ; les participations chevauchantes d'un même Project sont agrégées.
- `range=all` est une requête explicite et conserve les bornes ouvertes. Les presets bornés sont un an (aujourd'hui −3 mois / +9 mois) et cinq ans (−1 an / +4 ans), navigables par pas de six mois avec retour à Aujourd'hui.
- `ProjectWorkloadTimeline` reste compact, affiche un profil en escalier et le seuil 100 %, autorise une échelle supérieure à 100 %, et réserve le token `--destructive` à la seule surcharge. La composition Project est accessible au clavier et au pointeur. Aucun faux lien Project n'est créé.

## R2.4b Contracts

- La temporalité d'un Contract est déterminée par `start_date` et `end_date`. `Contract.is_active` indique qu'un suivi ou une action RH reste à prévoir, notamment à l'échéance ou pour un renouvellement ; il ne doit pas produire un libellé temporel « Actif/Inactif » dans le nouveau frontend.
- Un Contract est lié à un Fund. `Fund_Institution` est le financeur ; l'Institution gestionnaire est `project.Institution` via `Fund.institution` et constitue une information essentielle de la lecture RH.
- La visibilité contextuelle du Fund ou de l'Institution n'autorise pas leur navigation. Un lien Institution exige la permission indépendante `common.display_infos` ; le parcours Django historique demeure. Depuis R2.24b, les fiches Institution et Financeur possèdent des routes React réelles pour ces liens visibles.
- Le panneau présente une liste synthétique des contrats courants, futurs et historiques. Un `ContractDetailSheet` latéral réunit les détails utiles et une synthèse des `Contract_expense` associés.
- Les dépenses du contrat sont chargées à la demande lors de l'ouverture du détail, et non avec toute la liste. Cette synthèse ne mensualise pas artificiellement les dépenses, ne projette pas de valeurs et ne crée ni graphique financier ni dashboard comptable.
- `Expense.status` (`Engaged`, `Realised`, `Projected`) n'est pas utilisé fonctionnellement dans cette interface prévue et ne doit créer aucune dépendance React. Son éventuelle suppression future reste indécise ; aucune suppression de modèle n'est décidée ici.
- R2.4b reste strictement en lecture seule. Les mutations Contract sont différées.

## R2.15 Contracts Project et harmonisation Employee

- La présentation R2.4b par groupes et `ContractDetailSheet` est remplacée dans les deux fiches par une liste sélectionnable, un détail partagé sous la liste, puis `ExpenseSection`. Le Sheet Contract sert à créer et modifier ; les actions de ligne utilisent le menu canonique et la suppression confirmée.
- Les capacités Project Contract découlent de `project.change_project` global ou objet sur le Project visible, sans exiger un droit RH sur chaque Participant. Les capacités Employee Contract gardent leurs règles propres ; le même Contract peut donc avoir des actions différentes selon l'endpoint.
- Le Fund d'un Contract Project appartient au Project et son Employee en est Participant, vérifiés côté serveur. L'identité Employee/Fund ne change pas lors d'un PATCH. `Contract.is_active` reste exclusivement l'indicateur « Suivi RH » ; la temporalité dépend des dates.

## R2.5 Financement, Contributions et Budgets

- La sous-route Employee `/funding` est le panneau commun aux Contributions et aux Budget items affectés à l'Employee ; ces deux notions restent présentées dans des sections distinctes.
- Après autorisation de l'Employee racine, ses Contributions sont contextuelles et proviennent directement de `Contribution.objects.filter(employee=employee)`. Aucun second périmètre autonome Contribution ne réduit cette collection.
- `Participant.quotity` décrit la charge Project, tandis que `Contribution.quotity` décrit la quotité RH déclarée au financement. Ces valeurs et leurs timelines restent séparées.
- Un type de coût RH est un `Cost_Type.is_hr=True` ou l'un de ses descendants MPTT.
- `WorkloadTimeline` porte seulement le renderer temporel commun. Les adaptateurs Project et Contribution fournissent leur vocabulaire et leur composition métier.

## R2.6a — Calendar Core et absences Employee

- Le calendrier commun est un service d'agrégation non persistant. `CalendarContext` et `LabsManagerCalendarEvent` sont indépendants du système de plugins ; `CalendarService` est seul responsable de leur découverte, de l'isolation des erreurs et de l'ordre cœur puis plugins.
- Les domaines convertissent eux-mêmes leurs modèles en événements. Le Calendar Core ne connaît pas la sémantique Leave et n'interprète pas `ST`, `MI` ou `EN` ; ces valeurs restent transportées comme métadonnées.
- Une sous-ressource Calendar autorise d'abord sa ressource racine. Pour Employee, les Leave proviennent ensuite directement de la relation Employee, sans second périmètre autonome Leave.
- `CalendarEventMixin` expose `get_calendar_events(context)` et `filter_calendar_queryset(queryset, context)`. Les anciennes mutations de liste d'événements ne constituent plus une API interne supportée.
- `/calendar_plugin/` reste compatible comme façade FullCalendar des écrans Django et délègue au même service ; aucun moteur historique parallèle n'est conservé.
- Les vues calendaires React demandent toujours une période bornée. Depuis R2.16c, Employee et Project partagent `projectCalendarScopes` et `projectDayGridViews` pour 15 jours, Mois, 2 mois et Année ; l'ancien calendrier Employee cinq ans est supprimé. Les timelines de charge Project/Contribution ne dépendent pas de FullCalendar.
- Un adaptateur explicite convertit le contrat Calendar en `EventInput`. `description`, `source`, `kind` et `metadata` restent dans `extendedProps`; `display="background"` demeure un vrai événement de fond FullCalendar. Project Ressources utilise Scheduler et sa clé AGPL depuis R2.16.
- Un événement de plugin reste distinct d'un événement métier Leave. Seul l'événement Leave ouvre le Sheet du congé.
- Les textes calendaires restent des données brutes. L'API et les producteurs ne pré-échappent pas les apostrophes en entités HTML ; React et FullCalendar assurent l'échappement de rendu normal.
- Les plugins déclarent leurs filtres par `get_calendar_filters(CalendarContext)`. Le cœur les normalise sous `LabsManagerCalendarFilter` (`id`, `title`, `type`, `source`, `choices`, `default`) et les agrège dans `CalendarService`; React traite leurs identifiants comme des données opaques.
- Les définitions historiques `FILTERS` restent une forme déclarative acceptable et leurs `choices`/`default` peuvent être statiques ou issus de classmethods. L'interface Django historique est un adaptateur du contrat normalisé, pas un moteur parallèle.
- Les vues DayGrid communes affichent tous les événements sans débordement `+X` ; les événements de fond restent transmis à FullCalendar dans chaque scope.
- Les demi-journées utilisent une règle textuelle partagée : Matin ou Après-midi sur un seul jour, À partir de midi ou Jusqu'à midi sur plusieurs jours, et Midi → midi lorsque les deux bornes sont à midi.
- R2.6a.2 clôt le Calendar/Leave Employee en lecture seule. La roadmap a ensuite séparé le Gantt Employee R2.8 des futurs scopes Project/global, puis R2.9 dépendances déclaratives sans scheduling et R2.10 mutations Leave.

## R2.8 — Gantt Employee

- `@svar-ui/react-gantt` OSS/MIT est le renderer, isolé dans SvarGanttAdapter. Les adaptateurs de scope produisent le contrat LabsManagerGantt indépendant des endpoints et de SVAR ; seul EmployeeGanttAdapter est implémenté dans ce lot. Project et Global restent différés.
- CalendarService reste la seule entrée des plugins. `LabsManagerCalendarEvent` et les filtres déclaratifs existants sont réutilisés avec le contexte `employee-gantt`, sans second contrat d'événement ou de filtre. Les événements `display="background"` sont conservés par l'API mais non rendus faute de mécanisme public OSS satisfaisant pour leurs plages et couleurs.
- La vue est read-only : aucune édition, dépendance ou planification automatique. Fenêtres 6 mois/1 an/2 ans ; aucun repère « aujourd'hui » obligatoire. Les dépendances entre planning items appartiennent à R2.9.

## R2.9 — dépendances déclaratives

- `MilestoneDependency` relie deux `Milestones`, sans limiter les Projects ni modifier les dates. Self et doublon sont contraints en base ; les cycles sont contrôlés sous transaction côté backend. L'ordre des dates effectives (`start_date` ou `end_date`) est informatif seulement.
- Le POST et le DELETE nécessitent `change` sur les deux Projects selon la méthode canonique de Project, réévaluée lors de chaque requête. La recherche des candidats est bornée par ces mêmes droits. Le CRUD reste dans le Sheet existant ; les liens du Gantt Employee sont uniquement rendus et uniquement lorsque les deux éléments sont déjà dans son scope.
- La lecture des dépendances suit la visibilité Project ou Employee contextuelle, sans exiger `change` ; les capacités de mutation restent calculées par les droits Project. Le formulaire d'ajout s'ouvre à la demande.

## R2.10 — absences Employee

- Les mutations Leave suivent `change_employee` sur l'Employee de l'URL. Le catalogue Leave_Type est sélectionnable à tous les niveaux ; les dates sont obligatoires à l'écriture. Un même Employee et un même type ne peuvent avoir deux intervalles de demi-journées qui se chevauchent ; deux intervalles contigus sont permis. Aucun schéma supplémentaire n'est introduit.
- Un seul Sheet sert Tableau et Calendrier pour consultation, création et modification. Depuis R2.16c, les quatre scopes Employee permettent la sélection de plage ; la date de fin exclusive FullCalendar est convertie dans l'UI. Calendar Core et ses plugins conservent leur contrat.
- **Toute suppression déclenchée depuis l'interface utilisateur nécessite une confirmation explicite avant exécution.**

## R2.11a — liste Project

- La visibilité de la liste et du détail Project suit `Project.get_instances_for_user("view")` ; le backend publie les capacités de mutation calculées avec les droits Project existants. Les relations de liste sont compactes et préchargées, avec la visibilité Fund appliquée aux fonds affichés.
- Le catalogue de filtres React reste commun aux listes Employee et Project. Active=true est une valeur initiale explicite et visible dans les deux listes ; un marqueur d'initialisation d'URL empêche son retour après retrait volontaire. Les définitions métier restent propres à chaque liste.
- La création et l'édition de Project partagent un Sheet limité aux champs racine. La création navigue avec l'identifiant du POST vers une route React transitoire ; le contenu de la fiche Project relève de R2.11b. La suppression utilise la confirmation générale.

## R2.11b — fiche Project

- La Vue d’ensemble est la seule section Project active. Les autres entrées restent visibles mais désactivées jusqu’à leur lot métier ; aucun contenu financier n’est ajouté.
- Les droits Project et des trois collections enfants sont calculés et appliqués côté backend. Les mutations enfants restent rattachées au Project de l’URL. L’ajout et la modification suivent les droits Project objet ou les permissions globales du modèle enfant ; la suppression requiert la permission globale de suppression correspondante. Le choix d’un Employee pour un Participant exige sa visibilité.
- GenericInfo utilise un composant React commun aux fiches Employee et Project, paramétré par les appels API et les capacités contextuelles. La quotité Participant est stockée comme fraction et présentée en pourcentage dans le formulaire.

## R2.11-refactor-2 — Shared Planning Core

- Tasks et Milestones constituent un même métier Planning : `PlanningMilestoneTable`, `MilestoneDetailSheet`, le contrat API et `PlanningGanttAdapter` sont communs aux scopes. Cette évolution remplace l'hypothèse R2.8 d'un `ProjectGanttAdapter` nécessaire par défaut.
- Le backend qualifie les états temporels selon la préférence de l'utilisateur et applique les filtres Planning au queryset déjà borné par le contexte. Tableau et Gantt consomment la même collection ; les filtres Calendar/plugins continuent à ne concerner que leurs événements.
- Aucun CRUD Task/Milestone React n'existe dans le contexte Employee actuel. Le futur CRUD Project doit réutiliser un socle commun lorsque son contrat sera défini ; l'affectation d'un Employee doit être validée côté backend contre les participants du Project, indépendamment de `change_project`.


## R2.7 — premier pattern de mutation React

- GenericInfo est le premier cas CRUD ; pas de framework CRUD déclaratif. Formulaire métier,
  petite primitive de mutation, normalisation DRF, confirmation et rafraîchissement réutilisables.
- GenericInfo reste attaché à Employee. Valeur texte facultative, null/vide admis, 150 caractères,
  doublons Employee/type autorisés. Le type est choisi à la création et immuable ensuite,
  y compris côté API. L’Employee vient uniquement de l’URL ; champs interdits refusés par 400.
- FULL CHANGE combine `staff.change_employee` global et objet selon sa sémantique historique.
  `common.self_edit` conserve son rôle d’autorisation explicite pour éditer sa propre fiche.
- `staff.change_partial_employee` est une rule objet : FULL CHANGE ou Employee lié à l’utilisateur.
  Le nouveau prédicat d’identité ne modifie pas `is_user_employee`. Aucune permission modèle
  attribuable supplémentaire n’est introduite.
- Après accès à l’Employee : lecteur = read ; soi sans self_edit = read/create ; soi avec
  self_edit ou autre full change = read/create/update/delete. Le même calcul backend fournit
  les capacités et contrôle les mutations. Aucune règle hiérarchique dans React.
- Les capacités `{can_add, can_change, can_delete}` sont sur l’enveloppe de la collection
  GenericInfo, même vide. Le catalogue GenericInfoType est global, authentifié et read-only.
- Création et modification utilisent un Sheet local ; aucune édition globale de la fiche.
  Le menu ne contient que les actions autorisées. Hover, focus et sélection donnent accès
  aux actions ; sur tactile elles sont disponibles sans hover.
- DELETE est définitif et précédé d’une confirmation accessible. Auditlog reste la traçabilité.
- Succès de mutation et succès de relecture sont distincts. La réponse serveur actualise
  immédiatement l’affichage ; une relecture échouée ne déclenche jamais une nouvelle écriture.
- GenericInfoType sort de FAIcon en R2.7 : CharField et mapping Django borné vers Lucide.
  Une icône inconnue est conservée exactement en base ; CircleQuestionMark est le fallback React.
  Null et vide restent acceptés. Aucun convertisseur général ni adaptateur Lucide vers FAIcon.
- La conversion perd les styles FA et est explicitement non réversible. Sauvegarde BDD avant
  production et restauration avec version applicative correspondante constituent le rollback.
- Le legacy Employee abandonne seulement le rendu FAIcon concerné. Project suivra en
  R2.11b ; la dépendance FAIcon reste nécessaire aux autres modèles et migrations historiques.
- Création imbriquée de type, mutations de types en API v1, Paramètres React, Note, Gantt,
  dépendances et mutations Leave restent exclus. Aucune nouvelle dépendance.

## R2.12b — Expense individuelle

- `Expense.fund_item` pointe vers Fund ; `expense.change_expense` suit l'intention historique
  `project.change_project` via ce lien. La permission Fund ne s'y substitue pas.
- L'affectation et la désaffectation d'un Contract conservent le parent Expense et son PK.
  La promotion insère l'enfant multi-table `Contract_expense` avec le même PK ; la
  désaffectation supprime seulement cet enfant avec `keep_parents=True`.
- Une Contract_expense exige le Cost_Type RH historique ; Contract et Budget sont
  indépendants et doivent appartenir au même Fund. Les trois statuts restent agrégés
  identiquement ; la dépense individuelle conserve le signe saisi.
- La synchronisation est une action Fund autorisée par `fund.change_fund` objet et
  le mode `e`/`h`, sans permission Django nouvelle. Elle conserve l'appel historique
  `calculate_expense(force=True)` et actualise ensuite les totaux en cache.

## R2.14 — Budgets et Contributions Project

- Budget et Contribution restent deux modèles et deux sections métier ; les contrats de champs, formulaires et Sheets partagent uniquement le socle réel `BudgetAbstract`. Une ligne correspond à un objet, sans agrégation ni répartition automatique.
- Les écritures Project Budget/Contribution utilisent le droit objet `project.change_project`, exposé aussi comme capacité API. La lecture exige le Project et le Fund visibles. Les validations `clean()` et les hooks de persistance restent côté Django.
- Seul Budget porte des Expense contextuelles ; la création fixe Budget et Fund dans l’API, et React réutilise `ExpenseSection`. Le calcul historique `available = amount - expense` est conservé, indépendamment de la convention Fund. Aucun Expense n’est associé à Contribution.
- La suppression d’un Budget conserve le `on_delete=CASCADE` historique sur `Expense.budget_item` ; l’interface l’annonce dans la confirmation. Aucun versioning, workflow ni contrôle global d’enveloppe n’est introduit.

## R2.16 — Calendar Project et Scheduler

- Leave reste un événement cœur produit par un seul producteur du domaine Leave pour Employee et Project ; `CalendarService` agrège les événements complémentaires des plugins sans devenir producteur Leave.
- La lecture Project Calendar suit `Project.get_instances_for_user("view", ...)` ; une mutation Leave exige `staff.change_employee` sur l'Employee. La création depuis Project exige aussi que l'Employee soit Participant du Project.
- La vue Ressources utilise `resourceTimeline` du paquet officiel FullCalendar 7 `@fullcalendar/react-scheduler` : Mois standard et durées 15 jours, 2 mois et Année depuis R2.16a. Le dépôt étant sous AGPLv3, elle emploie `AGPL-My-Frontend-And-Backend-Are-Open-Source`.

## R2.17 — Generic Notes

- `GenericNote` conserve son lien générique et ajoute un auteur obligatoire, protégé contre suppression, ainsi que `visibility=object|creator`. La migration attribue les notes historiques au compte administratif nommé `ben_admin`, identifié sur la base de développement ; son absence bloque volontairement une migration d'un environnement contenant des notes.
- L'API Notes v1 accepte Project, Employee, Team, Institution et Contract comme parents. Elle filtre la visibilité avant de retourner les notes et partage un seul calcul de capacités avec les mutations. Le créateur n'est jamais accepté depuis le client. La permission historique `staff.changenote_employee` reste distincte de `staff.change_employee` ; Contract utilise `expense.change_contract`.
- Le panneau React réutilise l'éditeur WYSIWYG déjà fourni par `django_prose_editor` et le champ backend sanitizé. Le contenu se sauvegarde après temporisation et à la fermeture de l'édition ; nom et visibilité ont leurs actions propres. Le même `GenericNotes` est hébergé en Sheet depuis la ligne Contract, sans système Notes parallèle. Son compteur est filtré par visibilité et agrégé côté backend.

## R2.19a — filtres des listes Employee et Project

- La liste Employee complète son catalogue URL existant sans état parallèle : le filtre Nom partage le paramètre `search` et sa recherche backend prénom/nom ; Statut couvre tout l'historique, Statut actuel suit `Employee_Status.current`, Team couvre leader et TeamMate, Project suit Participant. Les sous-requêtes d'identifiants conservent l'intersection et évitent les doublons.
- Les choix Statut/Team proviennent des relations d'Employees visibles. Le Project choisi utilise le même `EntitySearch` que Supérieur et Participant. Les liens vers les fiches transmettent le contexte de liste pour que le retour dédié restitue son URL filtrée, triée et paginée.
- Les dix filtres Project et leur sémantique restent inchangés. « En retard » applique `Project.staleFilter()` : Project actif dont `end_date` est au plus tard maintenant plus `DASHBOARD_PROJECT_STALE_TO_MONTH` mois (3 par défaut), y compris les projets déjà échus.

## R2.19b — exports des listes Employee et Project

- Les vues d'export réutilisent les vues de liste v1 pour construire le queryset visible, filtré et ordonné ; seule la liste le pagine. Les Resources métier historiques produisent les fichiers complets, sans colonnes React propres à l'export.
- CSV, TSV, XLS et XLSX sont explicitement autorisés. Les endpoints d'export réservent `?format=` au choix du fichier, malgré l'override de renderer portant le même nom dans DRF ; leur réponse fichier a un MIME et un nom daté propres. Le Dialog de liste est partagé entre Employee et Project, distinct du Dialog de rapports Word/PDF.
- `ProjectResource` reçoit explicitement un scope Fund. Les exports utilisateur v1 et historique réutilisent `Fund.get_instances_for_user("view", …)` et transmettent les Funds visibles préchargés ; le texte Fund et les six agrégats sont bornés au même ensemble. Le mode complet est réservé aux appels explicites de confiance et n'est pas employé par les endpoints utilisateur.

## R2.20 — contexte Team

- La visibilité Team conserve le prédicat historique : responsable ou TeamMate, avec la permission globale `staff.view_team` ; la composition se modifie avec `staff.change_team` selon sa sémantique existante. Une mutation Leave ne dérive jamais de ce droit Team : elle exige `staff.change_employee` sur le membre.
- Un Project Team est retenu seulement si un membre est Participant leader ou co-leader, puis filtré par visibilité Project. Un Budget Team exige en plus la visibilité Fund et Budget ; sa présentation est en lecture seule et n'expose aucune mutation Expense.
- `CalendarType.TEAM` ajoute uniquement la résolution des membres au producteur Leave partagé. Le panneau React Calendar Project accepte le contexte Team et conserve les quatre scopes, Resources, filtres plugins et le Sheet Leave communs.

## R2.21a — préférences génériques et compatibilité

- Conserver `favorite` et `subscription` comme modèles canoniques. Une migration supprime les seuls doublons éventuels en conservant le plus petit PK, puis ajoute une contrainte unique sur utilisateur/type/objet.
- Le client définit explicitement chaque état booléen via l'API v1 ; les anciens toggles HTML restent fonctionnels mais délèguent au même service. Seuls les types déclarés et les objets visibles sont acceptés.
- Les favoris invisibles restent enregistrés mais disparaissent des menus et des anciennes listes REST. Les abonnements restent indépendants de la navigation Favorites ; la sélection du rapport mail tient compte de la visibilité, sans modifier ses réglages ni sa fréquence.

## R2.22 — Accès contextualisé à Django Admin

- L’action Admin réutilise les menus métier existants, mais son autorisation est distincte : superuser ou staff ayant `user.has_perm("<app>.change_<model>", obj)`. Le backend ne publie pas de lien si le modèle n’a pas de route Admin.
- L’API transmet une URL résolue ou `null`. React n’infère ni nom de route, ni permission, et ouvre le lien dans un nouvel onglet. Un modèle présent seulement en inline, comme TeamMate, ne reçoit pas de page de modification dédiée.

## R2.23 — Contract Hub transversal

- Le Hub est un outil de consultation et de modification des Contracts visibles, jamais un point de création ou de suppression de Contract, même pour un utilisateur disposant de permissions techniques supplémentaires.
- Active (`Contract.is_active`/suivi RH), Ongoing (inclusion de la date courante dans les deux bornes) et Stale (`Contract.staleFilter()`) sont trois filtres distincts et cumulables.
- Dans ce contexte autonome, Modifier suit `expense.change_contract` ; les droits de mutation Project ou Employee des fiches parentes ne sont pas transposés. Les Expense conservent leurs propres capacités et contrôles backend.

## R2.27 — imports React

- Les profils d'import déclarent chacun leur Resource et leur permission ; les trois profils initiaux conservent `common.import` du workflow historique. Le frontend reste ignorant des classes et validations métier.
- Dry-run et commit relisent le même fichier temporaire et la même feuille via un token signé lié à l'utilisateur et au profil. La transaction globale existante est conservée ; les erreurs transformées en `skip` par la Resource autorisent toujours un résultat partiel.

## R2.29b — listes mutables Settings

- Les neuf listes actives du legacy sont définies par un registre backend fermé ; React consomme ses métadonnées et ne connaît ni modèles ni formulaires Django.
- La lecture suit l'accès Settings authentifié historique ; les mutations vérifient les permissions globales du modèle. Les formulaires historiques déterminent les champs modifiables. Aucune suppression n'est activée, conformément aux panneaux Settings actifs et à leurs relations potentiellement en cascade.

## R2.30 — impression statique enregistrée

- Un aperçu React dédié reçoit une capture des données et de l'état courant ; il n'imprime pas le DOM de FullCalendar, SVAR ou React Flow, dont le viewport, le scroll et les transforms peuvent tronquer le résultat.
- Les renderers sont enregistrés par clé dans un registre frontend indépendant des métiers. Un futur plugin pourra ajouter son renderer frontend sans changer le shell ; aucun code plugin distant n'est chargé dans ce lot.
- L'aperçu recouvre la SPA sans démonter la vue source afin que Retour retrouve exactement son état. L'impression navigateur n'est proposée qu'après le signal de disponibilité du renderer.

## R3.1 — Dashboard Foundation

- Plusieurs Dashboards personnels par utilisateur ; une contrainte DB conditionnelle et des transactions sur la ligne User garantissent un seul default au maximum. Le premier dashboard créé est default. Après suppression du default, le premier restant dans l'ordre utilisateur devient default ; après suppression du dernier, l'onboarding revient.
- Le modèle Employee/Leader/Lab manager/Blank est toujours choisi explicitement. Un template est copié en instances à la création et n'est jamais lié au Dashboard vivant.
- DataSource, renderer, WidgetDefinition et WidgetInstance restent distincts. Les définitions core/plugins ne sont pas persistées ; les instances enregistrent des clés stables et une config validée.
- Le contexte Dashboard vient de la route et du backend authentifié. Seul `user` est actif en R3.1 ; `project` et `employee` sont préparés sans `GenericForeignKey` anticipé. Un Dashboard n'accorde aucune permission métier supplémentaire.
- Le registre Dashboard agrège le core et les plugins actifs découverts par le registre plugin existant. `DashboardPluginMixin` est le point d'extension ; aucun bundle React distant n'est exécuté.
- React Grid Layout v2 est retenu avec React 19 et TypeScript ; un layout desktop est persisté par lot, tandis que le mobile suit l'ordre logique. La route React canonique est `/app/dashboard` ; le Django legacy reste disponible séparément.

## R3.2 — Source, renderer et configuration Dashboard

- Une instance possède une source et un renderer distincts. Une même DataSource peut fournir plusieurs payloads normalisés, sélectionnés par le renderer compatible ; les renderers React ne connaissent aucun modèle métier.
- La configuration est déclarée par source, éventuellement complétée par le renderer ou une ancienne définition, dans un JSON plat aux clés distinctes. L’API applique les défauts et refuse types, choix, bornes et clés inconnues invalides. Les sources core et plugin traversent le même pipeline ; les plugins n’exécutent pas de bundle React distant.
- La variante de rendu compact/standard/expanded est calculée une seule fois depuis la taille de grille. Duplicate Widget est différé ; le détail Dashboard continue de fournir les données des widgets en une réponse batch.

## R3.4 — présentation et impression Dashboard

- Présentation et impression sont deux modes du Dashboard existant. La présentation est une route authentifiée sans chrome global ; l'impression reprend l'instantané déjà chargé par le `PrintRegistry` central.
- Le papier utilise `logical_order` et une grille A4 paysage indépendante des coordonnées RGL. Aucun champ `print_order` ou contrôle de réordonnancement n'est ajouté.
- Une définition `printable=false` est omise ; une définition indisponible reste lisible par placeholder. Un renderer peut fournir un composant print local optionnel, avec repli sur son rendu normal.

## R3.5 — Dataset synthétique dédié

Le générateur de démonstration opère sur une base dédiée, refuse une génération incrémentale en présence de données opérationnelles et ne marque pas les lignes métier. Son `--reset` est transactionnel et réservé à DEBUG ou à une base de test ; il recrée le jeu entier en conservant les catalogues techniques et les groupes issus de la fixture existante. T0 et la seed sont explicites pour rendre les scénarios reproductibles. Cette décision évite d'introduire une logique demo dans les APIs ou les modèles de production.

## R3.6 — Dashboard Project et historique financier

- Le Dashboard Project conserve le modèle, les WidgetInstances et le registre R3.1–R3.4. La relation Project optionnelle introduite par `dashboard.0003` est historique ; R3.6a la remplace par un contexte générique sans changer la propriété de l’instance ni l’unicité par owner/contexte.
- L’évolution des dépenses utilise l’historique métier `AmountHistory` des `Expense_point`, après filtrage des Funds visibles, plutôt qu’une nouvelle table de séries ou des Expenses recalculées dans React. Les périodes demo supplémentaires passent par les signaux existants.
- `line-chart` est un renderer core générique SVG sans dépendance graphique. Les sources plugins peuvent l’utiliser en déclarant le scope Project ; aucune dépendance core vers un plugin ni code frontend plugin distant n’est introduit.

## R3.6a — Ownership et contexte métier séparés

- `owner` identifie toujours le configurateur ; deux champs de contexte nuls identifient le Dashboard personnel. Un contexte non nul utilise `ContentType` et l’identifiant d’objet, avec unicité owner/type/id. Seuls user et Project sont résolus par l’API aujourd’hui ; le stockage est indépendant du modèle métier.
- `dashboard.0004` migre les valeurs Project après `0003` déjà appliquée, puis supprime la FK spécifique. Le reverse restaure les Project et refuse les contextes non Project. Un signal Project `post_delete` restitue la cascade de l’ancienne FK ; aucun orphelin Project n’est laissé.
- Les sources/plugins continuent à recevoir le seul `DashboardContext` résolu et ses noms de scope existants. Le frontend ne connaît ni `ContentType` ni le stockage ORM.

## R3.7 — Plugin Dashboard concret

- `FrenchHollidayPlugin` sert de référence pour une contribution Dashboard autonome : une seule source à deux renderers core (KPI et liste compacte) sur les contextes `user` et `project`. Le plugin réutilise son setting de zone et ses fichiers JSON locaux ; le rendu ne synchronise jamais les données. Aucun renderer React spécifique ni import plugin dans le cœur Dashboard.

## R3.8 — Fondation Global Search

- Le registre `global_search` est l'unique source des providers core et des contributions des plugins actifs via `SearchPluginMixin`. Aucun modèle métier n'hérite d'un mixin Search ; chaque provider possède son périmètre visible, son type de résultat et sa destination React.
- Le moteur v1 reçoit `SearchQuery` structuré, applique un matching ORM simple et produit des `SearchResult` comparables avec raison du match. Le schéma machine-readable expose les champs/capacités actifs ; l'interface et la grammaire avancée sont différées.
- `GenericInfoType` ne reçoit aucun flag de recherche. Le schéma R3.8/R3.9 n'annonçait pas encore les GenericInfo Employee/Project ; leur inclusion automatique arrive en R3.10. L'opérateur stable `info:` reste réservé à un lot ultérieur.

## R3.10 — Providers métier Global Search

- Les axes relationnels restent explicites par provider : tous les participants Project sont recherchables ; un Fund ne matche jamais par le seul nom de son Project. Les GenericInfo Employee/Project visibles suivent automatiquement la visibilité du parent, sans configuration des types.
- Le moteur conserve le contrat `SearchResult` et ajoute des poids aux axes déclarés ainsi que des `counts` exacts issus des querysets visibles, indépendants des limites de résultats. Les plugins gardent un poids par défaut et le même contrat de recherche.
- Les destinations utilisent les routes existantes : ligne Fund dans Project Funding et Hub Contract filtré sur l'Employee. La création d'un deep-link Contract unique est différée ; aucun droit de lecture n'est inféré de la seule relation.

## R3.11 — Langage Global Search

- Les mots-clés AND/OR/NOT sont insensibles à la casse et ont la priorité NOT > AND > OR ; les espaces seuls conservent la recherche libre multi-termes R3.10. Les clés provider/field sont déclarées par le registre actif, avec priorité au provider en cas de collision. Une clé inconnue est une erreur 400 structurée ; un type GenericInfo inconnu est une requête valide sans résultat.
- `info:"TYPE"="value"` compare exactement, sans tenir compte de la casse, le nom de type et la valeur. Le provider applique sa visibilité canonique avant toute condition, y compris négative ; un champ non déclaré rend la branche inapplicable à ce provider. L'AST reste interne au backend, sans nouvelle dépendance ni endpoint public.

## R3.12 — Autocomplétion Global Search

- Le contexte d'autocomplétion est calculé côté backend depuis le tokenizer R3.11 en mode tolérant ; la recherche exécutée garde son parser strict. L'endpoint renvoie contexte, plage de remplacement et texte à insérer. React partage le même contrôle Topbar/page et ne contient aucune grammaire métier.
- Les suggestions de valeurs proviennent uniquement des querysets visibles des providers actifs, avec projection bornée ; les champs et valeurs plugins suivent le même contrat. Les types GenericInfo reprennent les catalogues visibles, sans exposer de valeurs GenericInfo. Aucun opérateur de recherche supplémentaire n'est ajouté.

## R3.13 — Home et récents

- Un récent désigne une destination ouverte, objet ou page, identifiée par `url_id` et `obj_id` nullable. Deux contraintes partielles garantissent l'unicité avec et sans `obj_id` sur PostgreSQL. Le frontend décide quand suivre ; le backend contrôle et résout, sans accepter d'URL arbitraire.
- La Home reste un hub sans widgets, favoris ni annonces. Les liens Search et Recent partagent les destinations métier canoniques ; la visibilité actuelle est revérifiée à chaque lecture. Les pages financières globales suivent leur API authentifiée, tandis que Calendar conserve sa capability de navigation.

## R4.3 — Upgrade explicite et transport de confiance

- Les migrations de production ne sont pas lancées automatiquement par plusieurs services. L'opérateur sauvegarde la base, applique les migrations une seule fois avec la nouvelle image, puis démarre la stack ; serveur et worker refusent un schéma incomplet. Le retour arrière s'appuie sur le dump et l'image antérieure, pas sur une inversion automatique des migrations.
- Django ne fait confiance à `X-Forwarded-Proto` que sur opt-in explicite. nginx fixe `http` sur ses ports directs et `https` sur deux listeners réservés à un terminateur TLS de confiance (React et legacy), publiés seulement sur loopback ; le port Gunicorn publié est aussi limité au loopback. Le frontend compilé garde ses URLs Django relatives dans le déploiement de même origine.

## Dashboard — grammaire de visualisation

- Le Dashboard possède une grammaire visuelle dédiée construite sur le design system LabsManager. Ses renderers peuvent hiérarchiser métriques, densité, progression et statut différemment des composants génériques, tout en conservant tokens Light/Dark, Lucide, typographie et accessibilité.
- Les renderers restent associés à `renderer_key` et consomment des payloads de présentation explicites. Les calculs et la visibilité métier demeurent côté backend ; la configuration demeure dans l’éditeur. Une amélioration de renderer ne crée ni runtime frontend plugin ni abstraction universelle de payload.
