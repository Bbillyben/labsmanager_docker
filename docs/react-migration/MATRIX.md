# Matrice fonctionnelle de migration

Legende risque : faible, moyen, eleve. `BDD : non` signifie qu'aucune modification de schema n'est attendue a ce stade.

| Fonction | Priorite | Etat actuel | Cible React | Travail backend necessaire | BDD | Risque |
|---|---:|---|---|---|---|---|
| Authentication / current user | P0 | Allauth, sessions et API users existantes | Session/CSRF et utilisateur courant | Contrat `/api/v1/` et tests auth | Non | Eleve |
| Permissions | P0 | Django, rules, mixins et DRF heterogenes | UI guidee, backend autoritaire | Matrice de droits et tests par role | Non | Eleve |
| Employee list | P1 | Vue Django et ViewSet | Liste en lecture seule | Serializer v1 minimal, filtres, pagination | Non | Moyen |
| Employee detail | P1 | Fiche Django et actions DRF | Fiche en lecture seule | Endpoint v1 explicite et droits | Non | Moyen |
| Teams | P2 | UI Django et ViewSet | Liste/detail puis edition | Stabiliser serializers et permissions | Non | Moyen |
| Project list | P2 | UI Django et ViewSet | Liste en lecture seule | Contrat v1, filtres et pagination | Non | Moyen |
| Project detail | P2 | Fiche Django multi-domaines | Fiche React progressive | Endpoint compose ou appels bornes | Non | Eleve |
| Participants | P2 | Modeles et sous-actions | Consultation puis CRUD | Endpoints v1 et validation metier | Non | Eleve |
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
