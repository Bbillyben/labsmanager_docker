# LabsManager

**LabsManager** is a web application for managing academic research laboratories. Its Django backend and React interface bring together staff, projects, equipment, finances, calendars, and administrative workflows in one place.

Documentation is available at:

<https://labsmanager-doc.readthedocs.io/en/latest/>

---

## Features

LabsManager currently includes tools for managing:

- **Employees** — employee records, status and hierarchy, contracts, project involvement, dedicated budgets, leave, and related information.
- **Teams** — organisation of employees into teams.
- **Contracts** — employee contracts, dates, funding sources, and associated information.
- **Projects** — participants, tasks, milestones, planning, funding, and administrative information.
- **Equipment** — catalogue and categories, dated responsibilities, institutional inventories, related expenses, and maintenance planning, history and notifications.
- **Funds** — management of project and institutional funding.
- **Budgets** — budget allocation and monitoring.
- **Expenses** — expense tracking and financial follow-up.
- **Calendars and leave** — employee absences, project and equipment maintenance calendars, and calendars supplied by plugins.
- **Institutions and funders** — organisations, contacts, and associated information.
- **Dashboards** — configurable widgets and indicators, including Equipment and maintenance indicators.
- **Reports** — configurable Word and PDF templates for employees, projects, and equipment.
- **Tools** — financial tools, imports, an organisation chart, and data consistency checks.
- **Global search** — cross-application search with support for structured and extensible fields.
- **Plugins** — extensible backend and React features, including imports, UI contributions, calendars, and iCalendar subscriptions.

---

## Architecture

LabsManager is maintained as a single repository containing both the backend and frontend.

```
labsmanager/
├── backend/              # Django application, REST API and legacy interface
├── frontend/             # React application
├── docs/react-migration/ # Architecture and migration documentation
├── Dockerfile
├── docker-compose.yml
├── changelog.md
└── README.md
```

The application uses:

- **Django** as the backend, REST API server and permission authority.
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
/api/v1/ (alongside historical /api/ routes)
/admin/
```

React static assets are served under:

```
/static/frontend/
```

The historical Django interface remains available during the migration. React uses the same Django sessions and database; existing permissions continue to be enforced by the backend. In the Docker setup, a separate temporary port can expose the legacy interface.

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

Example for the repository's Docker Compose deployment (replace the sample domain and secrets):

```
# ---------------------------------------------------------------------
# Django
# ---------------------------------------------------------------------

SECRET_KEY=change-me
DEBUG=false

DJANGO_ALLOWED_HOSTS=labs.example.org
CSRF_TRUSTED_ORIGINS=https://labs.example.org

LABS_LOG_LEVEL=INFO


# ---------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------

SQL_ENGINE=django.db.backends.postgresql

LAB_DB_NAME=django_db
LAB_DB_USER=djangoUser
LAB_DB_PASSWORD=change-me
LAB_DB_HOST=lab-db
LAB_DB_PORT=5432


# ---------------------------------------------------------------------
# Docker / application
# ---------------------------------------------------------------------

LAB_WEB_PORT=1337
LAB_TAG=latest
LAB_EXT_VOLUME=/srv/labsmanager/data
# Enable only behind a trusted HTTPS-terminating reverse proxy.
LAB_TRUST_PROXY_SSL_HEADER=true
REACT_PUBLIC_URL=https://labs.example.org/app


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

Set `LAB_TRUST_PROXY_SSL_HEADER=false` for direct HTTP access. The HTTPS setting assumes traffic reaches Django only through the trusted proxy. Set `REACT_PUBLIC_URL` to the public React base URL, including `/app`, for links sent outside the application. Environment variable names and available settings may evolve; refer to the [installation guide](https://labsmanager-doc.readthedocs.io/en/latest/admin/installation/) and project configuration for the authoritative list.

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

LabsManager discovers plugins in the built-in and sample directories under `backend/plugin/`, as well as external plugins stored in:

```
data/plugins/
```

External plugins must be installed in this directory to be discovered. Plugin activation and permissions remain under application control.

Plugins may extend backend behaviour with models, URLs, imports, tokens, settings and published calendars. They can also contribute React modules, actions and dashboard widgets through the shared extension contracts. ICalExport provides iCalendar subscriptions; the Calendars plugin provides calendar types and events when installed.

The application plugin registry is responsible for discovering and exposing plugin capabilities.

---

## Initial setup and database migrations

Migrations are intentionally **not executed automatically when containers start**. For a new instance, start PostgreSQL first, then follow the one-off installation procedure in the [installation guide](https://labsmanager-doc.readthedocs.io/en/latest/admin/installation/) before starting the application services. This includes migrations, Django checks, static collection and initial data. The guide also covers administrator creation and the bare-metal layout.

For an existing instance, back up the database and apply pending migrations explicitly before restarting application services. Review new permissions and report definitions before updating existing data; do not blindly reload initialization fixtures. See the [Unreleased update notes](changelog.md#updating-an-existing-installation) for current migration and template requirements.

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

The legacy Django interface remains available alongside the React application for historical workflows and compatibility.

---

## React migration documentation

Architecture and migration decisions are documented under:

```
docs/react-migration/
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

Start with the [current migration status](docs/react-migration/STATUS.md) and [React architecture](docs/react-migration/ARCHITECTURE.md); the [reusable components guide](docs/react-migration/REUSABLE.md) records established frontend patterns.

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
docs/react-migration/REUSABLE.md
```

The project favours reuse of existing components and patterns over duplication.

### Source documentation

Write code documentation in English. Use Google-style Python docstrings and
TSDoc/JSDoc for nontrivial TypeScript and React functions, hooks, components,
and public types. Explain parameters, return values, meaningful exceptions,
side effects, permissions, and usage constraints when they are relevant.
Document public plugin extension contracts in enough detail for independently
built plugins to implement them without relying on undocumented assumptions.
Internal comments should explain decisions and invariants that are not obvious
from the code; avoid comments that merely restate an operation.

### React formatting

Run `npm run format` from `frontend/` to format its source files with the locally
installed Prettier version. Run `npm run format:check` to verify formatting
without changing files. In VS Code, select Prettier as the formatter for
JavaScript and TypeScript and enable Format on Save if desired. Keep the
`frontend/.prettierrc.json` conventions for future React changes, including
the existing code documentation.

---

## Changelog

Project changes are documented in:

```
changelog.md
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

---

## AI-assisted development

The migration of LabsManager's user interface to React was carried out with the assistance of artificial intelligence tools, particularly for code development, refactoring, and testing. Architectural decisions, functional specifications, code review, and validation remained under human supervision.
