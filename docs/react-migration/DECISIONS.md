# Decisions durables

- Django reste le backend et porte la logique metier.
- PostgreSQL et les donnees existantes sont conserves.
- La migration est progressive, par lots fonctionnels ; aucun Big Bang.
- L'interface Django existante reste fonctionnelle pendant la transition.
- Le nouveau frontend sera React + TypeScript. Le scaffold JSX actuel n'est pas une contrainte de compatibilite.
- Les nouvelles API stables sont versionnees sous `/api/v1/`. Les routes `/api/` actuelles restent compatibles pendant la transition.
- Les apps Django ne sont pas renommees ou reorganisees sans necessite demontree, afin de proteger migrations, ContentTypes et permissions.
- Le backend controle toutes les permissions ; le frontend adapte seulement la presentation.
- L'authentification Django par session et cookie CSRF est privilegiee. Aucun JWT n'est introduit sans besoin explicite. Token et Basic existants seront audites, pas etendus par defaut.
- Aucune migration BDD sans benefice metier ou technique concret.
- Aucun refactoring global preventif ; les abstractions sont creees lorsqu'un lot les justifie.
- Toute dependance Python est epinglee et ajoutee au `requirements.txt` racine installe par Docker, avec mise a jour coherente de `requirements.in`, dans le meme changement que son usage.
- Toute dependance npm met a jour `frontend/package.json` et `frontend/package-lock.json` dans le meme changement.
- Toute action manuelle est documentee chronologiquement dans `COMMANDES.md`, en distinguant bare-metal et Docker.
- Les routes Django historiques sont conservees et `/app/` est reserve au shell React.
- Le build React de production ne sera integre a Nginx/Docker qu'apres validation du shell.
- L'ecart local entre le gitlink historique `labsmanager` et `backend/` doit etre resolu ou documente avant de modifier la distribution.
