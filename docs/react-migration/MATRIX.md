# Matrice fonctionnelle de migration

États utilisés : **migré** signifie utilisable dans React ; **partiel** signifie qu'une partie du domaine est migrée ; **placeholder** signifie que la sous-route existe sans fonctionnalité métier ; **legacy** signifie que le parcours reste uniquement dans Django ; **différé** signifie qu'aucun lot actif ne le prend en charge.

| Fonction | Lot | État React actuel | Backend/API v1 | Suite prévue | BDD | Risque |
|---|---:|---|---|---|---|---|
| Authentification / utilisateur courant | AUTH1 / UX2.1 | Migré : session, login/logout, identité Employee et menu utilisateur | `/me/` et auth v1 en place | Workflows de compte spécialisés restent legacy | Non | Élevé |
| Shell / navigation globale / i18n | R0 / UX1 / UX2 | Migré | Capacités de navigation fournies par `/me/` | Intégration build production différée | Non | Moyen |
| Liste Employee | R1 / R1.1 / R2.11a | Migré en lecture seule ; Active=true visible par défaut et badge de statut partagé | Liste, recherche, tri, pagination, filtres Activité/Supérieur | Autres sources de filtres selon contrats futurs | Non | Moyen |
| Navigation locale Employee | R2.4a | Migrée : vraies sous-routes et header partagé | Aucun endpoint spécifique | Étendre panneau par panneau | Non | Faible |
| Employee Overview | R2 / R2.4a | Informations et indicateurs en lecture seule ; GenericInfo CRUD R2.7 validé | Détail dédié + collection GenericInfo avec capacités | R2.7 clôturé ; autres mutations différées | staff.0014 appliquée en développement | Moyen |
| Statuts Employee / historique | R2 | Migré en lecture seule | `statuses` en place | Mutations différées | Non | Faible |
| Hiérarchie Employee / historique | R2 | Migré en lecture seule | `hierarchy` en place | Mutations différées | Non | Moyen |
| Jalons et tâches Employee | R2.2 | Migré en lecture seule : groupes, progression et Sheet | `milestones` en place ; classification Django-side | Mutations différées | Non | Moyen |
| Participations Project de l'Employee | R2.4a | Migré en lecture seule dans Projets | `project-participations` en place | Navigation Project autonome différée | Non | Moyen |
| Charge projet temporelle | R2.3 | Migrée en lecture seule : timeline et composition | `project-workload` en place | Réutilisation possible dans d'autres domaines | Non | Moyen |
| Contracts Employee | R2.4b | Migré en lecture seule : groupes temporels, suivi RH, Institution, Sheet et dépenses synthétiques | Liste et détail v1 en place ; scope Employee puis Contract | Mutations différées | Non | Élevé |
| Contributions Employee | R2.5a | Migré en lecture seule dans Financement : timeline et groupes temporels | Liste contextuelle et profil de quotité v1 | Mutations différées | Non | Élevé |
| Congés Employee | R2.6a–R2.10 | CRUD validé fonctionnellement | `leaves` CRUD, capacités, catalogue types, `calendar` agrégé et filtres plugins | Sheet unique, sélection et manipulation Mois/Année, synthèse cinq ans sans sélection | Non | Élevé |
| Budget Employee | R2.5b | Migré en lecture seule dans Financement : montants, consommation et dépassement | Liste contextuelle v1 avec calculs financiers explicites | Mutations différées | Non | Élevé |
| Notes Employee | Futur | Placeholder | Aucun contrat du panneau | À cadrer | Non prévu | Moyen |
| Mutations Employee | Futur | Différées | Permissions objet et contrats d'écriture à stabiliser | Lot explicite avec confirmations | À évaluer | Élevé |
| Liste Project autonome | R2.11a | Liste/CRUD validés ; filtre Participant à sélection Employee ajouté ensuite | API v1 paginée, filtres, relations compactes, capacités et mutations | Route React de fiche transitoire ; contenu R2.11b | Non | Élevé |
| Détail Project autonome | R2.11b | Route React minimale sans fiche métier | Aucun contrat de détail fonctionnel R2.11b | Implémentation ultérieure de ProjectSingle | Non prévu | Élevé |
| Teams | Futur | Legacy | ViewSet historique | Stabiliser contrats et permissions | Non prévu | Moyen |
| Funds | Futur | Legacy | ViewSet historique | Consultation puis mutations par lots | Non prévu | Élevé |
| Organizations / Institutions | Futur | Legacy | Contrats autonomes à définir | Nécessaire avant toute navigation React | Non prévu | Élevé |
| Expenses hors synthèse Contract | Futur | Legacy | ViewSet historique | Domaine comptable à cadrer séparément | À évaluer | Élevé |
| Calendrier | R2.6a / R2.6a.1 | Partiel : Calendar Core partagé, adaptateur `EventInput` et FullCalendar Standard Employee ; calendriers globaux restent legacy | Événement/contexte/service stables ; façade `/calendar_plugin/` conservée | Étendre domaine par domaine | Non | Élevé |
| Plugins calendrier | R2.6a / R2.6a.2 | Événements et filtres normalisés ; FrenchHollidayPlugin migré avec zone dynamique | `get_calendar_events(context)`, `get_calendar_filters(context)` et contrat `LabsManagerCalendarFilter` via registre actif | Migrer chaque futur plugin sur ces contrats | Non | Moyen |
| Mutations GenericInfo | R2.7 | Migrées et validées : READ/CREATE/UPDATE/DELETE selon capacités | Collection enveloppée, POST/PATCH/DELETE et catalogue global types | R2.7 clôturé ; déploiement production ultérieur | staff.0014 appliquée et vérifiée en développement | Élevé |
| Gantt Employee | R2.8 | Validé manuellement et automatisé | Endpoints Employee existants + CalendarService `employee-gantt` | Liste/Gantt, SVAR OSS en lecture seule ; background Calendar non rendu | Non | Élevé |
| Gantt Project / global | Futur | Différé | APIs propres à créer au moment du besoin | ProjectGanttAdapter / GlobalGanttAdapter vers le même LabsManagerGantt | Non prévu | Élevé |
| Dépendances Task / Milestone | R2.9 | Validées fonctionnellement | `MilestoneDependency`, API v1, Sheet Employee et liens Gantt | Déclaratif, cycles contrôlés, temporalité informative, sans scheduling | `endpoints.0006` créée ; état d'application à confirmer par environnement | Élevé |
| Mutations Leave | R2.10 | Validées fonctionnellement | POST/PATCH/DELETE contextuels, capacités et Leave_Type | `change_employee`, chevauchement demi-journée, confirmation DELETE | Aucune | Élevé |
| Favoris / abonnements / notifications | Futur | Legacy | APIs historiques partielles | Lots dédiés | Non prévu | Moyen à élevé |
| Dashboard / rapports | Futur | Legacy | Calculs et génération Django | Contrats de synthèse et tâches | Non prévu | Élevé |
| Imports / réglages / plugins | Futur | Legacy ou différé | Parcours Django actuels | Peut rester dans Django tant qu'un besoin React n'est pas établi | À évaluer | Élevé |

Les fonctionnalités Employee restent en lecture seule sauf GenericInfo R2.7, dont les mutations dépendent des capacités contextuelles. Les références liées visibles dans ce contexte ne donnent pas automatiquement accès à une fiche autonome.
