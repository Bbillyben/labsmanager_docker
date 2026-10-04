"""R3.12 completion context, safe suggestions and plugin extensions."""

from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient

from fund.models import Fund, Fund_Institution
from project.models import GenericInfoTypeProject, Institution, Institution_Participant, Participant, Project
from staff.models import Employee, Employee_Status, Employee_Type, GenericInfoType, Team, TeamMate

from .contracts import SearchField, SearchProvider, SearchResult
from .language import completion_context, tokenize


class CompletionContextTests(SimpleTestCase):
    def test_tolerates_partials_and_tracks_middle_ranges(self):
        self.assertEqual(completion_context('', 0).kind, 'key')
        self.assertEqual(completion_context('pro', 3).replace_start, 0)
        self.assertEqual(completion_context('project:', 8).kind, 'value')
        self.assertEqual(completion_context('project:Foo AND ', 16).kind, 'key')
        self.assertEqual(completion_context('project:Foo OR ', 15).kind, 'key')
        self.assertEqual(completion_context('NOT ', 4).kind, 'key')
        self.assertEqual(completion_context('(lea', 4).kind, 'key')
        self.assertEqual(completion_context('info:"', 6).kind, 'generic_info_type')
        self.assertEqual(completion_context('info:"ORCID"=', 13).kind, 'generic_info_value')
        self.assertEqual(completion_context('leader:Dupont ', 14).kind, 'operator')
        self.assertEqual(completion_context('leader:"Jean Dupont"', 20).kind, 'complete')
        middle = completion_context('project:Foo AND lea:Dupont', 19)
        self.assertEqual((middle.kind, middle.prefix, middle.replace_start, middle.replace_end),
                         ('key', 'lea', 16, 20))
        self.assertEqual(tokenize('info:"unfinished', tolerant=True)[2].kind, 'STRING')


class AutocompleteApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='completion-user')
        self.employee = Employee.objects.create(first_name='Jean', last_name='Dupont', user=self.user)
        self.hidden_employee = Employee.objects.create(first_name='Secret', last_name='Dupont')
        status = Employee_Type.objects.create(name='PhD student', shortname='PHD')
        Employee_Status.objects.create(employee=self.employee, type=status)
        self.project = Project.objects.create(name='PreciseIT')
        self.hidden_project = Project.objects.create(name='Hidden project')
        Participant.objects.create(project=self.project, employee=self.employee, status='l')
        Participant.objects.create(project=self.project, employee=self.employee, status='p')
        Participant.objects.create(project=self.hidden_project, employee=self.hidden_employee, status='l')
        self.institution = Institution.objects.create(short_name='INSERM', name='Inserm Institute')
        Institution_Participant.objects.create(project=self.project, institution=self.institution)
        self.funder = Fund_Institution.objects.create(short_name='ANR', name='Agency')
        self.manager = Institution.objects.create(short_name='LILLE', name='Lille University')
        Fund.objects.create(project=self.project, funder=self.funder, institution=self.manager, ref='FUND-42')
        self.team = Team.objects.create(name='Genomics', leader=self.employee)
        TeamMate.objects.create(team=self.team, employee=self.employee)
        GenericInfoType.objects.create(name='Matricule CHU')
        GenericInfoTypeProject.objects.create(name='Project Office')
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def suggest(self, query, cursor=None, **kwargs):
        response = self.client.get('/api/v1/search/autocomplete/', {'q': query, 'cursor': len(query) if cursor is None else cursor, **kwargs})
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def test_syntax_context_and_insertions(self):
        empty = self.suggest('')
        self.assertEqual(empty['context'], 'key')
        self.assertIn('project', [item['label'] for item in self.suggest('pro')['suggestions']])
        self.assertIn('employee', [item['label'] for item in self.suggest('emp')['suggestions']])
        self.assertIn('leader', [item['label'] for item in self.suggest('lea')['suggestions']])
        self.assertIn('institution', [item['label'] for item in self.suggest('inst')['suggestions']])
        self.assertIn('info', [item['label'] for item in self.suggest('inf')['suggestions']])
        self.assertIn('leader', [item['label'] for item in self.suggest('project:Foo AND lea')['suggestions']])
        self.assertIn('leader', [item['label'] for item in self.suggest('project:Foo OR lea')['suggestions']])
        self.assertIn('leader', [item['label'] for item in self.suggest('NOT lea')['suggestions']])
        self.assertIn('leader', [item['label'] for item in self.suggest('(lea')['suggestions']])
        operators = self.suggest('leader:Dupont ')
        self.assertEqual([item['label'] for item in operators['suggestions']], ['AND', 'OR'])
        middle = self.suggest('project:Foo AND lea:Dupont', cursor=19)
        self.assertEqual((middle['replace_start'], middle['replace_end']), (16, 20))
        self.assertEqual(next(item for item in middle['suggestions'] if item['label'] == 'leader')['insert_text'], 'leader:')

    def test_generic_types_and_incomplete_quote(self):
        self.assertTrue(self.suggest('info:')['incomplete'])
        suggestions = self.suggest('info:mat')['suggestions']
        self.assertEqual(suggestions[0]['insert_text'], '"Matricule CHU"=')
        self.assertEqual(self.suggest('info:"mat')['suggestions'][0]['insert_text'], '"Matricule CHU"=')
        self.assertEqual(self.suggest('info:"ORCID"=')['suggestions'], [])
        self.assertFalse(self.suggest('info:"ORCID"="0000"')['incomplete'])
        self.assertTrue(self.suggest('info:"ORCID"="0000')['incomplete'])
        self.assertEqual(self.suggest('info:pro')['suggestions'][0]['label'], 'Project Office')

    def test_visible_values_and_provider_values(self):
        for query, expected in [('leader:dup', 'Jean DUPONT'), ('participant:dup', 'Jean DUPONT'),
                                ('institution:ins', 'INSERM'), ('funder:an', 'ANR'),
                                ('manager:lil', 'LILLE'), ('status:p', 'PhD student'),
                                ('project:prec', 'PreciseIT')]:
            labels = [item['label'] for item in self.suggest(query)['suggestions']]
            self.assertIn(expected, labels, query)
        self.assertNotIn('Secret DUPONT', [item['label'] for item in self.suggest('leader:dup')['suggestions']])
        self.assertEqual(self.suggest('project:hid')['suggestions'], [])
        self.assertEqual(self.suggest('leader:')['suggestions'], [])

    def test_plugin_and_validation(self):
        class Publication(SearchProvider):
            key = 'publication'
            label = 'Publications'
            fields = (SearchField('author', 'Author', ('name',)), SearchField('doi', 'DOI', ('name',)))
            suggestable_fields = ('author',)

            def visible_queryset(self, user):
                return Project.get_instances_for_user('view', user, Project.objects.all())

            def make_result(self, obj, *, score, match_reason):
                return SearchResult(self.key, str(obj.pk), obj.name, '', f'/app/projects/{obj.pk}', score,
                                    'BookOpen', match_reason)

        plugin = SimpleNamespace(get_search_providers=lambda user: (Publication(),))
        with patch('plugin.registry.registry.with_mixin', return_value=[plugin]):
            self.assertIn('publication', [item['label'] for item in self.suggest('pub')['suggestions']])
            self.assertIn('author', [item['label'] for item in self.suggest('aut')['suggestions']])
            self.assertIn('PreciseIT', [item['label'] for item in self.suggest('author:pre')['suggestions']])
        self.assertNotIn('publication', [item['label'] for item in self.suggest('pub')['suggestions']])
        for params in ({'q': 'x', 'cursor': 99}, {'q': 'x', 'cursor': 'bad'}, {'q': 'x', 'provider': 'missing'}):
            self.assertEqual(self.client.get('/api/v1/search/autocomplete/', params).status_code, 400)
        self.client.force_authenticate(user=None)
        self.assertIn(self.client.get('/api/v1/search/autocomplete/').status_code, (401, 403))

    def test_cursor_and_replace_range_use_browser_utf16_positions(self):
        query = '😀 AND lea'
        response = self.suggest(query, cursor=10)
        self.assertEqual((response['replace_start'], response['replace_end']), (7, 10))
        self.assertIn('leader', [item['label'] for item in response['suggestions']])

    def test_project_info_types_require_project_visibility(self):
        other = get_user_model().objects.create_user(username='completion-no-project')
        self.client.force_authenticate(other)
        self.assertEqual(self.suggest('info:pro')['suggestions'], [])
        self.assertEqual(self.suggest('info:mat')['suggestions'][0]['label'], 'Matricule CHU')
