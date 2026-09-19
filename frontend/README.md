# LabsManager React

Socle React/Vite servi sous `/app/`. Le backend Django reste l’autorité pour la session, le CSRF et les autorisations.

Le serveur Vite relaie uniquement `/api` vers Django. La cible par défaut est `http://192.168.1.145:7000` et peut être remplacée avec `VITE_DJANGO_PROXY_TARGET`. Pour les POST CSRF de ce proxy de developpement, l'en-tete `Origin` transmis a Django est aligne sur cette cible.

Les liens vers l'interface Django historique utilisent `VITE_DJANGO_PUBLIC_URL`. En développement sur la VM, lancer par exemple :

```bash
VITE_DJANGO_PROXY_TARGET=http://127.0.0.1:7000 VITE_DJANGO_PUBLIC_URL=http://192.168.1.145:7000 npm run dev -- --host 0.0.0.0
```

Les commandes d’installation et de validation Debian sont maintenues dans `docs/react-migration/COMMANDES.md`.
