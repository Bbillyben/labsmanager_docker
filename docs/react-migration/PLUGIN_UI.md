# Interfaces React des plugins (contrat v1)

## Déclarations et accès

`UIContributionMixin.UI_CONTRIBUTIONS` accepte les actions et sections historiques sans changement. Deux nouveaux types sont disponibles :

```python
{"id": "example-page", "slot": "plugin.page", "type": "page",
 "label": "Model Example", "module": "main", "component": "Page", "api_version": 1}
{"id": "employee-tab", "slot": "employee.detail.tabs", "type": "tab",
 "label": "Model Example", "module": "main", "component": "EmployeeTab", "api_version": 1}
{"id": "team-tab", "slot": "team.detail.tabs", "type": "tab",
 "label": "Example", "module": "main", "component": "ContextTab", "api_version": 1,
 "visible": "has_context_data"}
{"id": "project-tab", "slot": "project.detail.tabs", "type": "tab",
 "label": "Example", "module": "main", "component": "ContextTab", "api_version": 1,
 "visible": "has_context_data"}
```

`id` est unique dans le plugin ; l'identité publique inclut son slug. `module` nomme une entrée du manifeste Vite, et `component` un export nommé de cette entrée. Les identifiants sont validés ; aucune URL JS externe ne peut être déclarée. Une méthode optionnelle `visible(request, context)` peut affiner la visibilité sans charger le module ni les données métier. Les contributions ne sont exposées que pour un plugin actif. L'API exige une session authentifiée ; chaque onglet résout l'objet Employee, Team ou Project avec son droit `view` avant de l'annoncer et avant chaque chargement direct. La page possède la route `/app/plugins/<slug>/<id>` et les onglets suivent `/app/<employees|teams|projects>/<id>/plugins/<slug>/<id>`. Les données métier et actions spécifiques restent dans des endpoints `UrlsMixin` protégés côté Django : une route React ou le JS public ne confèrent aucun droit.

L'API `/api/v1/ui-contributions/pages/` liste les pages autorisées pour la navigation depuis « Mes plugins ». Son détail et le détail de l'onglet renvoient les URLs JS/CSS résolues du manifeste et, pour l'onglet, `{entity: "employee" | "team" | "project", objectId: ...}`. La liste des contributions n'importe aucun module React ; l'ouverture de l'onglet charge son bundle. Les erreurs ou refus empêchent ce chargement. Le plugin doit recontrôler les droits dans ses propres API, même après une réponse `visible` positive. Les slots historiques continuent de fonctionner.

## Actions ouvrant un module React

Une action `UIContributionMixin` peut déclarer `behavior: "module"` avec `module`, `component`, `api_version: 1`, `handler` et éventuellement `visible`. Le cœur affiche l'action dans son emplacement habituel, puis résout son descripteur et charge ses assets seulement au clic. Le composant reçoit `context` et `onClose`; `context.actionUrl` est l'URL de l'action autorisée. Le module décide quand appeler cette URL en POST et présente lui-même son interface. Le GET recontrôle la visibilité et les droits d'accès, sans exécuter le handler ; le POST recontrôle les mêmes droits avant de l'exécuter. Le résultat du POST est une URL sûre ou un message court. Le cœur fournit les composants UI partagés via `@labsmanager/plugin-ui`, dont `Sheet`, `Button`, `Input`, `Alert` et `copyPluginToken`. Aucun jeton ne doit être créé ou renvoyé au simple chargement du module.

Le slot générique `published-calendar.actions` expose ces actions pour un calendrier publié par un fournisseur actif. Son API `/api/v1/ui-contributions/published-calendar/<provider_slug>/<calendar_id>/` renvoie les actions visibles ; le détail `/.../<identity>/` donne au module `providerSlug`, `calendarId`, `name`, `options` et `actionUrl`. Le cœur résout le calendrier avec les permissions existantes avant la liste, le GET de détail et le POST. Le fournisseur publie ses options de consultation ; il n'a pas à connaître le plugin qui fournit l'action. Voir [PLUGIN_CALENDAR_PUBLICATION.md](PLUGIN_CALENDAR_PUBLICATION.md) pour le contrat des fournisseurs et [UI_CONTRIBUTIONS.md](UI_CONTRIBUTIONS.md) pour les autres slots d'action.

Une page peut aussi être proposée dans la navigation des calendriers en ajoutant à sa déclaration `plugin.page` :

```python
"navigation": {"location": "calendars", "labels": {"fr": "Agenda", "en": "Calendar"},
               "icon": "calendar", "order": 0}
```

`navigation` est facultatif et réservé aux pages. `calendars` est le seul emplacement admis actuellement. Les libellés `fr` et `en` sont facultatifs et reviennent à `label` lorsqu'ils manquent ; ils doivent être non vides et limités à 150 caractères. L'icône facultative appartient à la liste autorisée par le registre UI. L'ordre est un entier entre -1000 et 1000 ; à égalité, l'identité de la contribution départage les entrées. Une URL ou route arbitraire est refusée : la cible provient du slug et de l'identifiant de cette même page. L'entrée n'apparaît que si le plugin est actif et sa page visible pour l'utilisateur. L'accès direct revalide cette visibilité ; les API métier conservent leurs propres droits. La découverte de navigation ne résout ni ne charge les ressources JS/CSS du plugin. Les pages historiques sans `navigation` restent inchangées.

## API publique et runtime partagé

Le contrat `PLUGIN_UI_API_VERSION = 1` est publié par `frontend/src/plugin-api.ts`. Il expose les composants déclarés par ce fichier, notamment `EntitySearch`, les sources de recherche, `Button`, `EntityActionMenu`, `copyPluginToken`, `useTranslation` et `apiRequest`. Le menu d'actions partagé permet aux modules externes de reprendre les menus de ligne du cœur. `copyPluginToken` fournit la copie avec repli pour les URL personnelles d'abonnement. Le plugin reçoit le contexte du fournisseur i18n et des autres contextes React de la SPA ; ses appels restent authentifiés et soumis aux permissions de l'API correspondante.

### Traductions propres aux modules React

`@labsmanager/plugin-ui` expose `registerPluginTranslations(namespace, { fr, en })` et `usePluginTranslation(namespace)`. Le namespace est le slug stable du plugin, en minuscules ; chaque clé reste locale au dictionnaire du plugin. Déposer les JSON dans `frontend/src/locales/fr.json` et `en.json` du plugin, puis les importer dans son module React. Vite les inclut dans le bundle différé : aucun endpoint, fichier de langue du cœur ou chargement initial de tous les plugins n'est nécessaire.

```tsx
import { Button, registerPluginTranslations, usePluginTranslation } from '@labsmanager/plugin-ui'
import fr from './locales/fr.json'
import en from './locales/en.json'

registerPluginTranslations('example', { fr, en })

export function Page() {
  const { t, language } = usePluginTranslation('example')
  return <Button>{t('createEvent', { name: 'Ada' })}</Button>
}
```

Le hook utilise la même langue et le même contexte React que `useTranslation` du cœur ; il suit un changement de préférence linguistique du navigateur via l'événement `languagechange`, sans rechargement de la SPA. Le cœur prend actuellement en charge `fr` et `en`, avec `fr` par défaut. Une clé absente dans la langue active se replie sur `fr`, puis `en` ; si elle manque partout, le texte affiché est `namespace.key`. L'interpolation `{name}` suit celle du cœur. Pour ajouter une langue au produit, étendre d'abord le contrat linguistique du cœur, puis ajouter son JSON aux plugins concernés ; les dictionnaires incomplets restent acceptés.

Les dictionnaires des plugins sont séparés de celui du cœur : un slug comme `calendars` peut coexister avec les clés `calendars.*` du cœur. Un second enregistrement identique ne fait rien ; un enregistrement différent sous le même slug est refusé. Un plugin sans dictionnaire continue à fonctionner. Les traductions enregistrées peuvent rester en mémoire après désactivation, mais seules les contributions actives sont affichées. Construire le frontend du cœur avant les bundles qui utilisent ces nouveaux exports, puis exécuter le build indépendant de chaque plugin et publier ses `frontend/dist` par le processus statique habituel.

Le build hôte fournit trois entrées ES de base : `plugin-react.js`, `plugin-jsx-runtime.js` et `plugin-api.js`. Une import map dans `index.html` mappe `react`, `react/jsx-runtime` et `@labsmanager/plugin-ui` vers **les mêmes URLs** que celles utilisées par la SPA. En développement Vite, elle pointe vers les modules source hôtes sous la `base` résolue par Vite (par exemple `/app/src/plugin-react.ts`) ; les chemins restent absolus même sur une route React imbriquée. Les entrées proviennent du **même build Vite** que la SPA : leurs imports internes partagent les mêmes modules React et contextes. Elles sont servies par nginx avec une politique HTTP de revalidation ; elles ne portent pas de paramètre de version, qui créerait une deuxième instance du module dans un même document. Le build indépendant du plugin traite ces noms comme des dépendances externes. Il ne doit ni inclure React dans son bundle, ni importer des chemins internes du cœur. Une montée de version incompatible du contrat nécessite une nouvelle version du cœur et du plugin.

Calendars V1 a ajouté l'entrée publique `@labsmanager/plugin-calendar` → `plugin-calendar.js`, qui expose FullCalendar, ses plugins mois/semaine/jour, son thème et les locales FR/EN aux autres plugins. La SPA utilise déjà FullCalendar : Vite peut précharger cette entrée partagée dès le démarrage. Le **bundle propre à Calendars** reste chargé seulement lors de l'ouverture de sa page ; depuis V1.8, le composant partagé du cœur fournit aussi les styles FullCalendar nécessaires à ses vues. `@labsmanager/plugin-ui` expose `Alert`, `ConfirmDialog` et les composants `Sheet` déjà présents dans le cœur. Ces exports restent spécifiques aux interfaces de plugins, sans exposer l'ensemble du frontend. Voir le README du plugin Calendars actif pour son API et son déploiement.

### Présentation calendaire réutilisable

`@labsmanager/plugin-ui` exporte `PluginCalendarView` et ses types `PluginCalendarEvent`, `PluginCalendarResource`, `PluginCalendarRange` et `PluginCalendarMode`. Le composant utilise les définitions natives de `projectCalendarScopes.ts` : `fifteenDays`, `month`, `twoMonths`, `year`. Pour chaque période, un plugin peut proposer `calendar` et `list` ; `resources` est annoncé par `allowResources` lorsqu'il dispose de lignes métier. L'interface garde sa date de référence et sa période en changeant de mode. `onRangeChange` fournit les bornes `[start, end)` à charger ; `onEventClick` et `onDateSelect` laissent au plugin ses propres formulaires et droits. Les événements sont passés comme DTO de présentation, avec couleur, nom de calendrier, type et noms visibles des employés. Les IDs de ressources sont des chaînes locales à la vue, sans nouveau modèle Django.

La vue liste utilise le module `@fullcalendar/react/list` déjà présent dans la dépendance FullCalendar du cœur. La vue ressources utilise le Resource Timeline déjà installé. Les événements sans ligne Employee visible sont regroupés sur une unique ligne virtuelle « Sans ligne employé » ; les calendriers simples restent ainsi visibles en affichage mixte. Les affectations multiples utilisent plusieurs `resourceIds` pour un seul événement. `PluginCalendarView` passe la vue active, la période, les événements et les lignes visibles au `PrintProvider` existant via le renderer `plugin-calendar` ; l'impression n'interroge pas à nouveau le backend. Les vues natives et leur renderer `calendar` restent inchangés. Le plugin fournit uniquement des données déjà autorisées ; les contrôles métier demeurent dans son API.

## Build et distribution de ModelExample

`data/plugins/ModelExample/frontend/` contient les sources, `package.json`, la configuration Vite et le dossier compilé `dist/`. Sur une machine de développement avec Node 24 :

```bash
cd data/plugins/ModelExample/frontend
npm install
npm run build
```

Distribuer `ModelExample.py`, `frontend/dist/manifest.json` et **tous** les fichiers de `frontend/dist/assets/` avec le plugin. Aucun `node_modules` ni source TypeScript n'est requis en production. L'exemple distribue ses fichiers précompilés ; il n'est pas copié dans l'image Docker du cœur. Le manifeste contient les noms hachés. Le backend n'accepte que des fichiers locaux `assets/*.js` et `assets/*.css` et renvoie des URLs `/static/plugins/modelexample/...` avec une version dérivée du manifeste. Le navigateur n'importe le JS qu'à la première ouverture de la page ou de l'onglet, charge le CSS correspondant et réutilise le module ensuite. Après mise à jour, un nouveau nom haché et la version de manifeste invalident le cache. Les fichiers statiques sont publics : ne jamais y placer de secret ou de donnée personnelle.

`STATICFILES_DIRS` découvre les `frontend/dist/` des plugins de répertoire, même ceux sans `ModelMixin`. Après installation ou remplacement des fichiers sur l'hôte, redémarrer les processus Django pour actualiser les déclarations et la liste des sources statiques. En Docker, copier le package dans `<LAB_EXT_VOLUME>/plugins/ModelExample/`, puis exécuter `docker compose run --rm --no-deps --entrypoint python3 lab-server /home/labsmanager/labsmanager/manage.py collectstatic --noinput` avec la même image, configuration et volumes que les services. Recréer ou redémarrer serveur et worker ; le serveur relance aussi `collectstatic` à son démarrage normal. Nul besoin de reconstruire l'image pour installer ou mettre à jour les fichiers du plugin **après** déploiement d'un cœur P2 compatible. Activer ensuite le plugin avec l'administration existante. Le contrôle des migrations de P1 demeure inchangé.

En bare metal avec Vite, `vite.config.ts` relaie `/static/plugins/` vers Django. Django doit servir ces fichiers via ses finders en mode développement, ou un serveur statique doit servir le résultat de `collectstatic` sous `/static/`. Vérifier `/api/v1/ui-contributions/pages/`, puis la route de la page et l'onglet d'un Employee visible. En production, nginx sert directement `STATIC_ROOT/plugins/` via son alias `/static/`. Le bundle du plugin n'est pas chargé par les autres pages ; la liste légère des pages n'est demandée qu'à l'ouverture de « Mes plugins ».
