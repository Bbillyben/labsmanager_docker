# ICalExport — abonnement iCalendar intégré

Ce plugin intégré fournit des flux `.ics` personnels en lecture seule.

## Installation et activation

Installer la dépendance déclarée dans [`requirements.txt`](requirements.txt) depuis la fiche administrative du plugin, puis redémarrer les processus Django. Le [gestionnaire central](../../../../docs/react-migration/PLUGIN_DEPENDENCIES.md) stocke le package dans un dépôt persistant sans modifier l’environnement Python principal.

En tant que plugin intégré, **ICalExport** est activé automatiquement lorsque ses dépendances sont disponibles. Les contributions de l’interface utilisent `UIContributionMixin` ; les flux exigent `UrlsMixin` et le réglage global `ENABLE_PLUGINS_URL`. Aucun abonnement n’est créé lors de l’activation.

## Création des abonnements

Après activation, ouvrir **Mes plugins → iCalendar Export** pour les deux abonnements généraux. Les menus d’action du calendrier courant et des fiches Project, Employee et Team proposent les abonnements contextuels. L’action `copy_url` de React crée un nouveau token personnel, copie l’URL et l’affiche pour permettre une copie manuelle, y compris si la copie automatique échoue. Le secret complet n’est renvoyé que lors de cette action. Conserver l’URL dans le client de calendrier : elle fait office de mot de passe.

L’URL ICS utilise l’origine Django publique construite par `django_email_url()` : domaine du `Site` courant et protocole de `REACT_PUBLIC_URL` lorsque le domaine n’indique pas lui-même de protocole. Configurer ces valeurs avec l’adresse réellement accessible aux clients calendrier. En HTTPS derrière un proxy, ne pas utiliser l’adresse HTTP interne comme domaine du `Site`.

Un token est créé par abonnement via `TokenMixin`, avec le scope `ics`. Sa partie secrète est hachée en base. La signature de l’URL lie son identifiant public au type de calendrier et à l’objet ; modifier le chemin ne change pas le périmètre du token. À chaque lecture, le token, l’utilisateur actif, le plugin actif et les droits sur les données sont recontrôlés. Révoquer un abonnement depuis la gestion existante des tokens personnels dans **Mes plugins**. Les réponses contenant une URL secrète et les flux portent `Cache-Control: no-store`. Configurer le serveur HTTP et le proxy pour ne pas journaliser les paramètres de requête de `/plugin/icalexport/ics/`.

L’adaptation du cœur se limite à `Cache-Control: no-store` sur les réponses d’actions `UIContributionMixin`. Le composant React commun affiche aussi l’URL renvoyée par `copy_url` pendant la session courante, pour permettre la copie manuelle après une copie automatique. Aucun modèle ou contrat de calendrier n’est ajouté.

## Périmètres disponibles

| Flux | Source réutilisée |
| --- | --- |
| Planning général | `GlobalProjectPlanning` : jalons et périodes sérialisés, événements des plugins |
| Absences générales | `GlobalEmployeeCalendar` : absences visibles, événements des plugins |
| Projet | `ProjectPlanningV1View` et `ProjectCalendarV1View` |
| Projets d’un employé | `EmployeeMilestoneV1View` : **Assigned project tasks and milestones for the selected employee.** Événements des plugins via `EmployeeCalendarV1View` en contexte `employee-gantt` |
| Absences d’un employé | `EmployeeCalendarV1View` |
| Projets d’une équipe | **Assigned project tasks and milestones for members of the selected team.** Sélection groupée par `Milestones.employee` et `team_members()`, événements des plugins via `TeamCalendarV1View` |
| Absences d’une équipe | `TeamCalendarV1View` |

Le plugin reprend les résultats des API de lecture autorisées. Ces vues utilisent les requêtes métier existantes et `CalendarService` avec `CalendarContext` et `LabsManagerCalendarEvent`. Aucun modèle d’un autre plugin n’est importé. Les événements qui déclarent un identifiant d’objet étranger au contexte demandé sont écartés. Les jalons ponctuels sont exportés le jour de leur échéance ; les tâches conservent leur période. La bibliothèque `icalendar` gère l’échappement et le repliement des lignes RFC 5545.

Les trois flux Projects (`project`, `employee-projects`, `team-projects`) contiennent les tâches, jalons et événements complémentaires pertinents, mais excluent tout événement normalisé `kind="leave"`, qu’il provienne du cœur ou d’un plugin. Les flux Absences (`absences`, `employee-absences`, `team-absences`) conservent les absences.

Pour les événements Calendar normalisés, l'export transmet `CalendarContext.consumer="ical"` et demande `include_details=True` aux vues autorisées. `SUMMARY` utilise `metadata["detailed_title"]` lorsqu'il est fourni et non vide, sinon le `title` habituel. Les absences peuvent ainsi afficher « Marie Dupont - Congé » lorsque le propriétaire du flux est autorisé à consulter l'Employee. Les événements des autres plugins peuvent suivre la même convention sans logique spécifique dans ICalExport.

## Présentation des flux

Les propriétés ICS `NAME` et `X-WR-CALNAME` indiquent « LabsManager - Planning général », « LabsManager - Absences générales », ou « LabsManager - Projet/Projets/Absences : nom de l’objet » selon le flux. Le nom du projet, de l’employé ou de l’équipe est relu lors de chaque récupération ; un renommage ne nécessite pas de nouveau token. Certains clients conservent toutefois le nom d’abonnement défini localement même après un changement de `X-WR-CALNAME`.

Les tâches et jalons du Planning général et des flux Employee/Team Projects portent « Projet - Titre ». Le flux d’un projet conserve « Titre ». Team Projects ajoute entre parenthèses les membres affectés dont l’identité est visible, sans dupliquer l’événement. Les titres des événements fournis par les plugins conservent la convention `detailed_title` puis `title`.

Lorsque `REACT_PUBLIC_URL` désigne une adresse publique HTTP(S), les tâches et jalons ouvrent l’onglet React du projet (`projects/:id/tasks`) si le projet est consultable ; dans le contexte Employee Projects sans accès indépendant au projet, le lien ouvre l’onglet des projets de l’employé (`employees/:id/projects`). Les absences du cœur pointent vers l’onglet des absences de l’employé (`employees/:id/leaves`) seulement si sa fiche est consultable. Le lien est placé dans `DESCRIPTION` et `URL` en conservant la description existante. React ne propose pas de route indépendante vers une tâche, un jalon ou une absence ; les liens ouvrent donc l’onglet correspondant. Les événements des plugins n’ont pas de convention de lien utilisateur dans `CalendarEventMixin` : leur `admin_url` éventuelle n’est jamais exportée comme lien de détail.

## Limites

Chaque lecture couvre les deux années civiles précédentes et les cinq années civiles suivantes. Cette borne protège les fournisseurs de plugins dont les événements sont calculés à la demande. Les abonnements se mettent à jour lors de la prochaine récupération par le client. Les flux « projets d’un employé » et « projets d’une équipe » utilisent directement les tâches et jalons affectés, sans consulter les projets un par un. Le flux d’équipe conserve le contrôle de visibilité des projets du propriétaire du token. L’équipe comprend son leader et les relations `TeamMate`, conformément à `team_members()` ; cette définition inclut aussi les appartenances historiques. Les titres des éléments de l’équipe indiquent les membres affectés seulement lorsque leur identité est visible pour le propriétaire du token. Les événements complémentaires proviennent des contextes Employee Gantt et Team : chaque fournisseur doit respecter l’Employee ou l’équipe transmis dans le contexte. Les filtres interactifs de React ne sont pas mémorisés dans l’URL d’abonnement.

## Validation

```sh
python3 backend/manage.py test plugin.test_icalexport
```

Dans React, créer chacun des abonnements proposés, coller l’URL dans un client iCalendar, puis révoquer le token correspondant et confirmer que la lecture échoue. Vérifier également qu’un autre utilisateur n’obtient pas les projets ou employés non autorisés.
Les tests du plugin sont ignorés si la dépendance optionnelle n’est pas installée ; ils s’exécutent après installation.
