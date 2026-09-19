# Matrice fonctionnelle de migration

Legende risque : faible, moyen, eleve. `BDD : non` signifie qu'aucune modification de schema n'est attendue a ce stade.

| Fonction | Priorite | Etat actuel | Cible React | Travail backend necessaire | BDD | Risque |
|---|---:|---|---|---|---|---|
| Authentication / current user | AUTH1 | Valide sur Debian et dans le navigateur | Session/CSRF, connexion React, utilisateur courant et deconnexion | Termine : Allauth, CSRF, non-enumeration, connexion, liens historiques et deconnexion valides | Non | Eleve |
| React shell / session bootstrap | R0 | Socle TypeScript valide sur Debian | Shell protege sous `/app/`, etats de session, client session/CSRF et 404 | Termine : installation, 13 tests, typecheck, lint et build Vite valides | Non | Moyen |
| UX/UI foundations | UX1 | Valide automatiquement et visuellement sur Debian | Sidebar/topbar accessibles, tokens, CSS Modules, responsive et primitives minimales | Termine : shell, navigation et coexistence avec les pages Django verifies | Non | Moyen |
| Permissions | P0 | Capacites globales du shell calculees par `/api/v1/me/` depuis les permissions existantes ; regles objet conservees | UI guidee, backend autoritaire | Valider le contrat de capacites, puis appliquer les controles et filtres sur chaque endpoint v1 | Non | Eleve |
| Employee list | P1 / R1 / R1.1 | API validée, retour R1 positif ; R1.1 validé fonctionnellement par retour utilisateur | Liste + galerie commune, Activité et Supérieur, URL, sélection au clic | Aucun changement ; nomenclature/multi-statut, actions et Admin différés | Non | Moyen |
| Common React filters | R1.1 | Validé fonctionnellement par retour utilisateur | Galerie catégorisée, contrôles actifs, URL, sources séparées ; choix statique et entity search | Aucun pour Activité/Supérieur ; autres sources selon contrats futurs | Non | Moyen |
| Employee detail | P1 | Endpoint minimal `/api/v1/employees/<id>/` valide sur Debian | Fiche en lecture seule enrichie progressivement | Termine : perimetre objet, contrat commun avec la liste et reponses 401/404 testes | Non | Moyen |
| Employee status history | P1 | Sous-ressource `/api/v1/employees/<id>/statuses/` validee sur Debian | Historique en lecture seule | Termine : perimetre Employee, contrat, ordre et reponses 401/404 testes | Non | Faible |
| Employee hierarchy | P1 | Sous-ressource `/api/v1/employees/<id>/hierarchy/` validee sur Debian | Relations directes actuelles et historiques en lecture seule | Termine : perimetre cible, identite minimale liee, ordre et reponses 401/404 testes | Non | Moyen |
| Employee project participations | P1 | Sous-ressource `/api/v1/employees/<id>/project-participations/` validee sur Debian | Participations actuelles et historiques en lecture seule | Termine : perimetre Employee, reference Project minimale, filtre temporel et ordre testes | Non | Moyen |
| Teams | P2 | UI Django et ViewSet | Liste/detail puis edition | Stabiliser serializers et permissions | Non | Moyen |
| Project list | P2 | UI Django et ViewSet | Liste en lecture seule | Contrat v1, filtres et pagination | Non | Moyen |
| Project detail | P2 | Fiche Django multi-domaines | Fiche React progressive | Endpoint compose ou appels bornes | Non | Eleve |
| Participants | P2 | Sous-ressource Employee en lecture seule implementee ; domaine Project non migre | Consultation Employee puis CRUD ulterieur | Definir les endpoints du domaine Project et les droits de modification | Non | Eleve |
| Funds | P2 | UI Django et ViewSet | Consultation puis CRUD | Contrats v1, calculs et droits | Non | Eleve |
| Financial summary | P3 | Calculs repartis | Synthese React | Source canonique et endpoint agrege | Non | Eleve |
| Budgets | P3 | ViewSet et formulaires | CRUD React | Validation et permissions API | Non | Eleve |
| Contributions | P3 | ViewSet et formulaires | CRUD React | Validation et permissions API | Non | Eleve |
| Expenses | P3 | ViewSet et UI complexes | CRUD React | Normaliser contrats et calculs | Non | Eleve |
| Contracts | P3 | ViewSet et sous-ressources | CRUD React | Contrat v1 et validations | Non | Eleve |
| Milestones | P2 | ViewSet et modales | Liste/calendrier puis CRUD | Actions v1 valider/decaler | Non | Moyen |
| Leaves | P3 | ViewSet, formulaires, calendrier | CRUD et calendrier | API v1, regles dates et droits | Non | Eleve |
| Calendar | P3 | Agregation multi-domaines/plugins | Calendrier React unifie | Ressources/events v1 performants | Non | Eleve |
| Organizations | P2 | UI et ViewSet generique | Liste/detail puis CRUD | Contrat v1 polymorphe | Non | Eleve |
| Notes | P2 | Notes par ContentType | Composant reutilisable | Endpoint v1 et droits objet | Non | Eleve |
| Favorites | P2 | ViewSet et AJAX | Favoris dans le shell | Endpoint idempotent et tests | Non | Moyen |
| Subscriptions | P3 | ViewSet, AJAX, taches email | Gestion React | API, droits et effets asynchrones | Non | Eleve |
| Notifications | P3 | App Django, exposition partielle | Centre de notifications | API dediee et etats de lecture | A evaluer | Eleve |
| Dashboard | P3 | Cartes Django et calculs | Dashboard React | Endpoints de synthese stables | Non | Eleve |
| Reports | P3 | Word/PDF et telechargements | Lancement/telechargement React | API, statut de tache et droits | Non | Eleve |
| Imports | P4 | Parcours Django | Peut rester en Django | API seulement si justifiee | Non | Eleve |
| Settings | P4 | API partielle et UI Django | Administration ulterieure | Clarifier portees et permissions | Non | Eleve |
| Plugins | P4 | Registre, settings, calendrier | Peut rester en Django | Stabiliser API plugin | Non | Eleve |
