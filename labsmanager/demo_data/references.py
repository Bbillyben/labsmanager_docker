"""Small fictional reference catalog required by the operational dataset."""

from django.core.management import call_command
from django.contrib.auth.models import Group
from expense.models import Contract_type
from fund.models import Cost_Type, Fund_Institution
from leave.models import Leave_Type
from project.models import Institution
from staff.models import Employee_Type


GROUPS = ("Lab_admin", "Lab_Manager", "Lab_leader", "Lab_employee", "favorite_notif_perm")


def ensure_reference_data(ctx):
    if not all(Group.objects.filter(name=name).exists() for name in GROUPS):
        call_command("loaddata", "group-fixture", verbosity=0)
    missing = [name for name in GROUPS if not Group.objects.filter(name=name).exists()]
    if missing:
        raise ValueError(f"Missing permission fixture groups: {', '.join(missing)}")

    ctx.references["employee_types"] = {
        key: Employee_Type.objects.get_or_create(shortname=key, defaults={"name": name})[0]
        for key, name in (
            ("PERM", "Permanent researcher"), ("POSTDOC", "Postdoctoral researcher"),
            ("PHD", "Doctoral researcher"), ("ENG", "Research engineer"),
            ("TECH", "Research technician"), ("INTERN", "Research intern"),
        )
    }
    ctx.references["contract_types"] = {
        key: Contract_type.objects.get_or_create(name=name)[0]
        for key, name in (("fixed", "Fixed-term research contract"), ("doctoral", "Doctoral contract"),
                          ("postdoc", "Postdoctoral contract"))
    }
    hr, _ = Cost_Type.objects.get_or_create(short_name="DHR", parent=None, defaults={"name": "Demo personnel", "is_hr": True})
    ctx.references["cost_types"] = {"hr": hr}
    for key, short, name in (
        ("equipment", "DEQ", "Demo equipment"), ("consumables", "DCO", "Demo consumables"),
        ("travel", "DTR", "Demo travel"), ("services", "DSV", "Demo services"),
    ):
        ctx.references["cost_types"][key] = Cost_Type.objects.get_or_create(short_name=short, parent=None, defaults={"name": name})[0]
    ctx.references["leave_types"] = {
        key: Leave_Type.objects.get_or_create(short_name=short, parent=None, defaults={"name": name, "color": color})[0]
        for key, short, name, color in (
            ("annual", "DAL", "Annual leave", "#2F8C83"),
            ("training", "DTR", "Training leave", "#5470B8"),
            ("personal", "DPL", "Personal leave", "#B88045"),
        )
    }
    ctx.references["institutions"] = {
        key: Institution.objects.get_or_create(short_name=short, defaults={"name": name})[0]
        for key, short, name in (
            ("university", "NVAU", "North Vale Academic University"),
            ("institute", "AERI", "Aster Research Institute"),
            ("hospital", "MRHC", "Merebrook Research Hospital"),
        )
    }
    ctx.references["funders"] = {
        key: Fund_Institution.objects.get_or_create(short_name=short, defaults={"name": name})[0]
        for key, short, name in (
            ("public", "VRC", "Vale Research Council"),
            ("foundation", "LUMF", "Lumen Discovery Foundation"),
            ("european", "AURA", "Aurora Collaborative Programme"),
            ("industry", "CYSYN", "Cypress Synthesis Partnership"),
        )
    }
