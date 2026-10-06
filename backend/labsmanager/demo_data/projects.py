"""Project portfolio, participation, and task/milestone scenarios."""

from decimal import Decimal

from endpoints.models import Milestones
from project.models import Participant, Project


# Key, display name, start/end offsets, active flag, leading team.
PROJECTS = (
    ("orion", "ORION — Optical Resilience", -540, 540, True, "quantum"),
    ("helix", "HELIX — Hybrid Materials", -420, 35, True, "quantum"),
    ("cobalt", "COBALT — Coordinated Sensors", -320, 420, True, "systems"),
    ("selene", "SELENE — Sustainable Signals", -780, -9, True, "quantum"),
    ("lyra", "LYRA — Learning Research Arrays", -460, -12, True, "systems"),
    ("verda", "VERDA — Green Instrumentation", -620, 380, True, "methods"),
    ("aster", "ASTER — Adaptive Interfaces", -380, 290, True, "quantum"),
    ("nimbus", "NIMBUS — Distributed Measurements", -270, 300, True, "systems"),
    ("aural", "AURAL — Acoustic Materials", -260, 160, True, "methods"),
    ("quanta", "QUANTA — Precise Modelling", -810, 640, True, "quantum"),
    ("mosaic", "MOSAIC — Modular Experiments", -180, 460, True, "systems"),
    ("vireo", "VIREO — Research Workflows", -260, 230, True, "methods"),
    ("opal", "OPAL — Open Analytical Platforms", -240, 370, True, "quantum"),
    ("arcus", "ARCUS — Reconfigurable Systems", -350, 190, True, "systems"),
    ("prism", "PRISM — Photonic Methods", -200, 500, True, "methods"),
    ("halcyon", "HALCYON — Scientific Networks", -150, 270, True, "quantum"),
    ("fable", "FABLE — Functional Assemblies", -110, 350, True, "systems"),
    ("nova", "NOVA — Novel Validation", 24, 450, True, "methods"),
    ("echo", "ECHO — Experimental Collaboration", -660, -24, False, "quantum"),
    ("meridian", "MERIDIAN — Measurement Standards", -400, 300, True, "methods"),
)


def _within(project, candidate):
    return max(project.start_date, min(candidate, project.end_date))


def generate_projects(ctx):
    for index, (key, name, start, end, active, team_key) in enumerate(PROJECTS):
        project = Project.objects.create(name=name, start_date=ctx.day(start), end_date=ctx.day(end), status=active)
        ctx.projects[key] = project
        team = ctx.teams[team_key]
        leader = team.leader
        people = [leader]
        if key == "orion":
            people += [ctx.people["phd-midterm"], ctx.people["postdoc-ending-soon"], ctx.people["senior-researcher"]]
        if key in ("orion", "cobalt", "mosaic", "verda"):
            people.append(ctx.people["engineer-multiproject"])
        secondary = [ctx.people[f"colleague-{number + 1:02d}"] for number in range(20) if number % 3 == ("quantum", "systems", "methods").index(team_key)]
        rng = ctx.rng_for("project-participants", key)
        people += rng.sample(secondary, min(3 + index % 2, len(secondary)))
        unique = {person.pk: person for person in people}
        ctx.participants[key] = []
        for person in unique.values():
            start_date = max(project.start_date, person.entry_date or project.start_date)
            end_date = min(project.end_date, person.exit_date) if person.exit_date else project.end_date
            # An open leader assignment keeps an overdue Project in the existing
            # "managed" dashboard scope until that Project is actually closed.
            if person == leader and key in ("selene", "lyra"):
                end_date = None
            if end_date is not None and start_date > end_date:
                continue
            participation = Participant.objects.create(
                project=project, employee=person, status="l" if person == leader else "p",
                start_date=start_date, end_date=end_date,
                quotity=Decimal("0.2") if person == leader else Decimal("0.4"),
            )
            ctx.participants[key].append(participation)
        if not ctx.participants[key]:
            raise ValueError(f"Project {key} has no valid participants")

        assigned = [part.employee for part in ctx.participants[key]]
        mid = project.start_date + (project.end_date - project.start_date) // 2
        due_soon = _within(project, ctx.day(7 if key == "orion" else 14 + index % 20))
        later = _within(project, ctx.day(45 + index % 55))
        overdue = _within(project, ctx.day(-5 - index % 8))
        completed = _within(project, mid)
        for suffix, due, done in (("review", due_soon, False), ("deliverable", later, False),
                                  ("completed-review", completed, True)):
            milestone = Milestones.objects.create(project=project, name=f"{key.upper()} {suffix.replace('-', ' ')}",
                                                   end_date=due, status=done)
            milestone.employee.add(assigned[0] if done else assigned[min(1, len(assigned) - 1)])
        for suffix, task_start, due, done in (
            ("analysis", _within(project, overdue - (ctx.day(0) - ctx.day(-20))), overdue, False),
            ("experiment", _within(project, due_soon - (ctx.day(0) - ctx.day(-18))), due_soon, False),
        ):
            start_date = min(task_start, due)
            task = Milestones.objects.create(project=project, name=f"{key.upper()} {suffix}",
                                             start_date=start_date, end_date=due, status=done,
                                             type="q", quotity=Decimal("0.35"))
            task.employee.add(assigned[min(1, len(assigned) - 1)])
