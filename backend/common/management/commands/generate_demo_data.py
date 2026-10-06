"""Generate a complete, time-relative fictional laboratory on a dedicated DB."""

from datetime import date

from django.core.management.base import BaseCommand, CommandError

from labsmanager.demo_data import DEMO_DATA_VERSION
from labsmanager.demo_data.people import DEMO_ACCOUNTS
from labsmanager.demo_data.runner import generate_demo_dataset


class Command(BaseCommand):
    help = "Generate the synthetic demo dataset on a dedicated non-production database."

    def add_arguments(self, parser):
        parser.add_argument("--reference-date", default=date.today().isoformat(), metavar="YYYY-MM-DD")
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument("--reset", action="store_true")

    def handle(self, *args, **options):
        try:
            reference_date = date.fromisoformat(options["reference_date"])
        except ValueError as exc:
            raise CommandError("--reference-date must be YYYY-MM-DD") from exc
        ctx = generate_demo_dataset(reference_date, options["seed"], options["reset"])
        self.stdout.write(self.style.SUCCESS(
            f"Demo dataset v{DEMO_DATA_VERSION} generated: T0={reference_date}, seed={options['seed']}; "
            f"{len(ctx.people)} employees, {len(ctx.projects)} projects, {len(ctx.funds)} funds."
        ))
        for username, (_, group, password) in DEMO_ACCOUNTS.items():
            self.stdout.write(f"  {username} / {password} ({group})")
