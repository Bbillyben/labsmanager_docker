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
