# État de la migration React

## État courant

LabsManager conserve Django comme backend et l'interface historique pendant la migration progressive. La SPA React/TypeScript est montée sous `/app/`, utilise les sessions Django et le cookie CSRF, et appelle les contrats stables sous `/api/v1/`. Le backend reste l'autorité pour les permissions et les périmètres objet.

Les fondations R0, UX1, AUTH1, R1, R1.1, UX2 et UX2.1 sont en place. La liste Employee est utilisable avec recherche, tri, pagination, sélection de ligne et filtres déclaratifs Activité/Supérieur. La topbar contextualisée, l'identité Employee retournée par `/api/v1/me/`, le menu utilisateur et l'i18n navigateur français/anglais sont également en place.

R0, UX1 et AUTH1 ont été validés techniquement et dans le navigateur. R1 a reçu un retour fonctionnel positif sur la VM, R1.1 a été validé fonctionnellement, et UX2/UX2.1 sont validés. Le code de R2 à R2.5b et ses validations ciblées sont présents ; ce document ne revendique pas une validation navigateur globale supplémentaire qui n'aurait pas été consignée.

La fiche Employee React est désormais structurée par une navigation locale et de vraies sous-routes. Le contexte et l'en-tête Employee sont communs ; chaque panneau charge uniquement ses données métier lorsqu'il est affiché.

| Route | État fonctionnel |
|---|---|
| `/app/employees/:id` | Vue d’ensemble migrée ; GenericInfo CRUD R2.7 terminé et validé |
| `/app/employees/:id/projects` | Projets migrés en lecture seule |
| `/app/employees/:id/contracts` | Contrats migrés en lecture seule |
| `/app/employees/:id/funding` | Contributions et Budgets affectés migrés en lecture seule |
| `/app/employees/:id/leaves` | Absences : calendrier et tableau, CRUD R2.10 validé fonctionnellement |
| `/app/projects` | Liste Project R2.11a validée ; filtre Participant par recherche Employee ajouté ensuite |
| `/app/projects/:id` | Route React transitoire minimale ; fiche métier différée à R2.11b |
| `/app/employees/:id/notes` | Placeholder |

## Employee migré progressivement

### Vue d'ensemble

La Vue d'ensemble contient directement la section fonctionnelle **Informations générales**, sans répéter le titre « Vue d'ensemble » et sans collapse inutile. Elle réunit :

- identité, dates, email et `GenericInfo` dynamiques ;
- indicateurs calculés côté Django : quotités contrat, projet et contribution, et nombre de jalons actifs ;
- statuts courants et historique ;
- hiérarchie directe courante et historique ;
- copie accessible des valeurs via `CopyableValue` ;
- liens vers une fiche Employee seulement lorsque cette ressource est consultable indépendamment.

Les chargements et erreurs des sous-ressources restent locaux. Le détail principal distingue notamment ressource absente, accès interdit et erreur réessayable. R2.7 expose uniquement les mutations GenericInfo, sans édition globale de l’Employee.

### Projets

Le panneau Projets contient deux grandes sections internes persistantes : **Jalons et tâches** et **Participations projets**. Elles utilisent `PersistentCollapsibleSection`, avec une clé `localStorage` stable par type de section, commune à tous les Employee, un état ouvert à la première utilisation et toute la ligne de titre comme déclencheur accessible.

Le tracker Jalons et tâches est alimenté par `GET /api/v1/employees/<id>/milestones/`. La classification est calculée par Django pour l'utilisateur courant, dans l'ordre completed, overdue, due soon, planned, in progress. Le seuil « échéance proche » vient de `NOTIFICATION_ENDPOINTS_MILESTONES_STALE` via `LMUserSetting`. L'interface groupe les éléments en En retard, Échéance proche, En cours, Planifiés et Terminés ; le groupe Terminés est replié initialement. `MilestoneDetailSheet` affiche le détail dans un panneau latéral.

Les règles de représentation sont conservées : `start_date is None` désigne un jalon, une date de début désigne une tâche/activité ; `type="q"` affiche `quotity` comme progression, tandis que `type="o"` n'affiche aucune progression chiffrée.

Les participations sont fournies par `GET /api/v1/employees/<id>/project-participations/`. Le profil de charge est fourni par `GET /api/v1/employees/<id>/project-workload/` et calculé depuis les dates et quotités des relations `Participant`, jamais depuis les dates des Project. Le backend construit des segments aux changements de composition, agrège les participations qui se chevauchent pour un même Project et conserve les bornes ouvertes avec `range=all`.

`ProjectWorkloadTimeline` affiche un profil compact en escalier, le seuil de 100 %, la surcharge au-delà de 100 % et la composition par Project via des interactions accessibles. Les fenêtres disponibles sont un an par défaut (aujourd'hui −3 mois / +9 mois), cinq ans (−1 an / +4 ans) et Tout sur requête explicite. Les fenêtres bornées se déplacent de six mois et peuvent revenir à Aujourd'hui ; le mode Tout n'est pas navigable.

La visibilité des jalons, collaborateurs et participations Project est contextuelle à l'Employee visible. Elle permet de comprendre les relations sans accorder un droit autonome sur les ressources liées. Un lien n'est présenté que si le droit indépendant et une route réelle existent ; aucune fausse navigation Project n'est créée.

### Contrats

R2.4b remplace le placeholder Contracts par une vue synthétique en lecture seule. Les contrats visibles sont classés côté Django en contrats en cours, à venir et historique selon leurs seules dates. `Contract.is_active` est exposé sous le nom explicite `requires_follow_up` et produit uniquement l'indicateur discret **Suivi RH**.

Chaque ligne présente le type, le Fund, le Project, l'Institution gestionnaire, la période, la quotité et le statut Effectif/Prévisionnel. L'historique est replié localement. L'Institution utilise le parcours Django Organization réel uniquement avec `common.display_infos`.

`ContractDetailSheet` charge le détail et les `Contract_expense` seulement à l'ouverture. Il affiche les relations utiles, le total brut, le nombre et une liste synthétique des dépenses. `Expense.status` n'est ni exposé ni utilisé ; aucune mensualisation, projection, timeline ou analyse comptable n'est introduite.

### Financement

R2.5 remplace les anciens placeholders Contributions et Budget par la route commune `/funding`. La première section affiche les Contributions de l'Employee en cours, futures et historiques, avec Fund, Project, type de coût, description, période, quotité et montant. Les types RH incluent les descendants d'un `Cost_Type.is_hr=True`.

Le profil temporel additionne les `Contribution.quotity` actives à chaque période depuis leurs propres bornes, sans utiliser les dates du Fund ou du Project. Il reprend les fenêtres, la navigation, le seuil 100 %, la surcharge et les interactions accessibles du profil Project.

La seconde section affiche les Budget items explicitement affectés à l'Employee. Le backend fournit le montant budgété, la dépense nette signée, le disponible calculé par `amount-expense` et le ratio signé lorsqu'il est calculable. Une écriture négative augmente le disponible et reste affichée comme remboursement, sans barre positive trompeuse. L'interface conserve aussi le vrai taux au-delà de 100 %, signale sobrement un disponible négatif et n'affiche aucune barre lorsque le ratio n'est pas calculable. Les deux sections sont repliables avec une préférence persistée par type de section.

### Absences et Calendar Core

R2.6a remplace le placeholder Congés par une lecture Calendar/Tableau. Le calendrier propose les fenêtres Mois, Année et cinq ans, avec précédent, suivant et Aujourd'hui ; chaque requête `/calendar/` est bornée. R2.6a.1 utilise FullCalendar React Standard pour Mois et Année, et conserve le renderer synthétique seulement pour cinq ans. Le tableau `/leaves/` expose Type, Début, Fin, Durée et Commentaire. Les deux modes partagent le filtre de type et les bornes de période, et le mode choisi est persisté.

R2.6a.2 clôt ce périmètre read-only. Les plugins exposent maintenant leurs filtres normalisés depuis `/calendar/filters/`; React rend sans connaissance plugin les types select, checkbox, radio, texte et couleur. Le filtre dynamique de zone FrenchHolliday est transmis aux requêtes calendrier et reste sélectionné pendant la navigation temporelle. Depuis R2.10, l'Année utilise `dayGridYear` ; sa lisibilité sur mobile reste améliorable. La vue cinq ans masque les backgrounds, ajoute les dates et conserve l'ouverture accessible du même Sheet Leave.

Les demi-journées restent explicites à l'écran et dans le Sheet avec les libellés partagés Matin, Après-midi, À partir de midi, Jusqu'à midi et Midi → midi. Les événements de plugins sont transmis comme de vrais fonds FullCalendar et n'ouvrent pas le détail Leave. Les lignes du tableau et les événements Leave sont accessibles au clavier. Le producteur FrenchHolliday renvoie désormais les apostrophes brutes, sans double échappement HTML.

Le backend utilise désormais un Calendar Core commun. Le mixin plugin, `FrenchHollidayPlugin`, la façade historique `/calendar_plugin/` et l'API Employee délèguent au même `CalendarService` ; aucun second moteur d'agrégation n'est maintenu.

## Principe de structuration retenu par R2.4a

- Les sous-routes séparent les grands domaines Employee et portent l'URL, le refresh, l'historique navigateur et le panneau actif.
- Les collapsibles structurent l'intérieur d'un panneau qui contient plusieurs grandes sections, lorsque cela réduit réellement la navigation verticale.
- Un panneau avec une seule grande section ne reçoit pas un collapse artificiel.
- Le header et l'identité Employee restent communs à toutes les sous-routes.

## API Employee v1 disponible

- `GET /api/v1/employees/`
- `GET /api/v1/employees/<id>/`
- `GET/POST /api/v1/employees/<id>/generic-info/`
- `PATCH/DELETE /api/v1/employees/<id>/generic-info/<info_id>/`
- `GET /api/v1/generic-info-types/`
- `GET /api/v1/employees/<id>/statuses/`
- `GET /api/v1/employees/<id>/hierarchy/`
- `GET /api/v1/employees/<id>/milestones/`
- `GET /api/v1/employees/<id>/project-participations/`
- `GET /api/v1/employees/<id>/project-workload/`
- `GET /api/v1/employees/<id>/contracts/`
- `GET /api/v1/employees/<id>/contracts/<contract_id>/`
- `GET /api/v1/employees/<id>/contributions/`
- `GET /api/v1/employees/<id>/contribution-workload/`
- `GET /api/v1/employees/<id>/budgets/`
- `GET /api/v1/employees/<id>/leaves/`
- `GET /api/v1/employees/<id>/calendar/`
- `GET /api/v1/employees/<id>/calendar/filters/`

Ces contrats restent en lecture seule, sauf la collection GenericInfo désormais étendue par R2.7. La résolution de l'Employee cible reste bornée par `Employee.get_instances_for_user("view", ...)`; un objet absent ou hors périmètre produit le même `404`.

## Validation et prochaine étape

R2.6a est implémenté en lecture seule. La validation couvre 78 tests backend combinant toute l'API Employee, Calendar Core, plugin et façade historique ; 30 tests frontend ciblés ; ESLint ; TypeScript ; build Vite ; `manage.py check` et le contrôle de diff. Le build conserve l'avertissement existant sur le chunk JavaScript supérieur à 500 kB.

Le correctif R2.6a.1 ajoute 7 tests frontend ciblés couvrant l'adaptateur et le nouveau renderer, puis repasse ESLint, TypeScript et le build Vite. La suite backend combinée de 78 tests, incluant la régression d'apostrophe, ainsi que `manage.py check` réussissent également. La validation navigateur du rendu FullCalendar a été confirmée par l’utilisateur avec la clôture R2.6a.2.

R2.6a.2 ajoute 11 tests frontend ciblés pour les filtres génériques, les demi-journées et les renderers Calendar, et porte la suite backend Calendar/plugins/API Employee à 83 tests. ESLint, TypeScript, le build Vite et `manage.py check` réussissent ; le build conserve l'avertissement de chunk supérieur à 500 kB. La validation navigateur R2.6a.2 a été confirmée par l’utilisateur avant l’implémentation R2.7.

La roadmap de référence distingue R2.8 Gantt Employee en lecture seule, les futurs Gantt Project/global, R2.9 dépendances déclaratives Task/Milestone sans scheduling automatique et R2.10 mutations Leave. R2.6a.2 n'avait commencé aucun de ces lots.

## Éléments différés

- Création, modification, suppression et autres mutations Employee.
- Navigation Project autonome et migration du détail Project.
- Panneau Notes.
- Exposition de liens vers une ressource liée tant que son droit indépendant ou sa route React ne sont pas disponibles.
- Intégration du build React au déploiement Nginx/Docker, toujours distincte de la migration fonctionnelle Employee.


## R2.7 — GenericInfo et socle de mutation : terminé et validé

Implémentation CRUD validée : collection enveloppée et capacités contextuelles, catalogue
global des types existants, create et modification de valeur en Sheet, suppression confirmée,
erreurs DRF, verrou de soumission, actualisation locale depuis la réponse serveur et relecture.
Une relecture échouée est signalée séparément du succès de mutation et ne rejoue pas l’écriture.

La rule `change_partial_employee` étend le droit historique de modification à l’Employee lié
pour CREATE seulement. `change_employee` global/objet reste le droit UPDATE/DELETE ;
`common.self_edit` conserve donc les mutations complètes de sa propre fiche. Lecteurs sans
ces droits : aucun contrôle de mutation. Le type est immuable après création et l’Employee
est imposé par l’URL. Doublons de type et valeurs vides/nulles restent autorisés.

La migration staff.0014 convertit les icônes connues en identifiants Lucide. Les inconnues
sont conservées exactement ; CircleQuestionMark est le fallback React. Le legacy Employee
conserve ses textes sans rendu FAIcon ; Project conserve son comportement historique.
L’utilisateur confirme la migration `staff.0014` appliquée et vérifiée sur la base de
développement, ainsi que la validation navigateur React et du legacy Django après migration.
Les correspondances vérifiées sont : Badge, matricule Inserm et matricule CHU → Badge ;
ORCID → Contact ; HDR → Search ; CSS/BAP/CNU → Columns3 ; RPPS → Stethoscope.

La validation manuelle confirme les permissions, la création, la valeur vide, les doublons,
la modification, le type immuable, l’annulation/confirmation DELETE, les interactions
hover/clic/clavier et le responsive. **R2.7 est clôturé.** Le futur déploiement production
reste distinct de cette validation en développement.

Le contrôle global `makemigrations --check --dry-run` détecte des écarts préexistants dans
`endpoints.Milestones.start_date` et `project.Participant.employee`. Ces modèles n’ont pas
été modifiés par R2.7 ; aucune migration hors périmètre n’a été créée.

R2.8 est **validé manuellement** : Gantt Employee, switch Liste/Gantt, Calendar, filtres
CalendarEventMixin, ouverture du Sheet Task/Milestone et contrôles navigateur sont OK.
La fiche Project React, la vue globale, Notes et les mutations Leave restent hors périmètre.

### R2.8 — validation terminée

Le switch Liste/Gantt conserve les ressources métier Employee chargées et l'état des filtres
Calendar. Le Gantt regroupe participations, tâches et jalons par Project, réutilise le Sheet
des jalons/tâches, propose 6 mois/1 an/2 ans et suit le thème clair/sombre. Les événements
Calendar ordinaires sont rendus ; les événements de fond sont conservés côté API mais omis
du rendu SVAR OSS (pas de mécanisme public adapté à leurs plages et couleurs avec les
échelles actuelles). Aucun endpoint
métier Gantt ni migration BDD n'a été ajouté.

Tests ciblés : 8 tests API Employee Calendar et 5 tests FrenchHolliday réussis ; 2 fichiers
frontend / 17 tests réussis après correction du scénario de fermeture du Sheet. `manage.py
check`, TypeScript, ESLint et build ont réussi. Le build émet l'avertissement de taille de
chunk >500 kB. Les tests manuels sont globalement positifs ; l'interaction task/milestone
restait à corriger. Le correctif écoute maintenant l'action publique SVAR `select-task`
et transmet l'identité métier au Sheet existant. La vérification navigateur de ce clic
et des cas associés a ensuite été réalisée avec succès ; R2.8 est validé UX.
Le contrôle ciblé du correctif a réussi : **3 fichiers / 18 tests frontend**, dont la
sélection SVAR simulée et l'absence d'action Employee pour Project/Participation.

### R2.9 — dépendances Task/Milestone validées fonctionnellement

Un modèle `MilestoneDependency` relie deux `Milestones` (Task ou Milestone), y compris entre
Projects. La migration additive `endpoints.0006` a été créée pour ce lot ; son état
d'application actuel doit être vérifié par environnement. Auto-dépendance, doublon et cycle sont refusés ; l'ordre temporel incohérent
est seulement signalé. L'API v1 utilise `Project.get_instances_for_user("change", ...)` pour
les deux Projects au POST/DELETE. Le Sheet existant porte le CRUD ; le Gantt Employee affiche
uniquement les liens dont les deux extrémités sont déjà dans son scope, en lecture seule.
La validation fonctionnelle manuelle R2.9 est réussie, y compris la lecture pour un lecteur
seul, les mutations selon `change` et l'ouverture du formulaire d'ajout à la demande.
L'API de lecture accepte un élément visible via Project ou via le contexte Employee et
masque les prédécesseurs non visibles. L'état d'application de `endpoints.0006` sur chaque
environnement reste à vérifier séparément avant déploiement.
Contrôles réalisés : **14 tests backend R2.9** sur PostgreSQL de test ; **23 tests frontend
ciblés** (Gantt, Sheet, page Employee) ; `manage.py check`, TypeScript, ESLint et build OK.
Le build conserve l'avertissement de taille de chunk connu. Le contrôle Django
`makemigrations endpoints --check --dry-run` relève seulement l'écart préexistant sur le
`help_text` de `Milestones.start_date` ; aucune migration hors R2.9 n'a été ajoutée.

### R2.10 — CRUD Leave validé fonctionnellement

La fiche Employee conserve Tableau et Calendrier avec un même Sheet consultation/création/
modification. `change_employee` gouverne les mutations ; les capacités sont exposées par
l'API. Le catalogue hiérarchique Leave_Type est sélectionnable à tous les niveaux. La
validation backend refuse les chevauchements pour un même Employee et type tout en
autorisant deux demi-journées contiguës. Toute suppression passe par confirmation.
Mois et Année permettent une sélection de dates convertie depuis la fin exclusive
FullCalendar ; cinq ans reste une synthèse sans sélection. Mois et Année permettent aussi
le déplacement et le redimensionnement des Leave autorisés, avec conservation des périodes
ST/MI/EN et retour à la position initiale si le PATCH échoue. La vue Année utilise
`dayGridYear`. Les événements Leave continuent
de passer par Calendar Core et CalendarService. Aucune migration de schéma R2.10.
La validation navigateur R2.10 est terminée avec succès ; la lisibilité de la vue annuelle
pourra être améliorée ultérieurement. Les contrôles ciblés figurent dans COMMANDES.md.
Les tests automatisés R2.10 passent (**8 backend, 16 frontend**) sur PostgreSQL de test et
Vitest ; ESLint et le build
Vite direct passent. Le contrôle TypeScript global reste bloqué par trois erreurs
préexistantes de l'évolution Gantt 60/120 mois (types de fenêtre et traduction anglaise),
hors du périmètre R2.10 ; `npm run build`, qui commence par TypeScript, n'est donc pas validé.


### R2.11a — Project List validée, filtre Participant enrichi ensuite

`/app/projects` affiche la liste Project avec recherche, tri initial par nom croissant,
pagination, filtres legacy pertinents, relations compactes et capacités serveur par ligne.
La validation navigateur R2.11a a été confirmée par l'utilisateur. Le filtre Participant
utilise ensuite le même sélecteur Employee que le filtre Supérieur, inclut les Employees
inactifs dans sa recherche et transmet leur identifiant au filtre Project ; cette adaptation
reste à vérifier au navigateur.
Le correctif passe les 8 tests backend Project et 32 tests frontend ciblés Project/Employee.
Le filtre visible Active=true est initialisé par le même mécanisme déclaratif que sur la
liste Employee ; il peut être retiré pour retrouver les éléments inactifs. Les deux listes
partagent aussi le badge Actif/Inactif, la sélection de ligne et les en-têtes triables.
La création et l'édition utilisent un Sheet limité aux champs propres à Project ; la
suppression demande confirmation. Après création, l'identifiant retourné par le POST
conduit directement à la route React `/app/projects/:id`, dont la fiche métier reste à
implémenter en R2.11b. Aucune migration de schéma ni dépendance R2.11a.
Les contrôles ciblés passent : 8 tests backend, 50 tests frontend, ESLint ciblé,
`manage.py check` et build Vite direct. Le contrôle TypeScript global conserve les trois
erreurs Gantt/i18n préexistantes.

### Résultats automatisés R2.7 — 23 septembre 2026

- Backend ciblé : **14 tests réussis en 26,531 s** (CRUD, matrice complète incluant
  self_edit/global/hiérarchie, CSRF, audit avec acteur, migration et compatibilité legacy).
  Après renforcement des attentes explicites du mapping, les **2 tests icônes** ont été
  relancés et réussissent en **0,293 s**.
- Régression backend session/auth/Employee : **90 tests réussis en 156,493 s**.
- Frontend ciblé : **5 fichiers / 36 tests réussis**, durée **46,41 s**.
- Régression frontend client/détail/Contracts/Financement/Leave/charge Project :
  **6 fichiers / 43 tests réussis**, durée **50,50 s**.
- Les premiers tests backend ont nécessité un accès PostgreSQL hors du bac à sable
  (`could not create socket: Operation not permitted`). Le test du formulaire legacy
  a été corrigé pour fournir la requête attendue par bootstrap-modal-forms.
- La première régression frontend a révélé une fixture encore au format tableau, corrigée.
  Des tests d’intégration ont aussi dépassé 5 s sous charge ; la validation finale utilise
  `--maxWorkers=1 --testTimeout=15000`, sans changer les assertions ni la configuration globale.
- `manage.py check` : aucune anomalie. `makemigrations staff --check --dry-run` : aucun
  changement manquant. Le contrôle global reste en échec pour les deux écarts préexistants
  endpoints/project décrits ci-dessus ; aucune migration supplémentaire n’a été créée.
- ESLint et TypeScript réussis ; build final Vite 7.2.6 réussi (2 760 modules), avec
  l’avertissement existant de chunk JavaScript >500 kB. Aucun changement de dépendance.
- `git diff --check` réussi à la racine et dans backend ; nouveaux fichiers également
  contrôlés pour les espaces de fin de ligne.
- La migration en développement et la validation manuelle React/legacy ont ensuite été
  réalisées et confirmées par l’utilisateur ; elles n’ont pas été exécutées par l’agent.


### Inventaire des fichiers R2.7

Les modifications préexistantes des lots antérieurs sont conservées. Les fichiers déjà
présents mais non suivis par Git sont classés « modifiés », pas « créés par R2.7 ».

Fichiers existants modifiés (22), chemins relatifs à la racine de distribution :

```text
backend/staff/models.py
backend/staff/rules.py
backend/staff/api_v1.py
backend/staff/serializers_v1.py
backend/staff/forms.py
backend/staff/admin.py
backend/labsmanager/urls_v1.py
backend/labsmanager/serializers.py
backend/settings/views.py
backend/templates/employee/employee_info_table.html
backend/labsmanager/tests/test_api_v1_employees.py
frontend/src/api/employees.ts
frontend/src/api/errors.ts
frontend/src/pages/EmployeeOverview.tsx
frontend/src/pages/useEmployeeResource.ts
frontend/src/pages/EmployeeDetailPage.test.tsx
frontend/src/i18n/i18n.ts
docs/react-migration/ARCHITECTURE.md
docs/react-migration/DECISIONS.md
docs/react-migration/STATUS.md
docs/react-migration/MATRIX.md
docs/react-migration/COMMANDES.md
```

Fichiers créés (15) :

```text
backend/staff/permissions_v1.py
backend/staff/migrations/0014_genericinfotype_icon_lucide.py
backend/labsmanager/tests/test_api_v1_generic_info.py
backend/labsmanager/tests/test_generic_info_icons.py
frontend/src/api/useMutation.ts
frontend/src/api/useMutation.test.tsx
frontend/src/api/errors.test.ts
frontend/src/components/common/ConfirmDialog.tsx
frontend/src/components/common/ConfirmDialog.test.tsx
frontend/src/pages/EmployeeGenericInfo.tsx
frontend/src/pages/EmployeeGenericInfo.module.css
frontend/src/pages/EmployeeGenericInfo.test.tsx
frontend/src/pages/GenericInfoFormSheet.tsx
frontend/src/pages/genericInfoIcons.ts
frontend/src/pages/useEmployeeResource.test.tsx
```

Aucun fichier supprimé, aucune dépendance ajoutée, aucun commit ni changement R2.8.
