from django.test import SimpleTestCase

from labsmanager.mails import BodyTableMail, SubscriptionMail
from notification.mails import NotificationMail


class MailBodyTableTests(SimpleTestCase):
    def test_html_table_keeps_column_order_accents_and_missing_values(self):
        html = (
            '<p>Équipe</p><table><thead><tr><th>Nom</th><th>Statut</th></tr></thead>'
            '<tbody><tr><td>Chloé &amp; Zoé</td><td></td></tr>'
            '<tr><td>André</td><td>Actif</td></tr></tbody></table><p>Fin</p>'
        )

        for mail_class in (NotificationMail, SubscriptionMail):
            with self.subTest(mail_class=mail_class.__name__):
                body = mail_class().render_body(html)
                self.assertLess(body.index('Nom'), body.index('Statut'))
                self.assertIn('Chloé & Zoé', body)
                self.assertIn('André', body)
                self.assertIn(' -', body)
                self.assertIn('Fin', body)
                self.assertNotIn('<table', body)

    def test_header_only_table_and_no_table(self):
        mail = BodyTableMail()
        body = mail.render_body('<p>Avant</p><table><thead><tr><th>Nom</th></tr>'
                                '</thead><tbody></tbody></table><p>Après</p>')
        self.assertIn('Avant', body)
        self.assertIn('Nom', body)
        self.assertIn('Après', body)
        self.assertNotIn('<table', body)
        self.assertEqual(mail.render_body('<p>Sans tableau</p>'), 'Sans tableau')

    def test_escaped_table_values_survive_plain_text_conversion(self):
        html = ('<p>Avant</p><table><tr><th>Valeur</th></tr>'
                '<tr><td>&lt;script&gt;alerte &amp; test&lt;/script&gt;</td></tr>'
                '</table><p>Après</p>')
        body = BodyTableMail().render_body(html)
        self.assertIn('<script>alerte & test</script>', body)
        self.assertIn('Après', body)
        self.assertNotIn('&lt;script&gt;', body)

    def test_multiple_tables_keep_surrounding_text(self):
        html = ('<p>Premier</p><table><tr><th>A</th></tr><tr><td>1</td></tr></table>'
                '<p>Entre</p><table><tr><th>B</th></tr><tr><td>2</td></tr></table>'
                '<p>Dernier</p>')
        body = BodyTableMail().render_body(html)
        self.assertLess(body.index('Premier'), body.index('A'))
        self.assertLess(body.index('A'), body.index('Entre'))
        self.assertLess(body.index('Entre'), body.index('B'))
        self.assertLess(body.index('B'), body.index('Dernier'))
