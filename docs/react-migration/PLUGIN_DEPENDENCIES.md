# Dépendances Python des plugins

## Déclaration et diagnostic

Un plugin builtin, sample ou externe peut placer un `requirements.txt` dans son répertoire. Les exigences ordinaires au format PEP 440 sont acceptées, par exemple `icalendar==7.3.0` ou `requests>=2.30,<3`. Les commentaires et marqueurs d’environnement Python sont acceptés. Les URL, références Git, chemins locaux, options pip, index alternatifs et fichiers inclus avec `-r` sont refusés pour l’installation administrée. Les plugins sans fichier continuent de fonctionner.

Le gestionnaire parcourt les répertoires des plugins sans importer leurs classes, lit les déclarations et compare les distributions installées avec `importlib.metadata` et `packaging`. Un plugin qui échoue à l’import à cause d’une bibliothèque absente reste visible dans **Paramètres → Administration → Plugins** avec son diagnostic. Un `SLUG` déclaré comme chaîne littérale est lu statiquement ; un slug construit dynamiquement peut être affiché sous le nom du répertoire jusqu’à correction du plugin. Les plugins publiés comme points d’entrée doivent embarquer leur `requirements.txt` à la racine de leur package Python.

L’activation vérifie l’état des dépendances et ne lance jamais pip. Un plugin déjà actif dont les exigences ne sont plus satisfaites n’est pas initialisé au rechargement ; son diagnostic reste affiché. La désactivation ne supprime aucun package.

## Stockage et compatibilité

`LAB_PLUGIN_PACKAGES_ROOT` définit le dépôt partagé. Par défaut sur bare metal : `/var/lib/labsmanager/plugin-packages` ; le compte exécutant Django doit pouvoir y écrire. La configuration YAML peut utiliser `plugin_packages_root`. Sous Docker, le chemin par défaut est `/home/labsmanager/plugin-packages`, monté sur le volume nommé `lab_plugin_packages` pour `lab-server` et `lab-worker`. Ce volume est distinct de `lab_data` et persiste lors d’un redémarrage ou d’une recréation Compose. Ne pas utiliser `docker compose down --volumes` si les packages doivent être conservés.

Les releases sont rangées sous une identité qui inclut la version majeure et mineure de Python, la plateforme, l’architecture, le cache tag et le SOABI. Après une mise à jour incompatible de Python ou de l’image, l’ancienne release n’est pas chargée. Il faut réinstaller les dépendances pour le nouvel environnement ; le volume seul ne garantit pas la compatibilité des extensions natives.

Au démarrage Django, la release active est ajoutée **après** les chemins de l’environnement Python principal dans `sys.path`. Les packages du cœur sont donc prioritaires. Les distributions qui recouvriraient celles du cœur sont refusées. Les processus déjà démarrés gardent le chemin de release résolu au démarrage. Après installation, redémarrer tous les processus Django : sous Docker, `docker compose restart lab-server lab-worker` ; sur bare metal, redémarrer les services web et worker configurés localement. Le bouton « Recharger les plugins » ne remplace pas ce redémarrage.

## Installation administrée

Seul un administrateur staff connecté par session peut lancer l’action **Installer les dépendances** après confirmation. La requête HTTP démarre un processus de gestion séparé et retourne immédiatement ; la fiche interroge l’état périodiquement. Un verrou de fichier empêche deux installations simultanées dans un même environnement.

Le processus utilise `sys.executable` et pip en mode résolution `--dry-run --report`, puis installe uniquement les wheels sélectionnés dans un répertoire temporaire avec `--target --no-deps`. Il vérifie les versions finales et les contraintes des distributions. Une incompatibilité avec le cœur, un autre plugin actif ou des packages déjà installés arrête l’installation. Les versions déjà gérées sont conservées comme contraintes figées ; une mise à jour contradictoire nécessite une intervention explicite de l’opérateur. La nouvelle release est publiée par bascule atomique d’un lien `active`. En cas d’échec, l’ancienne release reste intacte. Le résultat et les erreurs génériques sont enregistrés dans `operation.json` ; la sortie pip n’est pas exposée par l’API.

Pip peut exécuter du code tiers ; cette action ne constitue **pas** un bac à sable. Réserver l’administration aux personnes autorisées et auditer les plugins et leurs exigences. La première version n’accepte que les wheels disponibles pour l’environnement courant ; les packages distribués uniquement comme archives source nécessitent une installation opérateur séparée. L’installation utilise l’index pip configuré pour le serveur, sans accepter d’option d’index dans le fichier d’un plugin.

## Validation avec ICalExport

1. Sans `icalendar` installé, ouvrir la liste des plugins : **iCalendar Export** reste visible et indique `icalendar==7.3.0` manquant.
2. Ouvrir sa fiche et confirmer **Installer les dépendances**. L’installation ne peut aboutir que si les versions du cœur satisfont aussi les dépendances transitives d’`icalendar`.
3. Vérifier qu’une release existe sous `LAB_PLUGIN_PACKAGES_ROOT/<identité>/releases/` et que `active` y pointe.
4. Redémarrer serveur et worker, rafraîchir le diagnostic, puis activer ICalExport.
5. Créer un abonnement ICS depuis « Mes plugins ». Révoquer son token pour vérifier que l’URL cesse de fonctionner.

En cas d’échec, vérifier l’écriture du dépôt, l’accès à l’index pip, la disponibilité d’un wheel compatible et les contraintes affichées. Le processus de publication ne modifie jamais l’environnement Python principal. Les anciennes releases sont conservées ; leur nettoyage est une opération manuelle après vérification qu’aucun processus ne les utilise.

**Compatibilité `tzdata` :** le verrou du cœur demande désormais `tzdata==2025.3`, compatible avec `icalendar==7.3.0` et `pandas==2.2.2`. Les environnements déjà déployés avec `tzdata==2024.1` restent incompatibles jusqu’à la mise à jour du cœur : reconstruire l’image Docker ou mettre à jour l’environnement bare metal, puis redémarrer les processus avant l’installation du plugin. Le gestionnaire ne doit pas masquer ce conflit par une installation `--target` de `tzdata` : les processus Django utiliseraient toujours la version du cœur en priorité.
