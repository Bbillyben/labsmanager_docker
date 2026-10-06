# LabsManager

**LabsManager**

A web application for managing academic research laboratories.

LabsManager is a Django and React application designed to help research laboratories manage their day-to-day administrative and project activity: employees, projects, funding, budgets, expenses, contracts, leave, institutions, reporting, and related information.

Documentation is available at:

<https://labsmanager-doc.readthedocs.io/en/latest/>

---

## Features

LabsManager currently includes tools for managing:

- **Employees** — employee records, status, contracts, project involvement, dedicated budgets, leave, and related information.
- **Teams** — organisation of employees into teams.
- **Contracts** — employee contracts, dates, funding sources, and associated information.
- **Projects** — project management, participants, milestones, funding, and administrative information.
- **Funds** — management of project and institutional funding.
- **Budgets** — budget allocation and monitoring.
- **Expenses** — expense tracking and financial follow-up.
- **Leave** — employee leave management.
- **Institutions and funders** — organisations, contacts, and associated information.
- **Dashboards** — configurable views for employees, team leaders, and laboratory managers.
- **Reports** — template-based reporting for employees, projects, and other entities.
- **Global search** — cross-application search with support for structured and extensible fields.
- **Plugins** — extensible features and integrations loaded from the application plugin system.

---

## Architecture

LabsManager is maintained as a single repository containing both the backend and frontend.

```
labsmanager/
├── backend/              # Django application, API and legacy interface
├── frontend/             # React application
├── react-migration/      # Architecture and migration documentation
├── Dockerfile
├── docker-compose.yml
├── CHANGELOG.md
└── README.md
```

The application uses:

- **Django** as the backend and API server.
- **React** as the main user interface.
- **PostgreSQL** as the database.
- **Nginx** as the reverse proxy and static file server.
- **Docker Compose** for container orchestration.

React does not use a separate backend. Both the React interface and the legacy Django interface use the same Django application and the same database.

The React application is built during the Docker image build. Node.js and npm are therefore required only at build time and are not part of the production runtime.

The React SPA is served under:

```
/app/
```

Django continues to handle server-side routes such as:

```
/api/
/admin/
```

React static assets are served under:

```
/static/frontend/
```

During the React migration period, the legacy Django interface remains available as a fallback.

---

## Installation

### Requirements

The recommended deployment method is Docker Compose.

You will need:

- Docker
- Docker Compose
- PostgreSQL through the provided Docker configuration or an external compatible PostgreSQL instance

---

## Environment configuration

LabsManager is configured using environment variables, typically stored in a `.env` file.

Do not commit production secrets to the repository.

Example:

```
# ---------------------------------------------------------------------
# Django
# ---------------------------------------------------------------------

SECRET_KEY=change-me
DEBUG=false

DJANGO_ALLOWED_HOSTS=localhost,example.org
CSRF_TRUSTED_ORIGINS=https://example.org

LABS_LOG_LEVEL=INFO


# ---------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------

SQL_ENGINE=django.db.backends.postgresql

LAB_DB_NAME=django_db
LAB_DB_USER=djangoUser
LAB_DB_PASSWORD=change-me
LAB_DB_HOST=db
LAB_DB_PORT=5432


# ---------------------------------------------------------------------
# Docker / application
# ---------------------------------------------------------------------

LAB_WEB_PORT=80
LAB_TAG=latest


# ---------------------------------------------------------------------
# Static and media files
# ---------------------------------------------------------------------

LABSMANAGER_STATIC_ROOT=/home/labsmanager/data/static/
LABSMANAGER_MEDIA_ROOT=/home/labsmanager/data/media/


# ---------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------

LAB_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
LAB_EMAIL_HOST=
LAB_EMAIL_PORT=
LAB_EMAIL_USERNAME=
LAB_EMAIL_SENDER=
LAB_EMAIL_PASSWORD=
LAB_EMAIL_PREFIX=
LAB_EMAIL_TLS=false
LAB_EMAIL_SSL=true


# ---------------------------------------------------------------------
# Django site
# ---------------------------------------------------------------------

LAB_SITE_ID=1

DJANGO_ADMINS="username1,<user1@example.org> username2,<user2@example.org>"


# ---------------------------------------------------------------------
# Django admin customisation
# ---------------------------------------------------------------------

ADMIN_HEADER=LabsManager
ADMIN_SITE_TITLE=LabsManager
ADMIN_INDEX_TITLE=Menu
```

Environment variable names and available settings may evolve. Refer to the project configuration and deployment documentation for the authoritative list.

---

## Persistent data

Application data that must persist between container recreations should be stored outside the application container.

This includes, in particular:

- PostgreSQL data
- uploaded media
- collected static files when applicable
- plugins stored in `data/plugins/`
- instance-specific configuration and persistent application data

The exact host paths depend on the deployment environment and should not be hard-coded into the repository documentation.

---

## Plugins

LabsManager supports plugins stored in:

```
data/plugins/
```

The presence of a plugin in this directory is the source of truth for plugin discovery.

Plugins may extend backend behaviour and expose frontend capabilities, including multiple dashboard widgets.

The application plugin registry is responsible for discovering and exposing plugin capabilities.

---

## Initial setup and database migrations

Database migrations are intentionally **not executed automatically when containers start**.

This prevents schema changes from being applied silently during deployment.

Before starting a new application version, check whether migrations are required and apply them explicitly.

For example:

```
docker compose exec lab-server python manage.py showmigrations
```

and, when appropriate:

```
docker compose exec lab-server python manage.py migrate
```

Initialisation of a completely empty database must remain supported.

Deployment procedures may differ depending on the environment. Instance-specific commands, hostnames, paths, credentials, database dumps, and operational procedures are intentionally not documented in this README.

---

## Frontend development

The React frontend lives in:

```
frontend/
```

During development, frontend dependencies and build commands are managed from this directory.

The production Docker build compiles the React application and integrates the resulting assets into Django's static files.

There is no separate React container in the production architecture.

---

## Backend development

The Django backend lives in:

```
backend/
```

It contains:

- Django applications
- REST/API endpoints
- permissions and capabilities
- plugin infrastructure
- legacy Django templates
- database migrations
- backend tests

The legacy Django interface is intentionally preserved during the first phase of the React migration.

---

## React migration documentation

Architecture and migration decisions are documented under:

```
react-migration/
```

This directory contains documentation such as:

```
ARCHITECTURE.md
DECISIONS.md
STATUS.md
MATRIX.md
COMMANDES.md
REUSABLE.md
```

These files document the product architecture and migration strategy.

They must not contain information specific to a particular production instance, such as:

- hostnames
- IP addresses
- secrets
- real database dumps
- VM-specific paths
- instance-specific deployment procedures

---

## Development principles

Before implementing a new component or pattern, check whether an existing reusable implementation is already documented in:

```
react-migration/REUSABLE.md
```

The project favours reuse of existing components and patterns over duplication.

---

## Changelog

Project changes are documented in:

```
CHANGELOG.md
```

The changelog now covers the LabsManager product as a whole, including backend, frontend, deployment architecture, and migration-related changes.

---

## License

LabsManager is licensed under the **GNU Affero General Public License v3.0**.

See:

```
LICENSE.txt
```

for details.

---

## Credits

LabsManager was inspired in part by [InvenTree](https://github.com/inventree/InvenTree), and some historical code was adapted from that project.

Historical menu illustrations were sourced from:

- [https://www.freevector.com](https://www.freevector.com/)
- [https://fr.vecteezy.com](https://fr.vecteezy.com/)





















































































































































































