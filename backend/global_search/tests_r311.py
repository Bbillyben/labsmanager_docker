"""Advanced Search language, execution and visibility regression tests."""

from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient

from project.models import GenericInfoProject, GenericInfoTypeProject, Institution, Institution_Participant, Participant, Project
from staff.models import Employee, GenericInfo, GenericInfoType, Team, TeamMate

from .contracts import SearchField, SearchProvider, SearchResult
from .language import AndNode, GenericInfoNode, KeyNode, NotNode, OrNode, SearchSyntaxError, TextNode, parse, tokenize


class LanguageTests(SimpleTestCase):
    def test_token_positions_quotes_escapes_and_keywords(self):
        tokens = tokenize('leader:"Jean \\"JP\\" Dupont" and (NOT status:PhD)')
        self.assertEqual([token.kind for token in tokens],
                         ["WORD", "COLON", "STRING", "AND", "LPAREN", "NOT", "WORD", "COLON", "WORD", "RPAREN", "EOF"])
        self.assertEqual(tokens[2].value, 'Jean "JP" Dupont')
        self.assertEqual(tokens[0].start, 0)
        self.assertEqual(tokens[2].end, 27)
        with self.assertRaises(SearchSyntaxError):
            tokenize('"unclosed')

    def test_parser_precedence_parentheses_free_text_and_generic_info(self):
        node = parse('project:Alpha OR project:Beta AND NOT leader:Jean')
        self.assertIsInstance(node, OrNode)
        self.assertIsInstance(node.children[1], AndNode)
        self.assertIsInstance(node.children[1].children[1], NotNode)
        self.assertIsInstance(parse('(project:Alpha OR project:Beta) AND leader:Jean'), AndNode)
        self.assertEqual(parse('Jean Dupont'), TextNode('Jean Dupont'))
        self.assertEqual(parse('"Jean Dupont"'), TextNode('Jean Dupont', True))
        self.assertEqual(parse('info:"ORCID"="0000-1234"'), GenericInfoNode('ORCID', '0000-1234'))
        for source in ('project:', '(project:Alpha', 'project:Alpha AND', 'info:"ORCID"=', 'project:Alpha foo'):
            with self.assertRaises(SearchSyntaxError, msg=source):
                parse(source)


class StructuredSearchTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="advanced-search")
        self.employee = Employee.objects.create(first_name="Jean", last_name="Dupont", user=self.user)
        self.other = Employee.objects.create(first_name="Alice", last_name="Martin")
        self.secret = Employee.objects.create(first_name="Secret", last_name="Person")
        self.institution = Institution.objects.create(short_name="INSERM", name="Inserm Institute")
        self.project = Project.objects.create(name="PreciseIT")
        self.second = Project.objects.create(name="BariBoul")
        self.hidden = Project.objects.create(name="Hidden")
        for project in (self.project, self.second):
            Participant.objects.create(project=project, employee=self.employee, status="p")
        Participant.objects.create(project=self.project, employee=self.employee, status="l")
        Participant.objects.create(project=self.second, employee=self.other, status="l")
        Participant.objects.create(project=self.hidden, employee=self.secret, status="l")
        Institution_Participant.objects.create(project=self.project, institution=self.institution)
        self.team = Team.objects.create(name="Team Alpha", leader=self.other)
        TeamMate.objects.create(team=self.team, employee=self.employee)
        kind = GenericInfoType.objects.create(name="ORCID")
        GenericInfo.objects.create(employee=self.employee, info=kind, value="0000-1234")
        GenericInfo.objects.create(employee=self.secret, info=kind, value="SECRET-ID")
        project_kind = GenericInfoTypeProject.objects.create(name="Project ID")
        GenericInfoProject.objects.create(project=self.project, info=project_kind, value="PI-42")
        GenericInfoProject.objects.create(project=self.hidden, info=project_kind, value="HIDDEN-ID")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def search(self, query, **kwargs):
        response = self.client.get('/api/v1/search/', {'q': query, **kwargs})
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def test_provider_field_boolean_counts_and_visibility(self):
        self.assertEqual(self.search('project:PreciseIT')['counts'], {'project': 1})
        self.assertEqual(self.search('employee:Dupont')['counts']['employee'], 1)
        self.assertEqual(set(self.search('project:PreciseIT OR employee:Dupont')['counts']), {'project', 'employee'})
        self.assertEqual(self.search('leader:Jean')['counts']['project'], 1)
        self.assertEqual(self.search('participant:Jean')['counts']['team'], 1)
        self.assertEqual(self.search('participant:Jean')['counts']['project'], 2)
        self.assertEqual(self.search('project:PreciseIT AND institution:Inserm')['counts']['project'], 1)
        self.assertEqual(self.search('project:PreciseIT AND NOT leader:Jean')['counts']['project'], 0)
        self.assertEqual(self.search('project:BariBoul AND NOT leader:Jean')['counts']['project'], 1)
        self.assertEqual(self.search('project:PreciseIT OR project:BariBoul')['counts']['project'], 2)
        self.assertEqual(self.search('project:PreciseIT OR project:BariBoul AND institution:Inserm')['counts']['project'], 1)
        self.assertEqual(self.search('(project:PreciseIT OR project:BariBoul) AND institution:Inserm')['counts']['project'], 1)
        self.assertEqual(self.search('NOT leader:Jean')['counts']['project'], 1)
        self.assertEqual(self.search('leader:Secret')['counts']['project'], 0)
        self.assertEqual(self.search('project:Hidden')['counts']['project'], 0)

    def test_phrase_generic_info_and_errors(self):
        self.assertEqual(self.search('"Jean Dupont"')['counts']['employee'], 1)
        self.assertEqual(self.search('leader:"Jean Dupont"')['counts']['project'], 1)
        self.assertEqual(self.search('info:"ORCID"="0000-1234"')['counts']['employee'], 1)
        self.assertEqual(self.search('info:"Project ID"="PI-42"')['counts']['project'], 1)
        self.assertEqual(self.search('info:"ORCID"="0000"')['counts']['employee'], 0)
        self.assertEqual(self.search('info:"Unknown"="anything"')['counts']['employee'], 0)
        self.assertEqual(self.search('info:"Project ID"="HIDDEN-ID"')['counts']['project'], 0)
        self.assertEqual(self.search('info:"ORCID"="SECRET-ID"')['counts']['employee'], 0)
        result = self.search('info:"ORCID"="0000-1234"')['results'][0]
        self.assertIn('ORCID: 0000-1234', result['match_reason'])
        for query in ('project:', '(project:Foo', 'unknown:bar'):
            response = self.client.get('/api/v1/search/', {'q': query})
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.data['error'], 'invalid_search_query')
            self.assertIsInstance(response.data['position'], int)

    def test_dynamic_plugin_provider_and_field(self):
        class PublicationProvider(SearchProvider):
            key = 'publication'
            fields = (SearchField('doi', 'DOI', ('name',)),)

            def visible_queryset(self, user):
                return Project.get_instances_for_user('view', user, Project.objects.all())

            def make_result(self, obj, *, score, match_reason):
                return SearchResult(self.key, str(obj.pk), obj.name, '', f'/app/projects/{obj.pk}', score,
                                    'BookOpen', match_reason)

        plugin = SimpleNamespace(get_search_providers=lambda user: (PublicationProvider(),))
        with patch('plugin.registry.registry.with_mixin', return_value=[plugin]):
            self.assertEqual(self.search('publication:PreciseIT')['counts']['publication'], 1)
            self.assertEqual(self.search('doi:PreciseIT')['counts']['publication'], 1)
        response = self.client.get('/api/v1/search/', {'q': 'doi:PreciseIT'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['error'], 'invalid_search_query')
