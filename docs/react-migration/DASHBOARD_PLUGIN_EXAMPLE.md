# Exemple de contribution Dashboard : FrenchHollidayPlugin

`FrenchHollidayPlugin` est l'exemple concret du contrat plugin Dashboard. Sa déclaration vit dans
`backend/plugin/samples/FrenchHollidayPlugin/FrenchHollidayPlugin.py` ; le cœur Dashboard ne
connaît pas ce plugin.

Pour ajouter une source à un plugin tiers :

1. Hériter de `DashboardPluginMixin` avec les autres mixins du plugin. Le registre actif découvre alors `get_dashboard_sources(context)` et, si besoin, `get_dashboard_widgets(context)`.
2. Retourner une `DataSource` avec une `key` stable et préfixée par le plugin, `label`, `category`, `supported_scopes`, `compatible_renderers`, `default_renderer`, `config_fields` et un `provider(context, config)`. Pour une source utilisant un renderer core, le registre crée automatiquement une `WidgetDefinition` ; `get_dashboard_widgets` peut rester vide.
3. Déclarer seulement les contextes réellement acceptés. Ici `("user", "project")` ; le Project arrive via `DashboardContext.context_object`, sans connaissance du stockage ORM. Une source globale peut l'ignorer. L'API résout déjà la visibilité du contexte Project.
4. Garder le provider en lecture seule et rapide. Ici il lit les fichiers JSON déjà utilisés par le calendrier, respecte `FHP_VACATION_ZONE`, puis retourne `{"__renderers__": {"kpi": {...}, "compact-list": {"items": [...]}}}`. Il ne déclenche ni `FHP_pull()` ni écriture. Les clés `horizon_days` (1–365, défaut 180) et `limit` (1–12, défaut 5) sont validées par l'API Dashboard.
5. Réutiliser les renderers core avant d'envisager un renderer React local. Les modes normal, présentation et impression utilisent ici les mêmes composants. Les labels statiques passent par gettext ; les noms des jours proviennent des données du plugin.

Le registre ne retourne que les plugins actifs. Si ce plugin est désactivé ou absent, ses sources disparaissent du catalogue ; les instances enregistrées montrent le placeholder « définition indisponible » et restent supprimables. Le plugin ne doit pas implémenter ce cas lui-même.
