"""R3.10 business axes, contextual visibility, ranking and full counts."""

from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from expense.models import Contract, Contract_type
from fund.models import Fund, Fund_Institution
from project.models import (GenericInfoProject, GenericInfoTypeProject, Institution,
                            Institution_Participant, Participant, Project)
from staff.models import (Employee, Employee_Status, Employee_Type, GenericInfo,
                          GenericInfoType, Team, TeamMate)


class BusinessSearchTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="business-search")
        self.employee = Employee.objects.create(first_name="Jean", last_name="Dupont", email="jean@example.test", user=self.user)
        self.hidden_employee = Employee.objects.create(first_name="Secret", last_name="Hidden", email="secret@example.test")
        self.coleader = Employee.objects.create(first_name="Claire", last_name="Martin")
        self.participant = Employee.objects.create(first_name="Alice", last_name="Moreau")
        self.status_type = Employee_Type.objects.create(name="Researcher", shortname="RES")
        Employee_Status.objects.create(employee=self.employee, type=self.status_type)
        self.old_status = Employee_Type.objects.create(name="Former pilot", shortname="OLD")
        Employee_Status.objects.create(employee=self.employee, type=self.old_status, end_date=date(2020, 1, 1))
        self.employee_info_type = GenericInfoType.objects.create(name="ORCID")
        GenericInfo.objects.create(employee=self.employee, info=self.employee_info_type, value="0000-SEARCH-1234")
        GenericInfo.objects.create(employee=self.hidden_employee, info=self.employee_info_type, value="HIDDEN-ORCID")

        self.project = Project.objects.create(name="Precise Medicine")
        self.hidden_project = Project.objects.create(name="Secret Precise Medicine")
        Participant.objects.create(project=self.project, employee=self.employee, status="l")
        Participant.objects.create(project=self.project, employee=self.coleader, status="cl")
        Participant.objects.create(project=self.project, employee=self.participant, status="p")
        Participant.objects.create(project=self.hidden_project, employee=self.hidden_employee, status="p")
        self.institution = Institution.objects.create(short_name="INSERM", name="Inserm Institute")
        Institution_Participant.objects.create(project=self.project, institution=self.institution)
        self.project_info_type = GenericInfoTypeProject.objects.create(name="Project ID")
        GenericInfoProject.objects.create(project=self.project, info=self.project_info_type, value="PI-SEARCH-1234")
        GenericInfoProject.objects.create(project=self.hidden_project, info=self.project_info_type, value="HIDDEN-PROJECT-ID")

        self.funder = Fund_Institution.objects.create(short_name="ANR", name="National Agency")
        self.manager = Institution.objects.create(short_name="LILLE", name="Lille University")
        self.fund = Fund.objects.create(project=self.project, funder=self.funder, institution=self.manager,
                                        ref="FUND-42", start_date=date(2026, 1, 1), end_date=date(2027, 1, 1))
        self.hidden_fund = Fund.objects.create(project=self.hidden_project, funder=self.funder, institution=self.manager,
                                               ref="SECRET-FUND", start_date=date(2026, 1, 1), end_date=date(2027, 1, 1))
        self.contract_type = Contract_type.objects.create(name="Research agreement")
        self.contract = Contract.objects.create(employee=self.employee, fund=self.fund, contract_type=self.contract_type)
        self.hidden_contract = Contract.objects.create(employee=self.hidden_employee, fund=self.hidden_fund,
                                                       contract_type=self.contract_type)
        self.team = Team.objects.create(name="Genomics", leader=self.coleader)
        TeamMate.objects.create(team=self.team, employee=self.employee)
        TeamMate.objects.create(team=self.team, employee=self.participant)
        self.hidden_team = Team.objects.create(name="Secret Team", leader=self.hidden_employee)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def search(self, text, provider=None, **options):
        params = {"q": text, **options}
        if provider:
            params["provider"] = provider
        response = self.client.get("/api/v1/search/", params)
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def ids(self, text, provider):
        return [item["object_id"] for item in self.search(text, provider)["results"]]

    def test_schema_has_all_business_axes_and_generic_info_capability(self):
        response = self.client.get("/api/v1/search/schema/")
        self.assertEqual(response.status_code, 200)
        providers = {item["key"]: item for item in response.data["providers"]}
        self.assertEqual(set(providers), {"employee", "project", "fund", "contract", "team"})
        self.assertTrue(providers["employee"]["supports_generic_info"])
        self.assertTrue(providers["project"]["supports_generic_info"])
        self.assertEqual({item["key"] for item in providers["project"]["fields"]},
                         {"name", "leader", "coleader", "participant", "institution", "generic_info"})
        self.assertEqual({item["key"] for item in providers["fund"]["fields"]}, {"reference", "funder", "manager"})
        self.assertFalse(hasattr(GenericInfoType, "searchable"))
        self.assertFalse(hasattr(GenericInfoTypeProject, "searchable"))

    def test_employee_name_email_current_status_and_generic_info(self):
        for query in ("Jean", "Dupont", "Dup", "Jean Dupont", "jean@example.test", "Researcher", "0000-SEARCH"):
            self.assertIn(str(self.employee.pk), self.ids(query, "employee"), query)
        self.assertEqual(self.ids("Former pilot", "employee"), [])
        result = self.search("0000-SEARCH", "employee")["results"][0]
        self.assertIn("ORCID: 0000-SEARCH-1234", result["match_reason"])
        self.assertEqual(result["url"], f"/app/employees/{self.employee.pk}")
        self.assertEqual(self.ids("HIDDEN-ORCID", "employee"), [])
        self.assertEqual(self.ids("Secret Hidden", "employee"), [])

    def test_project_roles_institution_generic_info_and_distributed_terms(self):
        for query, reason in (("Precise", "Name"), ("Jean", "Leader"), ("Claire", "Co-leader"),
                              ("Alice", "Participant"), ("INSERM", "Institution"),
                              ("PI-SEARCH", "Project ID")):
            result = self.search(query, "project")["results"][0]
            self.assertEqual(result["object_id"], str(self.project.pk), query)
            self.assertIn(reason, result["match_reason"])
        self.assertIn(str(self.project.pk), self.ids("Alice INSERM", "project"))
        self.assertEqual(self.ids("HIDDEN-PROJECT-ID", "project"), [])
        self.assertNotIn(str(self.hidden_project.pk), self.ids("Precise", "project"))

    def test_fund_reference_funder_manager_and_no_parent_name_propagation(self):
        for query, reason in (("FUND-42", "Reference"), ("National Agency", "Funder"),
                              ("LILLE", "Manager")):
            result = self.search(query, "fund")["results"][0]
            self.assertEqual(result["object_id"], str(self.fund.pk))
            self.assertIn(reason, result["match_reason"])
            self.assertEqual(result["url"], f"/app/projects/{self.project.pk}/funding#fund-row-{self.fund.pk}")
        self.assertEqual(self.ids("Precise Medicine", "fund"), [])
        self.assertEqual(self.ids("SECRET-FUND", "fund"), [])

    def test_contract_employee_email_type_status_and_hub_visibility(self):
        for query, reason in (("Jean", "Employee"), ("jean@example.test", "Employee email"),
                              ("Research agreement", "Contract type"), ("Effective", "Status")):
            result = self.search(query, "contract")["results"][0]
            self.assertEqual(result["object_id"], str(self.contract.pk), query)
            self.assertIn(reason, result["match_reason"])
            self.assertEqual(result["url"], f"/app/tools/contracts?employee={self.employee.pk}")
        self.assertEqual(self.ids("secret@example.test", "contract"), [])
        self.assertEqual(self.ids("Secret Hidden", "contract"), [])

    def test_visible_contract_does_not_expose_unviewable_employee_email_as_match(self):
        self.coleader.email = "claire.private@example.test"
        self.coleader.save()
        contract = Contract.objects.create(employee=self.coleader, fund=self.fund, contract_type=self.contract_type)
        self.assertIn(str(contract.pk), self.ids("Claire", "contract"))
        self.assertNotIn(str(contract.pk), self.ids("claire.private@example.test", "contract"))

    def test_team_name_leader_member_and_visibility(self):
        for query, reason in (("Genomics", "Name"), ("Claire", "Leader"), ("Alice", "Participant")):
            result = self.search(query, "team")["results"][0]
            self.assertEqual(result["object_id"], str(self.team.pk))
            self.assertIn(reason, result["match_reason"])
            self.assertEqual(result["url"], f"/app/teams/{self.team.pk}")
        self.assertEqual(self.ids("Secret Team", "team"), [])

    def test_counts_are_visible_complete_and_independent_of_returned_limit(self):
        for number in range(3):
            project = Project.objects.create(name=f"Precise expansion {number}")
            Participant.objects.create(project=project, employee=self.employee, status="p")
        data = self.search("Precise", "project", limit=1, per_provider=1)
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["groups"], {"project": 1})
        self.assertEqual(data["counts"], {"project": 4})
        self.assertEqual(self.search("SECRET-FUND", "fund")["counts"], {"fund": 0})
        all_counts = self.search("Jean")["counts"]
        self.assertEqual(all_counts["employee"], 1)
        self.assertEqual(all_counts["project"], 4)
        self.assertEqual(all_counts["contract"], 1)
        self.assertEqual(all_counts["team"], 1)
        self.assertEqual(all_counts["fund"], 0)

    def test_weighted_scoring_orders_name_before_relation_and_generic_info(self):
        direct = Project.objects.create(name="Atlas")
        related = Project.objects.create(name="Other relation")
        generic = Project.objects.create(name="Other info")
        for project in (direct, related, generic):
            Participant.objects.create(project=project, employee=self.employee, status="p")
        match_person = Employee.objects.create(first_name="Atlas", last_name="Person")
        Participant.objects.create(project=related, employee=match_person, status="p")
        GenericInfoProject.objects.create(project=generic, info=self.project_info_type, value="Atlas")
        results = self.search("Atlas", "project")["results"]
        self.assertEqual([item["object_id"] for item in results[:3]],
                         [str(direct.pk), str(related.pk), str(generic.pk)])

    def test_exact_prefix_and_contains_order_with_deduplicated_project(self):
        names = ("Atlas", "Atlas North", "North Atlas")
        projects = [Project.objects.create(name=name) for name in names]
        for project in projects:
            Participant.objects.create(project=project, employee=self.employee, status="p")
        # A second matching relation must not produce another row for one Project.
        duplicate = Employee.objects.create(first_name="Atlas", last_name="Colleague")
        Participant.objects.create(project=projects[0], employee=duplicate, status="p")
        results = self.search("Atlas", "project")["results"]
        self.assertEqual([item["object_id"] for item in results[:3]], [str(project.pk) for project in projects])
        self.assertEqual(len({item["object_id"] for item in results}), len(results))
