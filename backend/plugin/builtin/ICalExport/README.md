# ICalExport — sample d’abonnement iCalendar

Ce sample officiel fournit des flux `.ics` personnels en lecture seule. Sa présence dans `plugin/samples` permet la découverte standard ; elle **ne l’active pas**. Le code n’a aucun chemin particulier lié aux samples et peut être déplacé parmi les plugins externes ou builtin.

## Installation et activation

Installer la dépendance déclarée dans [`requirements.txt`](requirements.txt) depuis la fiche administrative du plugin, puis redémarrer les processus Django. Le [gestionnaire central](../../../../docs/react-migration/PLUGIN_DEPENDENCIES.md) stocke le package dans un dépôt persistant sans modifier l’environnement Python principal.

Activer ensuite **ICalExport** depuis l’administration des plugins. Les contributions de l’interface utilisent `UIContributionMixin` ; les flux exigent `UrlsMixin` et le réglage global `ENABLE_PLUGINS_URL`. La désactivation du plugin coupe immédiatement les flux. Aucun abonnement n’est créé lors de l’activation.

## Création des abonnements

Après activation, ouvrir **Mes plugins → iCalendar Export** pour les deux abonnements généraux. Les menus d’action du calendrier courant et des fiches Project, Employee et Team proposent les abonnements contextuels. L’action `copy_url` de React crée un nouveau token personnel, copie l’URL et l’affiche pour permettre une copie manuelle, y compris si la copie automatique échoue. Le secret complet n’est renvoyé que lors de cette action. Conserver l’URL dans le client de calendrier : elle fait office de mot de passe.

Un token est créé par abonnement via `TokenMixin`, avec le scope `ics`. Sa partie secrète est hachée en base. La signature de l’URL lie son identifiant public au type de calendrier et à l’objet ; modifier le chemin ne change pas le périmètre du token. À chaque lecture, le token, l’utilisateur actif, le plugin actif et les droits sur les données sont recontrôlés. Révoquer un abonnement depuis la gestion existante des tokens personnels dans **Mes plugins**. Les réponses contenant une URL secrète et les flux portent `Cache-Control: no-store`. Configurer le serveur HTTP et le proxy pour ne pas journaliser les paramètres de requête de `/plugin/icalexport/ics/`.

L’adaptation du cœur se limite à `Cache-Control: no-store` sur les réponses d’actions `UIContributionMixin`. Le composant React commun affiche aussi l’URL renvoyée par `copy_url` pendant la session courante, pour permettre la copie manuelle après une copie automatique. Aucun modèle ou contrat de calendrier n’est ajouté.

## Périmètres disponibles

| Flux | Source réutilisée |
| --- | --- |
| Planning général | `GlobalProjectPlanning` : jalons et périodes sérialisés, événements des plugins |
| Absences générales | `GlobalEmployeeCalendar` : absences visibles, événements des plugins |
| Projet | `ProjectPlanningV1View` et `ProjectCalendarV1View` |
| Projets d’un employé | `EmployeeProjectParticipationV1View`, projets individuellement visibles, puis vues Planning et événements Project |
| Absences d’un employé | `EmployeeCalendarV1View` |
| Projets d’une équipe | `TeamProjectsV1View`, puis vues Planning et événements Project |
| Absences d’une équipe | `TeamCalendarV1View` |

Le sample reprend les résultats des API de lecture autorisées. Ces vues utilisent les requêtes métier existantes et `CalendarService` avec `CalendarContext` et `LabsManagerCalendarEvent`. Aucun modèle d’un autre plugin n’est importé. Les événements qui déclarent un identifiant d’objet étranger au contexte demandé sont écartés. Les jalons ponctuels sont exportés le jour de leur échéance ; les tâches conservent leur période. La bibliothèque `icalendar` gère l’échappement et le repliement des lignes RFC 5545.

Pour les événements Calendar normalisés, l'export transmet `CalendarContext.consumer="ical"` et demande `include_details=True` aux vues autorisées. `SUMMARY` utilise `metadata["detailed_title"]` lorsqu'il est fourni et non vide, sinon le `title` habituel. Les absences peuvent ainsi afficher « Marie Dupont - Congé » lorsque le propriétaire du flux est autorisé à consulter l'Employee. Les événements des autres plugins peuvent suivre la même convention sans logique spécifique dans ICalExport. Les items Planning/Gantt gardent leur conversion actuelle.

## Limites

Chaque lecture couvre les deux années civiles précédentes et les cinq années civiles suivantes. Cette borne protège les fournisseurs de plugins dont les événements sont calculés à la demande. Les abonnements se mettent à jour lors de la prochaine récupération par le client. Les calendriers « projets d’un employé » et « projets d’une équipe » consultent chaque projet visible séparément ; le coût augmente avec le nombre de projets. Les événements d’absence sont exclus de ces deux flux projets, puisqu’ils disposent de flux absences distincts. Les filtres interactifs de React ne sont pas mémorisés dans l’URL d’abonnement.

## Validation

```sh
python3 backend/manage.py test plugin.test_icalexport
```

Dans React, activer le plugin, créer chacun des abonnements proposés, coller l’URL dans un client iCalendar, puis révoquer le token correspondant et confirmer que la lecture échoue. Vérifier également qu’un autre utilisateur n’obtient pas les projets ou employés non autorisés.
Les tests du sample sont ignorés si la dépendance optionnelle n’est pas installée ; ils s’exécutent après installation.
