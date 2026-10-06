"""Employment contracts tied to the generated funds and staff."""

from decimal import Decimal

from expense.models import Contract


CONTRACTS = (
    # Employee, fund, type, start/end offsets, HR follow-up, status.
    ("postdoc-ending-soon", "orion-main", "postdoc", -380, 24, True, "effe"),
    ("phd-midterm", "orion-main", "doctoral", -390, 510, True, "effe"),
    ("engineer-multiproject", "cobalt-main", "fixed", -220, 88, True, "effe"),
    ("colleague-01", "orion-bridge", "fixed", -120, 20, True, "effe"),
    ("colleague-02", "helix-grant", "fixed", -300, 29, True, "effe"),
    ("colleague-03", "verda-main", "doctoral", -260, 220, True, "effe"),
    ("colleague-04", "aster-main", "postdoc", -150, 75, True, "effe"),
    ("colleague-05", "nimbus-main", "fixed", -200, 180, False, "effe"),
    ("colleague-06", "aural-main", "fixed", -110, -7, True, "effe"),
    ("colleague-07", "quanta-main", "postdoc", -230, 390, True, "effe"),
    ("colleague-08", "mosaic-main", "doctoral", -100, 280, True, "effe"),
    ("colleague-09", "opal-main", "fixed", -140, 170, False, "effe"),
    ("colleague-10", "arcus-main", "fixed", -210, 130, True, "effe"),
    ("colleague-11", "prism-main", "postdoc", -80, 250, True, "prov"),
)


def generate_contracts(ctx):
    for employee_key, fund_key, type_key, start, end, active, status in CONTRACTS:
        employee = ctx.people[employee_key]
        Contract.objects.create(
            employee=employee, fund=ctx.funds[fund_key],
            contract_type=ctx.references["contract_types"][type_key],
            start_date=max(ctx.day(start), employee.entry_date), end_date=ctx.day(end),
            quotity=Decimal("1.000"), is_active=active, status=status,
        )
