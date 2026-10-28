# Contributions React des plugins

`UIContributionMixin` ajoute des actions et des sections déclaratives aux fiches React, des actions aux barres d'outils Calendar et aux pages personnelles des plugins, ainsi que des modules React chargés à la demande. Il fonctionne seul, sans `UrlsMixin`, `SettingsMixin` ou `TokenMixin`. Il utilise le registre de plugins existant : seules les instances actives qui portent le mixin sont consultées. La découverte des contributions ne charge aucun JavaScript de plugin.

## Slots et identité

Les slots de fiche sont `project.detail.actions`, `project.detail.sections`, `employee.detail.actions`, `employee.detail.sections`, `team.detail.actions` et `team.detail.sections`. Trois slots d'action s'y ajoutent : `calendar.toolbar.actions`, `published-calendar.actions` et `user.plugin.settings.actions`. `user.plugin.settings.panels` accueille un module React dans les paramètres personnels d'un plugin. Le catalogue central `plugin/ui_contributions.py:SLOTS` associe chaque slot à une entité et à un type ; les résolveurs autorisent ensuite le contexte propre à l'écran. Les contributions sont ordonnées par `priority` croissante (défaut 0), puis slug et id local. Plusieurs plugins peuvent contribuer au même slot. L'id local est unique dans un plugin ; son identité API globale est `plugin:<slug>:<id>`.

Pour ouvrir un nouveau slot, ajouter sa déclaration à `SLOTS` avec le résolveur de contexte existant ou une fonction de résolution de la nouvelle entité, puis monter `PluginContributionsProvider`, `PluginEntityActions` et/ou `PluginContributionSections` dans la page React concernée. `UIContributionMixin` ne change pas.

Le slot générique `published-calendar.actions` résout le fournisseur et le calendrier publiés avec le contrat `PublishedCalendarMixin` et revalide le droit `view` à chaque demande. Un fournisseur React peut afficher les actions disponibles avec `PluginPublishedCalendarActions` sans importer le module du consommateur.

Les modules React chargés à la demande peuvent embarquer leurs propres dictionnaires FR/EN dans leur bundle et les enregistrer via `registerPluginTranslations(slug, { fr, en })` de `@labsmanager/plugin-ui`. Le hook `usePluginTranslation(slug)` lit la langue du contexte React du cœur et actualise les textes d'un module déjà ouvert lorsqu'elle change. Les traductions restent locales au plugin, sans modification des fichiers de langue du cœur ni chargement des autres plugins. Voir [PLUGIN_UI.md](PLUGIN_UI.md#traductions-propres-aux-modules-react) pour le contrat complet, les replis et l'exemple de build.

## Déclaration

```python
from plugin import LabManagerPlugin
from plugin.mixins import UIContributionMixin

class ExamplePlugin(UIContributionMixin, LabManagerPlugin):
    NAME = "ExamplePlugin"
    SLUG = "example"
    UI_CONTRIBUTIONS = [
        {"id": "project_link", "slot": "project.detail.actions", "type": "action",
         "label": "Copier le lien", "handler": "project_link",
         "behavior": "copy_url", "icon": "copy", "priority": 0},
        {"id": "project_facts", "slot": "project.detail.sections", "type": "section",
         "label": "Informations", "handler": "project_facts"},
    ]

    def project_link(self, request, context):
        return {"url": f"/app/projects/{context['project'].pk}"}

    def project_facts(self, request, context):
        return {"format": "properties", "items": [
            {"label": "Utilisateur", "value": request.user.username},
        ]}
```

Chaque contribution doit déclarer un id, un slot existant, son type et un libellé. Les actions et sections déclarent un **handler existant sur ce plugin** ; les pages et onglets React déclarent `module`, `component` et `api_version: 1`. Une action `behavior: "module"` déclare les deux : le module pour l'interface et le handler pour le POST. Les ids sont alphanumériques avec `_` ou `-`. `icon` est facultatif et limité aux icônes connues du cœur (`calendar`, `copy`, `external-link`, `link`, `info`, `play`). Une déclaration invalide est ignorée et journalisée sans supprimer les contributions valides des autres plugins.

Une déclaration peut préciser `visible`, nom d'une méthode `visible(self, request, context) -> bool`. Elle est appelée lors de la découverte **et à chaque accès direct** à l'action ou à la section. Sans elle, la visibilité de l'objet est le minimum appliqué. Les handlers reçoivent la requête authentifiée et un dictionnaire contenant l'objet ORM résolu (`project`, `employee` ou `team`), `slot` et `contribution` (`id` global, `plugin_slug`, `local_id`). Le client n'envoie que l'id de l'objet ; Django utilise `Project.get_instances_for_user('view', ...)`, `Employee.get_instances_for_user('view', ...)` ou `team_queryset`, comme les fiches existantes. L'objet absent ou non visible renvoie 404. Un plugin doit appliquer ses permissions supplémentaires dans `visible` et **dans son handler** lorsque l'opération est plus sensible que la consultation. L'identité du compte vient exclusivement de `request.user`.

Une action React peut déclarer `behavior: "module"`, un handler POST et les mêmes champs `module`, `component`, `api_version: 1` que les pages et onglets. Le GET de son URL détail revalide sa visibilité et ne renvoie les assets qu'à l'ouverture. Il transmet un contexte borné : objet de fiche (`entity`, `objectId`, `name`), calendrier natif (`calendarType`, `objectId`, `name`), calendrier publié (`providerSlug`, `calendarId`, `name`, `options`) ou page personnelle (`pluginKey`), ainsi que `actionUrl`. Le module appartient au plugin et reçoit `onClose` ; il peut utiliser `Sheet`, `Button`, `Input`, `Alert` et les autres composants de `@labsmanager/plugin-ui`. L'ouverture ne lance pas le handler ; le module déclenche le POST au moment choisi. Une erreur d'assets ou de chargement reste locale à cette action.

## Actions et sections

Une action déclare `behavior` : `copy_url`, `open_url`, `action` (défaut) ou `module`. Elle peut déclarer `confirm: True`, sauf avec `module`, qui ouvre directement son interface. Son handler est appelé seulement par `POST`, avec session et CSRF Django. Pour `copy_url` et `open_url`, il retourne `{"url": "https://…"}` ou un chemin interne `/…`. Les URL sont limitées aux schémas HTTP(S) ou aux chemins internes sûrs. Pour `action`, il retourne `{"message": "…"}` ; un message vide utilise le feedback générique. Pour `module`, il retourne une URL sûre ou un message court au composant plugin. React utilise le menu d'entité et le dialogue de confirmation existants. Une copie refusée par le navigateur laisse le lien sélectionnable ; une ouverture d'onglet bloquée laisse un lien cliquable.

Une section est chargée séparément pour ne pas bloquer la fiche ni les autres sections. Le handler retourne l'un des formats JSON bornés suivants :

- `{"format": "text", "text": "…"}` ;
- `{"format": "properties", "items": [{"label": "…", "value": "…"}]}` ;
- `{"format": "items", "items": [{"label": "…", "description": "…", "url": "/…"}]}` (`description` et `url` facultatifs) ;
- `{"format": "links", "items": [{"label": "…", "url": "/…"}]}`.

React rend les chaînes en texte et utilise les composants existants ; les balises HTML contenues dans une valeur ne sont pas interprétées. Une erreur de handler donne un 502 local à cette contribution, avec une option Réessayer. Un slot sans contribution n'occupe aucun espace.

## API et démonstration

- `GET /api/v1/ui-contributions/slots/` : catalogue des slots.
- `GET /api/v1/ui-contributions/<entity>/<object_id>/` : contributions visibles pour la fiche.
- `GET /api/v1/ui-contributions/<entity>/<object_id>/<identity>/` : contenu d'une section.
- `POST /api/v1/ui-contributions/<entity>/<object_id>/<identity>/` : exécution d'une action.
- `GET /api/v1/ui-contributions/calendar/<calendar_type>/<object_id>/` et `POST …/<identity>/` : actions de la barre d'outils Calendar.
- `GET /api/v1/ui-contributions/user-plugin/<plugin_key>/` et `POST …/<identity>/` : actions de la page personnelle du plugin propriétaire.
- `GET /api/v1/ui-contributions/user-plugin/<plugin_key>/panels/` et `GET …/panels/<panel_id>/` : modules React intégrés à « Mes plugins → <plugin> → Paramètres ». Le second endpoint vérifie à nouveau l'activation et la visibilité avant de transmettre les assets et `context.pluginKey`.

Le slot `user.plugin.settings.panels` déclare `type: "tab"` avec `module`, `component` et `api_version: 1`, selon le même contrat de chargement différé que les onglets de fiche. La fiche personnelle affiche ces modules avec `PluginModule`, sans route métier propre au plugin. `SettingsMixin` continue à servir les réglages scalaires déclarés ; ce slot héberge les interfaces de gestion plus riches. `@labsmanager/plugin-ui` expose aussi `EntityActionMenu` et ses types pour les menus de lignes des modules externes. Un déploiement utilisant ce slot doit publier le nouveau build du cœur avant celui du plugin.

## Actions Calendar et paramètres personnels

`calendar.toolbar.actions` utilise `type: "action"` et les mêmes `behavior` (`copy_url`, `open_url`, `action`, `module`) que les menus des fiches. Il est intégré aux calendriers Employee, Project, Team, général Employee (`main`) et Planning général Project (`project_all`). Les contextes globaux utilisent `object_id=0` ; les autres utilisent l'id de leur objet. Django vérifie la visibilité de cet objet avec le même résolveur que sa fiche. Le handler reçoit `request.user`, `context["calendar_context"]` (un `CalendarContext` avec `calendar_type`, `user` et l'id métier pertinent), `context["calendar_type"]`, `context["calendar_id"]`, et l'objet ORM `project`, `employee` ou `team` pour un calendrier lié. Le contexte de toolbar ne contient ni dates ni filtres : il décrit le calendrier affiché, pas un abonnement à l'état temporaire de l'interface. Pour les calendriers globaux, l'API Calendar existante est authentifiée ; le handler doit contrôler toute permission supplémentaire avant une action sensible.

`user.plugin.settings.actions` utilise également `type: "action"` ; `copy_url` est une valeur de **`behavior`**, et non de `type`. Il apparaît seulement sous `Settings → Mes plugins → [Plugin]`, dans une section absente si aucune action n'est disponible. Les plugins dotés uniquement d'actions sont aussi listés dans « Mes plugins ». Le backend résout le plugin actif par `plugin_key`, puis filtre les déclarations sur son **slug propriétaire** à la découverte et à l'exécution. Le handler reçoit `context["plugin"]`, `context["plugin_key"]`, `request.user` et l'identité de contribution ; une identité d'un autre plugin renvoie 404. Les préférences `USER_SETTINGS` et les tokens personnels restent dans leurs sections existantes.

Exemple de déclaration :

```python
{"id": "subscribe", "slot": "calendar.toolbar.actions", "type": "action",
 "behavior": "copy_url", "label": "Copier le lien d'abonnement", "handler": "subscription_url"}
{"id": "copy_general", "slot": "user.plugin.settings.actions", "type": "action",
 "behavior": "copy_url", "label": "Copier le calendrier général", "handler": "general_url"}
```

## Point d'entrée calendrier pour un futur export ICS

Le contrat commun hors React est `common.calendar.CalendarContext` (`CalendarType.MAIN`, `PROJECT_ALL`, `PROJECT`, `EMPLOYEE`, `TEAM`, notamment) et `LabsManagerCalendarEvent`. Celui-ci porte `id`, `title`, `start`, `end`, `source`, `kind`, `all_day`, `color`, `description`, `display`, `metadata` et fournit `as_dict()`. `CalendarService.get_events(context, core_events)` agrège les événements cœur et ceux des plugins actifs ; `get_plugin_events(context)` appelle `CalendarEventMixin.get_calendar_events(context)` avec isolation des erreurs, tandis que `filter_calendar_queryset` et `get_filters` orchestrent les filtres déclarés.

`CalendarContext.include_details` vaut `False` par défaut. Un consommateur peut le passer à `True` pour demander des informations de présentation supplémentaires, sans étendre le périmètre ni les permissions de `context.user`. Un fournisseur peut alors renseigner la convention facultative `metadata["detailed_title"]`. `event.title` reste le titre ordinaire ; les consommateurs qui souhaitent un titre explicite utilisent `detailed_title` lorsqu'il est non vide, sinon `title`. Les plugins existants restent compatibles sans modification. L'enrichissement doit rester conditionnel, respecter les droits de lecture et éviter les requêtes N+1.

`CalendarContext.consumer` vaut `"labsmanager"` par défaut pour les calendriers de l'application ; `ICalExport` transmet `"ical"`. Un fournisseur peut choisir les destinations de ses événements sans connaître les autres consommateurs, par exemple :

```python
@classmethod
def get_calendar_events(cls, context):
    if context.consumer != "labsmanager":
        return []
    return cls.get_events(context)
```

Ce choix est facultatif et ne modifie jamais les permissions ni le périmètre visible de `context.user`.

Par exemple, une absence garde `title="Congé"` et peut porter `metadata={"employee_id": 73, "detailed_title": "Marie Dupont - Congé"}` si l'identité de l'employée est visible. Dans un plugin, `get_calendar_events(cls, context)` peut produire ses événements habituels, puis, lorsque `context.include_details` est vrai, retourner des variantes dont les métadonnées contiennent un titre explicite propre au plugin. Cet exemple est illustratif : `LabsManagerCalendarEvent` est une dataclass gelée et `metadata` est typé comme un `Mapping` ; utiliser `dataclasses.replace(event, metadata={**event.metadata, "detailed_title": titre})` plutôt que modifier l'événement ou supposer ses métadonnées mutables.

Les vues Calendar v1 bornent d'abord Project, Employee ou Team avec les permissions existantes, puis `leave.calendar.produce_leave_calendar_events` crée les événements Leave normalisés et `CalendarService` ajoute ceux des plugins. Le calendrier global Employee borne les Employees visibles, applique les filtres et retire les événements plugin rattachés à un Employee non visible. Le Planning global Project utilise aussi les Projects visibles mais ses Tasks/Milestones sont des **items Gantt**, distincts des `LabsManagerCalendarEvent` des plugins. Les endpoints React renvoient les événements normalisés ; `SharedCalendar` les adapte ensuite à FullCalendar. La façade legacy traduit la requête en `CalendarContext` et utilise le même service.

Pour un futur `ICalExport`, la base recommandée est cette orchestration Django des vues Calendar et de `CalendarService`, avec une extraction minimale de leurs parties communes si l'export exige un appel hors HTTP. L'exporteur peut sérialiser les `LabsManagerCalendarEvent` autorisés sans interroger chaque modèle plugin. `CalendarService` seul ne produit pas les Leave ni les items Gantt du Planning global ; ces éléments demandent respectivement le producteur Leave existant et une décision de conversion des items Planning. `UrlsMixin` peut exposer un endpoint propre au plugin ; `TokenMixin` fournit une validation explicite des tokens, sans authentification implicite de l'endpoint. Un flux d'abonnement devra donc associer de façon sûre son token à un utilisateur et à un périmètre ; l'authentification de l'action qui copie une URL ne suffit pas à autoriser les lectures ultérieures du flux. Aucun de ces mécanismes d'export n'est ajouté dans ce lot.

Le plugin externe `TestUIContribution` installé dans `/home/labsmanager/data/plugins/TestUIContribution/` fournit les six contributions de démonstration, avec son `README.md` de validation navigateur. Il n'est pas activé automatiquement. Sa désactivation retire les six contributions de l'API après rechargement du registre ; aucune donnée plugin n'est effacée.
