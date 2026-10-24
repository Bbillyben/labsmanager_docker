from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from django.contrib.admin.widgets import AdminSplitDateTime

from plugin.base.TokenMixin import TokenMixin
from plugin.admin import PluginTokenCreateForm
from plugin.models import PluginAccessToken, PluginConfig
from plugin.plugin import LabManagerPlugin
from plugin.registry import registry
from plugin.tokens import TokenError


class ExamplePlugin(TokenMixin):
    slug = 'token-test'
    TOKEN_CONFIG = {
        'plugin': True, 'user': True,
        'scopes': {
            'read': {'label': 'Read', 'plugin': True, 'user': True},
            'write': {'label': 'Write', 'plugin': True, 'user': False},
        },
    }

    def add_mixin(self, *args):
        pass

    def mixin_enabled(self, key):
        return key == 'token'


class TokenTests(TestCase):
    def setUp(self):
        self.config = PluginConfig.objects.create(key='token-test', name='Token Test')
        PluginConfig.objects.filter(pk=self.config.pk).update(active=True)
        self.config.active = True
        self.plugin = ExamplePlugin()
        self.alice = User.objects.create_user('alice')
        self.bob = User.objects.create_user('bob')
        self.staff = User.objects.create_user('staff', is_staff=True, is_superuser=True)
        self.patch_plugin = patch.object(registry, 'get_plugin', side_effect=lambda slug: self.plugin if slug == self.plugin.slug else None)
        self.patch_config = patch.object(registry, 'get_plugin_config', side_effect=lambda slug: self.config if slug == self.plugin.slug else None)
        self.patch_plugin.start()
        self.patch_config.start()
        self.addCleanup(self.patch_plugin.stop)
        self.addCleanup(self.patch_config.stop)

    def test_creation_validation_scopes_and_immutability(self):
        first, secret = self.plugin.create_token(kind='plugin', name='First', scopes=['read', 'write'])
        second, other_secret = self.plugin.create_token(kind='plugin', name='Second')
        personal, personal_secret = self.plugin.create_token(kind='user', name='Personal', user=self.alice, scopes=['read'])
        self.assertNotEqual(first.public_id, second.public_id)
        self.assertNotIn(secret, first.secret_hash)
        self.assertNotIn(secret.split('.')[1], first.secret_hash)
        self.assertEqual(self.plugin.validate_token(secret, kind='plugin', required_scopes=['write']).user, None)
        self.assertEqual(self.plugin.validate_token(personal_secret, kind='user', required_scopes=['read']).user, self.alice)
        self.assertIsNotNone(PluginAccessToken.objects.get(pk=first.pk).last_used_at)
        with self.assertRaises(TokenError):
            self.plugin.validate_token(other_secret, required_scopes=['read'])
        with self.assertRaises(TokenError):
            self.plugin.validate_token(personal_secret, required_scopes=['write'])
        with self.assertRaises(TokenError):
            self.plugin.validate_token(secret, kind='user')
        with self.assertRaises(TokenError):
            self.plugin.validate_token(first.public_id + '.wrong')
        with self.assertRaises(TokenError):
            self.plugin.create_token(kind='user', name='Invalid', user=self.alice, scopes=['write'])
        with self.assertRaises(TokenError):
            self.plugin.create_token(kind='plugin', name='x' * 151)
        first.scopes = []
        with self.assertRaises(ValidationError):
            first.save()

    def test_token_mixin_is_discoverable_without_other_mixins(self):
        class Standalone(TokenMixin, LabManagerPlugin):
            NAME = 'Standalone'
            SLUG = 'standalone'

        plugin = Standalone()
        self.assertTrue(plugin.mixin_enabled('token'))
        self.assertIn('token', plugin.get_registered_mixins())

    def test_expiry_revocation_inactive_plugin_and_user(self):
        token, secret = self.plugin.create_token(kind='user', name='Personal', user=self.alice)
        token.expires_at = timezone.now() - timedelta(seconds=1)
        token.save(update_fields=['expires_at'])
        with self.assertRaisesRegex(TokenError, 'expired'):
            self.plugin.validate_token(secret)
        token.expires_at = None
        token.save(update_fields=['expires_at'])
        self.alice.is_active = False
        self.alice.save(update_fields=['is_active'])
        with self.assertRaisesRegex(TokenError, 'inactive'):
            self.plugin.validate_token(secret)
        self.alice.is_active = True
        self.alice.save(update_fields=['is_active'])
        token.revoked_at = timezone.now()
        token.save(update_fields=['revoked_at'])
        with self.assertRaisesRegex(TokenError, 'revoked'):
            self.plugin.validate_token(secret)
        token.revoked_at = None
        with self.assertRaises(ValidationError):
            token.save(update_fields=['revoked_at'])
        token.revoked_at = PluginAccessToken.objects.get(pk=token.pk).revoked_at
        self.config.active = False
        with self.assertRaisesRegex(TokenError, 'inactive'):
            self.plugin.validate_token(secret)
        with self.assertRaises(TokenError):
            self.plugin.create_token(kind='plugin', name='New')
        self.assertTrue(PluginAccessToken.objects.filter(pk=token.pk).exists())

    def test_plugin_without_scopes_and_wrong_plugin(self):
        token, secret = self.plugin.create_token(kind='plugin', name='Plain')
        self.plugin.TOKEN_CONFIG = {'plugin': True, 'user': False}
        self.assertEqual(self.plugin.validate_token(secret).public_id, token.public_id)
        with self.assertRaisesRegex(TokenError, 'scope'):
            self.plugin.validate_token(secret, required_scopes=['read'])
        other = ExamplePlugin()
        other.slug = 'different'
        with self.assertRaises(TokenError):
            other.validate_token(secret)

    def test_public_id_collision_retries_with_a_fresh_secret(self):
        first, _ = self.plugin.create_token(kind='plugin', name='First')
        with patch('plugin.tokens.secrets.token_urlsafe', side_effect=[first.public_id, 'discarded-secret', 'new-public-id', 'new-secret']):
            second, value = self.plugin.create_token(kind='plugin', name='Second')
        self.assertEqual(second.public_id, 'new-public-id')
        self.assertEqual(value, 'new-public-id.new-secret')

    def test_personal_tokens_are_multiple_and_do_not_authenticate_drf(self):
        one, one_secret = self.plugin.create_token(kind='user', name='One', user=self.alice)
        two, _ = self.plugin.create_token(kind='user', name='Two', user=self.alice)
        three, _ = self.plugin.create_token(kind='user', name='Three', user=self.bob)
        self.assertEqual(len({one.pk, two.pk, three.pk}), 3)
        response = self.client.get('/api/v1/plugins/token-test/tokens/user/', HTTP_AUTHORIZATION=f'Bearer {one_secret}')
        self.assertIn(response.status_code, (401, 403))

    def test_api_owner_admin_and_one_time_secret(self):
        url = '/api/v1/plugins/token-test/tokens/user/'
        self.client.force_login(self.alice)
        created = self.client.post(url, {'name': 'Alice', 'scopes': ['read']}, content_type='application/json')
        self.assertEqual(created.status_code, 201, created.content)
        secret = created.json()['token']
        self.assertEqual(created['Cache-Control'], 'no-store')
        self.assertNotIn('token', self.client.get(url).json()['tokens'][0])
        self.assertNotIn('secret_hash', str(self.client.get(url).json()))
        self.assertEqual(self.client.get('/api/v1/plugins/token-test/tokens/plugin/').status_code, 404)
        detail = url + created.json()['public_id'] + '/'
        self.client.force_login(self.bob)
        self.assertEqual(self.client.get(url).json()['tokens'], [])
        self.assertEqual(self.client.delete(detail).status_code, 404)
        self.client.force_login(self.alice)
        self.assertEqual(self.client.patch(detail, {'name': 'x' * 151}, content_type='application/json').status_code, 400)
        self.assertEqual(self.client.patch(detail, {'name': 'Renamed'}, content_type='application/json').status_code, 200)
        self.assertEqual(self.client.delete(detail).status_code, 200)
        with self.assertRaises(TokenError):
            self.plugin.validate_token(secret)
        self.client.force_login(self.staff)
        technical = self.client.post('/api/v1/plugins/token-test/tokens/plugin/', {'name': 'Service'}, content_type='application/json')
        self.assertEqual(technical.status_code, 201, technical.content)
        self.assertEqual(PluginAccessToken.objects.filter(kind='plugin').count(), 1)

    def test_admin_create_shows_secret_once_and_filters_personal_tokens(self):
        self.client.force_login(self.alice)
        self.assertEqual(self.client.get('/admin/plugin/pluginaccesstoken/add/').status_code, 302)
        self.client.force_login(self.staff)
        with patch.object(registry, 'with_mixin', return_value=[self.plugin]):
            add = '/admin/plugin/pluginaccesstoken/add/'
            page = self.client.get(add)
            self.assertEqual(page.status_code, 200)
            self.assertIsInstance(PluginTokenCreateForm().fields['expires_at'].widget, AdminSplitDateTime)
            self.assertContains(page, 'admin/js/calendar.js')
            self.assertContains(page, 'admin/js/admin/DateTimeShortcuts.js')
            response = self.client.post(add, {'plugin': self.config.pk, 'name': 'Admin token', 'scopes': ['read']})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertContains(response, 'Copy this token now')
        self.assertContains(response, 'plugin/js/token_copy.js')
        self.assertIn('no-store', response['Cache-Control'])
        token = PluginAccessToken.objects.get(kind='plugin')
        self.assertIsNone(token.expires_at)
        self.assertContains(response, token.public_id)
        raw_token = response.context['secret']
        self.assertContains(response, raw_token)
        self.assertNotContains(self.client.get(add), raw_token)
        self.assertNotContains(self.client.get('/admin/plugin/pluginaccesstoken/'), raw_token)
        self.assertNotContains(self.client.get(f'/admin/plugin/pluginaccesstoken/{token.pk}/change/'), raw_token)
        self.assertNotContains(self.client.get('/admin/plugin/pluginaccesstoken/'), token.secret_hash)
        self.plugin.create_token(kind='user', name='Personal', user=self.alice)
        changelist = self.client.get('/admin/plugin/pluginaccesstoken/')
        self.assertContains(changelist, 'Admin token')
        self.assertNotContains(changelist, 'Personal')
        self.assertContains(self.client.get('/admin/plugin/pluginaccesstoken/?token_status=active'), 'Admin token')
        self.assertNotContains(self.client.get('/admin/plugin/pluginaccesstoken/?token_status=revoked'), 'Admin token')

    def test_admin_expiration_future_and_past(self):
        self.client.force_login(self.staff)
        add = '/admin/plugin/pluginaccesstoken/add/'
        future = timezone.localtime(timezone.now() + timedelta(days=1)).replace(microsecond=0)
        payload = {'plugin': self.config.pk, 'name': 'Expiring token',
                   'expires_at_0': future.strftime('%Y-%m-%d'),
                   'expires_at_1': future.strftime('%H:%M:%S')}
        with patch.object(registry, 'with_mixin', return_value=[self.plugin]):
            created = self.client.post(add, payload)
            self.assertContains(created, 'Copy this token now')
            token = PluginAccessToken.objects.get(name='Expiring token')
            self.assertEqual(timezone.localtime(token.expires_at).replace(microsecond=0), future)
            past = timezone.localtime(timezone.now() - timedelta(days=1))
            payload.update({'name': 'Past token', 'expires_at_0': past.strftime('%Y-%m-%d'),
                            'expires_at_1': past.strftime('%H:%M:%S')})
            rejected = self.client.post(add, payload)
        self.assertContains(rejected, 'Expiration must be in the future.')
        self.assertFalse(PluginAccessToken.objects.filter(name='Past token').exists())
