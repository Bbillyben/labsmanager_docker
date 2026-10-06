"""Scenario-based funding, budgets, and expense consumption."""

from decimal import Decimal, ROUND_HALF_UP
from datetime import timedelta

from expense.models import Expense, Expense_point
from fund.models import Budget, Fund, Fund_Item
from settings.models import LMProjectSetting


# Key, project, funder, institution, base amount, consumption ratio, start/end offsets.
FUNDS = (
    ("orion-main", "orion", "european", "university", 720000, "0.56", -530, 520),
    ("orion-bridge", "orion", "foundation", "institute", 80000, "0.94", -180, 25),
    ("helix-grant", "helix", "public", "university", 330000, "0.26", -410, 30),
    ("cobalt-main", "cobalt", "industry", "institute", 490000, "0.62", -300, 390),
    ("selene-closed", "selene", "public", "university", 270000, "0.83", -760, -12),
    ("verda-main", "verda", "european", "institute", 610000, "0.48", -600, 350),
    ("aster-main", "aster", "foundation", "university", 185000, "0.51", -360, 270),
    ("nimbus-main", "nimbus", "public", "hospital", 240000, "0.59", -250, 280),
    ("aural-main", "aural", "industry", "institute", 130000, "0.67", -240, 145),
    ("quanta-main", "quanta", "european", "university", 1150000, "0.44", -790, 610),
    ("mosaic-main", "mosaic", "public", "university", 290000, "0.37", -160, 440),
    ("opal-main", "opal", "foundation", "hospital", 215000, "0.53", -220, 340),
    ("arcus-main", "arcus", "public", "institute", 390000, "0.71", -330, 175),
    ("prism-main", "prism", "industry", "university", 125000, "0.22", -190, 470),
)

ALLOCATIONS = (("hr", Decimal("0.45")), ("consumables", Decimal("0.25")),
               ("equipment", Decimal("0.20")), ("travel", Decimal("0.10")))


def money(value):
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def generate_funding(ctx):
    for key, project_key, funder_key, institution_key, base, ratio, start, end in FUNDS:
        project = ctx.projects[project_key]
        # BaseLabsManagerSetting.set_setting does not include project in its lookup.
        # Use the model's actual (key, project) identity to avoid changing another project.
        LMProjectSetting.objects.update_or_create(
            key="EXPENSE_CALCULATION", project=project, defaults={"value": "e"},
        )
        rng = ctx.rng_for("fund", key)
        amount = money(base + rng.randint(-base // 20, base // 20))
        fund = Fund.objects.create(
            project=project, funder=ctx.references["funders"][funder_key],
            institution=ctx.references["institutions"][institution_key], ref=f"DM-{key.upper()}",
            start_date=ctx.day(start), end_date=ctx.day(end),
        )
        ctx.funds[key] = fund
        target_spend = money(amount * Decimal(ratio))
        allocated = Decimal("0")
        spent = Decimal("0")
        for index, (cost_key, share) in enumerate(ALLOCATIONS):
            allocation = money(amount * share) if index < len(ALLOCATIONS) - 1 else amount - allocated
            allocated += allocation
            consumption = money(target_spend * share) if index < len(ALLOCATIONS) - 1 else target_spend - spent
            spent += consumption
            cost_type = ctx.references["cost_types"][cost_key]
            Fund_Item.objects.create(
                fund=fund, type=cost_type, amount=allocation,
                entry_date=ctx.day(start), value_date=ctx.day(start),
            )
            budget = None
            if cost_key in ("hr", "consumables"):
                budget = Budget.objects.create(fund=fund, cost_type=cost_type, amount=allocation,
                                               desc=f"{cost_key.title()} work package")
            latest = min(ctx.reference_date, fund.end_date)
            span = max(1, (latest - fund.start_date).days)
            # Expense_point is the historical aggregate. Seed a zero point, then
            # let each ordinary Expense.save() update it through the real signal.
            point = Expense_point.objects.create(
                fund=fund, type=cost_type, amount=0,
                entry_date=fund.start_date, value_date=fund.start_date,
            )
            installments = 4 if key in ("orion-main", "orion-bridge", "helix-grant", "cobalt-main") else 1
            booked = Decimal("0")
            for installment in range(installments):
                rng_date = ctx.rng_for("expense-date", f"{key}:{cost_key}:{installment}")
                offset = max(1, min(span, round(span * (installment + 1) / (installments + 1)) + rng_date.randint(-5, 5)))
                expense_date = fund.start_date + timedelta(days=offset)
                amount_part = money(consumption / installments) if installment < installments - 1 else consumption - booked
                booked += amount_part
                Expense_point.objects.filter(pk=point.pk).update(value_date=expense_date)
                Expense(
                    fund_item=fund, budget_item=budget, type=cost_type, amount=amount_part,
                    date=expense_date, status="r",
                    desc=f"{cost_key.title()} expenditure for {project_key.upper()} ({installment + 1})",
                    expense_id=f"DM-{key.upper()}-{index + 1}-{installment + 1}",
                ).save()
        fund.refresh_from_db()
        if fund.amount != amount or fund.expense != -target_spend:
            raise ValueError(f"Financial aggregates are inconsistent for {key}")
