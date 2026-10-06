"""Transactional orchestration for a disposable, dedicated demo database."""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import CommandError
from django.db import connection, transaction

from dashboard.models import Dashboard
from dashboard.template_service import create_template_dashboard
from endpoints.models import Milestones
from expense.models import Contract, Expense, Expense_point
from fund.models import Budget, Fund, Fund_Item
from leave.models import Leave
from project.models import Participant, Project
from staff.models import Employee, Employee_Status, Employee_Superior, Team, TeamMate

from .context import DemoContext
from .contracts import generate_contracts
from .funding import generate_funding
from .leaves import generate_leaves
from .people import generate_people
from .projects import generate_projects
from .references import ensure_reference_data


OPERATIONAL_MODELS = (get_user_model(), Employee, Project, Fund, Expense, Contract, Leave, Team, Dashboard)


def has_operational_data():
    return any(model.objects.exists() for model in OPERATIONAL_MODELS)


def reset_operational_data():
    """Purge operational rows, retaining groups and reference catalogs."""
    Expense.objects.all().delete()
    Expense_point.objects.all().delete()
    Budget.objects.all().delete()
    Fund_Item.objects.all().delete()
    Contract.objects.all().delete()
    Fund.objects.all().delete()
    Milestones.objects.all().delete()
    Participant.objects.all().delete()
    Project.objects.all().delete()
    Leave.objects.all().delete()
    TeamMate.objects.all().delete()
    Team.objects.all().delete()
    Employee_Status.objects.all().delete()
    Employee_Superior.objects.all().delete()
    Employee.objects.all().delete()
    Dashboard.objects.all().delete()
    get_user_model().objects.all().delete()


def generate_demo_dataset(reference_date, seed, reset=False):
    if reset and not (settings.DEBUG or connection.settings_dict["NAME"].rsplit("/", 1)[-1].startswith("test_")):
        raise CommandError("Refusing --reset outside DEBUG or a test database.")
    if not reset and has_operational_data():
        raise CommandError("Existing operational data detected. Use --reset to rebuild the demo database.")
    with transaction.atomic():
        if reset:
            reset_operational_data()
        ctx = DemoContext(reference_date=reference_date, seed=seed)
        ensure_reference_data(ctx)
        generate_people(ctx)
        generate_projects(ctx)
        generate_funding(ctx)
        generate_contracts(ctx)
        generate_leaves(ctx)
        for account, template, name in (
            ("employee", "employee", "Employee overview"),
            ("leader", "leader", "Team overview"),
            ("labmanager", "lab-manager", "Laboratory overview"),
        ):
            dashboard = create_template_dashboard(ctx.users[account], template, name)
            if not dashboard.widgets.exists():
                raise CommandError(f"Dashboard template {template} produced no widgets")
        return ctx
