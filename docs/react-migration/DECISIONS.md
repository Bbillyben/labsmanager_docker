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
- Inscription/invitation, reinitialisation et changement de mot de passe, ainsi que gestion des emails restent des workflows Django/allauth tant qu'un lot dedie ne les migre pas.
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
- Teal Light/Dark via tokens sémantiques ; sélection locale du thème dans la topbar, aucune refonte des préférences utilisateur.
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

## Employee Projects en lecture seule

- La classification des jalons est autoritaire côté Django et dépend de l'utilisateur courant : completed, overdue, due soon, planned, puis in progress. Le seuil due soon vient de `NOTIFICATION_ENDPOINTS_MILESTONES_STALE` via `LMUserSetting`; React n'en recalcule pas la valeur.
- Pour les jalons, l'absence de `start_date` signifie milestone/jalon et sa présence signifie task/activity. `type="q"` utilise `quotity` comme progression ; `type="o"` n'affiche aucune progression numérique.
- La collection de jalons reste contextuelle à l'Employee visible. Les marqueurs `can_view` des ressources liées déterminent seulement si une navigation indépendante peut être proposée ; ils ne filtrent pas les données nécessaires à la compréhension de la charge du subordonné.
- Le profil de charge projet est calculé depuis les dates et quotités des relations `Participant`, jamais depuis les dates Project. Les changements de composition définissent les segments ; les participations chevauchantes d'un même Project sont agrégées.
- `range=all` est une requête explicite et conserve les bornes ouvertes. Les presets bornés sont un an (aujourd'hui −3 mois / +9 mois) et cinq ans (−1 an / +4 ans), navigables par pas de six mois avec retour à Aujourd'hui.
- `ProjectWorkloadTimeline` reste compact, affiche un profil en escalier et le seuil 100 %, autorise une échelle supérieure à 100 %, et réserve le token `--destructive` à la seule surcharge. La composition Project est accessible au clavier et au pointeur. Aucun faux lien Project n'est créé.

## R2.4b Contracts

- La temporalité d'un Contract est déterminée par `start_date` et `end_date`. `Contract.is_active` indique qu'un suivi ou une action RH reste à prévoir, notamment à l'échéance ou pour un renouvellement ; il ne doit pas produire un libellé temporel « Actif/Inactif » dans le nouveau frontend.
- Un Contract est lié à un Fund. `Fund_Institution` est le financeur ; l'Institution gestionnaire est `project.Institution` via `Fund.institution` et constitue une information essentielle de la lecture RH.
- La visibilité contextuelle du Fund ou de l'Institution n'autorise pas leur navigation. Le lien Institution utilise le parcours Django Organization `/infos/project/institution/<id>` seulement avec la permission indépendante `common.display_infos`; aucune route React fictive n'est créée.
- Le panneau présente une liste synthétique des contrats courants, futurs et historiques. Un `ContractDetailSheet` latéral réunit les détails utiles et une synthèse des `Contract_expense` associés.
- Les dépenses du contrat sont chargées à la demande lors de l'ouverture du détail, et non avec toute la liste. Cette synthèse ne mensualise pas artificiellement les dépenses, ne projette pas de valeurs et ne crée ni graphique financier ni dashboard comptable.
- `Expense.status` (`Engaged`, `Realised`, `Projected`) n'est pas utilisé fonctionnellement dans cette interface prévue et ne doit créer aucune dépendance React. Son éventuelle suppression future reste indécise ; aucune suppression de modèle n'est décidée ici.
- R2.4b reste strictement en lecture seule. Les mutations Contract sont différées.

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
- Les vues calendaires React demandent toujours une période bornée. Le renderer Employee reste local au besoin Mois/Année/cinq ans et ne crée pas une abstraction calendrier frontend universelle.
- Le renderer Employee utilise FullCalendar React Standard pour Mois (`dayGridMonth`) et Année (`dayGridYear` depuis R2.10). La synthèse cinq ans reste interne ; les timelines Project/Contribution ne dépendent pas de FullCalendar.
- Un adaptateur explicite convertit le contrat Calendar en `EventInput`. `description`, `source`, `kind` et `metadata` restent dans `extendedProps`; `display="background"` demeure un vrai événement de fond FullCalendar. Aucun composant Scheduler/Premium et aucune clé de licence ne sont introduits.
- Un événement de plugin reste distinct d'un événement métier Leave. Seul l'événement Leave ouvre le Sheet du congé.
- Les textes calendaires restent des données brutes. L'API et les producteurs ne pré-échappent pas les apostrophes en entités HTML ; React et FullCalendar assurent l'échappement de rendu normal.
- Les plugins déclarent leurs filtres par `get_calendar_filters(CalendarContext)`. Le cœur les normalise sous `LabsManagerCalendarFilter` (`id`, `title`, `type`, `source`, `choices`, `default`) et les agrège dans `CalendarService`; React traite leurs identifiants comme des données opaques.
- Les définitions historiques `FILTERS` restent une forme déclarative acceptable et leurs `choices`/`default` peuvent être statiques ou issus de classmethods. L'interface Django historique est un adaptateur du contrat normalisé, pas un moteur parallèle.
- La vue annuelle utilise `dayGridYear` depuis R2.10 ; sa lisibilité étroite reste améliorable. La synthèse cinq ans exclut tous les événements `display="background"` et affiche les dates des événements conservés.
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
- Un seul Sheet sert Tableau et Calendrier pour consultation, création et modification. Seules les vues Mois/Année permettent la sélection de plage ; la date de fin exclusive FullCalendar est convertie dans l'UI. Calendar Core et ses plugins conservent leur contrat.
- **Toute suppression déclenchée depuis l'interface utilisateur nécessite une confirmation explicite avant exécution.**

## R2.11a — liste Project

- La visibilité de la liste et du détail Project suit `Project.get_instances_for_user("view")` ; le backend publie les capacités de mutation calculées avec les droits Project existants. Les relations de liste sont compactes et préchargées, avec la visibilité Fund appliquée aux fonds affichés.
- Le catalogue de filtres React reste commun aux listes Employee et Project. Active=true est une valeur initiale explicite et visible dans les deux listes ; un marqueur d'initialisation d'URL empêche son retour après retrait volontaire. Les définitions métier restent propres à chaque liste.
- La création et l'édition de Project partagent un Sheet limité aux champs racine. La création navigue avec l'identifiant du POST vers une route React transitoire ; le contenu de la fiche Project relève de R2.11b. La suppression utilise la confirmation générale.


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
- GenericInfoType seul sort de FAIcon : CharField et mapping Django borné vers Lucide.
  Une icône inconnue est conservée exactement en base ; CircleQuestionMark est le fallback React.
  Null et vide restent acceptés. Aucun convertisseur général ni adaptateur Lucide vers FAIcon.
- La conversion perd les styles FA et est explicitement non réversible. Sauvegarde BDD avant
  production et restauration avec version applicative correspondante constituent le rollback.
- Le legacy Employee abandonne seulement le rendu FAIcon concerné. Project et la dépendance
  FAIcon restent en place, y compris pour les migrations historiques.
- Création imbriquée de type, mutations de types en API v1, Paramètres React, Note, Gantt,
  dépendances et mutations Leave restent exclus. Aucune nouvelle dépendance.
