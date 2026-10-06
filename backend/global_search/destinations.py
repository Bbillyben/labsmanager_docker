"""Canonical React destinations shared by Search and Recent Items."""


def employee_url(employee):
    return f"/app/employees/{employee.pk}"


def project_url(project):
    return f"/app/projects/{project.pk}"


def fund_url(fund):
    return f"/app/projects/{fund.project_id}/funding#fund-row-{fund.pk}"


def contract_url(contract):
    return f"/app/tools/contracts?employee={contract.employee_id}"


def team_url(team):
    return f"/app/teams/{team.pk}"
