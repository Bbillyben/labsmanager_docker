"""Fictional staff, accounts, teams, and current reporting lines."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from staff.models import Employee, Employee_Status, Employee_Superior, Team, TeamMate


DEMO_ACCOUNTS = {
    "admin": ("lab-director", "Lab_admin", "DemoAdmin42!"),
    "labmanager": ("lab-manager", "Lab_Manager", "DemoManager42!"),
    "leader": ("team-a-leader", "Lab_leader", "DemoLeader42!"),
    "employee": ("phd-midterm", "Lab_employee", "DemoEmployee42!"),
}

CORE_PEOPLE = (
    ("lab-director", "Mira", "Vellor", "PERM", -2400, None),
    ("lab-manager", "Noé", "Sorell", "ENG", -1200, None),
    ("team-a-leader", "Elina", "Varrel", "PERM", -2100, None),
    ("team-b-leader", "Sami", "Nerand", "PERM", -1800, None),
    ("team-c-leader", "Léna", "Corven", "PERM", -1600, None),
    ("senior-researcher", "Talia", "Merova", "PERM", -1500, None),
    ("postdoc-ending-soon", "Ilan", "Berive", "POSTDOC", -500, 35),
    ("phd-midterm", "Camille", "Orren", "PHD", -400, 520),
    ("engineer-multiproject", "Nora", "Valden", "ENG", -730, None),
)

SECONDARY_NAMES = (
    ("Adrien", "Solven"), ("Maëlle", "Cavril"), ("Jonas", "Relmor"),
    ("Inès", "Vassel"), ("Robin", "Dorell"), ("Salomé", "Ervane"),
    ("Élias", "Rivene"), ("Daria", "Molven"), ("Nils", "Averin"),
    ("Lila", "Vernac"), ("Oscar", "Tellin"), ("Zélie", "Orvane"),
    ("Hugo", "Mersel"), ("Nadia", "Calven"), ("Théo", "Lerand"),
    ("Maya", "Corin"), ("Anis", "Serel"), ("Clara", "Novrel"),
    ("Émil", "Arelle"), ("Zoé", "Lindor"), ("Rayan", "Ferval"),
    ("Aïcha", "Norel"), ("Léo", "Marven"), ("Yuna", "Serlin"),
)


def generate_people(ctx):
    User = get_user_model()
    account_by_person = {person: (username, group, password) for username, (person, group, password) in DEMO_ACCOUNTS.items()}
    all_people = list(CORE_PEOPLE)
    for index, (first, last) in enumerate(SECONDARY_NAMES):
        key = f"colleague-{index + 1:02d}"
        rng = ctx.rng_for("person", key)
        role = ("PERM", "POSTDOC", "PHD", "ENG", "TECH", "INTERN")[index % 6]
        entry = -rng.randint(120, 1300)
        exit_offset = -rng.randint(10, 90) if index in (20, 21) else None
        if index in (22, 23):
            entry = rng.randint(7, 25)
        all_people.append((key, first, last, role, entry, exit_offset))

    for key, first, last, role, entry, exit_offset in all_people:
        account = account_by_person.get(key)
        user = None
        if account:
            username, group, password = account
            user = User(username=username, email=f"{username}@example.invalid", is_active=True,
                        is_staff=username == "admin", is_superuser=username == "admin")
            user.set_password(password)
            user.save()
            user.groups.add(Group.objects.get(name=group), Group.objects.get(name="favorite_notif_perm"))
            ctx.users[username] = user
        employee = Employee.objects.create(
            first_name=first, last_name=last, user=user,
            email=f"{key}@example.invalid", entry_date=ctx.day(entry),
            exit_date=ctx.day(exit_offset) if exit_offset is not None else None,
            is_active=exit_offset is None or exit_offset >= 0,
        )
        ctx.people[key] = employee
        Employee_Status.objects.create(
            employee=employee, type=ctx.references["employee_types"][role],
            is_contractual="s" if role == "PERM" else "c",
            start_date=ctx.day(entry), end_date=ctx.day(exit_offset) if exit_offset is not None else None,
        )

    leaders = ("team-a-leader", "team-b-leader", "team-c-leader")
    for key in leaders + ("lab-manager",):
        Employee_Superior.objects.create(employee=ctx.people[key], superior=ctx.people["lab-director"], start_date=ctx.day(-1000))
    Employee_Superior.objects.create(employee=ctx.people["senior-researcher"], superior=ctx.people["team-a-leader"], start_date=ctx.day(-900))
    Employee_Superior.objects.create(employee=ctx.people["postdoc-ending-soon"], superior=ctx.people["team-a-leader"], start_date=ctx.day(-500))
    Employee_Superior.objects.create(employee=ctx.people["phd-midterm"], superior=ctx.people["team-a-leader"], start_date=ctx.day(-400))
    Employee_Superior.objects.create(employee=ctx.people["engineer-multiproject"], superior=ctx.people["team-b-leader"], start_date=ctx.day(-700))
    for index in range(len(SECONDARY_NAMES)):
        key = f"colleague-{index + 1:02d}"
        employee = ctx.people[key]
        Employee_Superior.objects.create(employee=employee, superior=ctx.people[leaders[index % 3]], start_date=employee.entry_date)

    team_specs = (("quantum", "Quantum Materials Studio", leaders[0]),
                  ("systems", "Adaptive Systems Studio", leaders[1]),
                  ("methods", "Research Methods Studio", leaders[2]))
    for key, name, leader in team_specs:
        ctx.teams[key] = Team.objects.create(name=name, leader=ctx.people[leader])
    for index in range(len(SECONDARY_NAMES)):
        employee = ctx.people[f"colleague-{index + 1:02d}"]
        team = ctx.teams[("quantum", "systems", "methods")[index % 3]]
        TeamMate.objects.create(team=team, employee=employee, start_date=employee.entry_date)
    for key, team_key in (("senior-researcher", "quantum"), ("postdoc-ending-soon", "quantum"),
                          ("phd-midterm", "quantum"), ("engineer-multiproject", "systems"),
                          ("lab-manager", "methods")):
        TeamMate.objects.create(team=ctx.teams[team_key], employee=ctx.people[key], start_date=ctx.people[key].entry_date)
