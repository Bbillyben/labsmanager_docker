"""Past, current, and upcoming leave scenarios."""

from leave.models import Leave


LEAVES = (
    ("phd-midterm", "annual", -75, -70, "ST", "EN"),
    ("phd-midterm", "annual", 8, 11, "ST", "EN"),
    ("postdoc-ending-soon", "annual", -2, 2, "ST", "EN"),
    ("senior-researcher", "annual", 15, 18, "MI", "EN"),
    ("engineer-multiproject", "training", 22, 24, "ST", "MI"),
    ("colleague-01", "annual", 5, 7, "ST", "EN"),
    ("colleague-02", "personal", 12, 12, "ST", "MI"),
    ("colleague-03", "annual", 28, 32, "ST", "EN"),
    ("colleague-04", "training", -18, -17, "ST", "EN"),
    ("colleague-05", "annual", 34, 40, "ST", "EN"),
    ("colleague-06", "annual", -11, -9, "ST", "EN"),
    ("colleague-07", "annual", 2, 4, "ST", "EN"),
)


def generate_leaves(ctx):
    for person, kind, start, end, start_period, end_period in LEAVES:
        leave = Leave(
            employee=ctx.people[person], type=ctx.references["leave_types"][kind],
            start_date=ctx.day(start), end_date=ctx.day(end),
            start_period=start_period, end_period=end_period,
            comment="Synthetic demonstration absence",
        )
        leave.full_clean()
        leave.save()
