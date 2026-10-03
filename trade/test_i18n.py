from io import StringIO
from unittest.mock import patch
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.utils.translation import gettext, override
from .models import HomePage, TradeCategory, TradeDirection, Enquiry, ContentPage
from .test_helpers import enquiry_data


@override_settings(DEBUG=True, STAGING=False, SECURE_SSL_REDIRECT=False,
                   TURNSTILE_SITE_KEY='', TURNSTILE_SECRET_KEY='',
                   CONTACT_NOTIFICATION_EMAIL='', LANGUAGE_COOKIE_SECURE=False)
class LanguageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_content', stdout=StringIO())

    def test_switch_persists_and_preserves_query_and_editorial_content(self):
        paths = ['/', '/contact/', '/contact/thanks/']
        paths += [p.get_absolute_url() for p in ContentPage.objects.filter(published=True)]
        paths += [d.get_absolute_url() for d in TradeDirection.objects.filter(published=True)]
        paths += [c.get_absolute_url() for c in TradeCategory.objects.filter(published=True, direction__published=True)]
        for lang, home in [('en', 'Home'), ('ar', 'الرئيسية'), ('hu', 'Kezdőlap'), ('uk', 'Головна'), ('fr', 'Accueil'), ('de', 'Startseite')]:
            response = self.client.post('/i18n/setlang/', {'language':lang, 'next':'/contact/?category=1&interest=general'})
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response['Location'], '/contact/?category=1&interest=general')
            self.assertEqual(response.cookies['django_language'].value, lang)
            for path in paths:
                with self.subTest(language=lang, path=path):
                    page = self.client.get(path)
                    self.assertEqual(page.status_code, 200)
                    self.assertContains(page, f'lang="{lang}" dir="{"rtl" if lang == "ar" else "ltr"}"')
                    self.assertContains(page, home)
                    self.assertEqual(page['Content-Language'], lang)
                    self.assertNotContains(page, 'hreflang=')
                    for native in ['English', 'العربية', 'Magyar', 'Українська', 'Français', 'Deutsch']:
                        self.assertContains(page, native)
            with override(lang):
                self.assertContains(self.client.get('/'), HomePage.objects.get(pk=1).translated['hero_heading'])

    def test_language_form_csrf_and_external_next(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post('/i18n/setlang/', {'language':'ar'}).status_code, 403)
        client.get('/contact/')
        response = client.post('/i18n/setlang/', {'language':'ar', 'next':'https://attacker.example/', 'csrfmiddlewaretoken':client.cookies['csrftoken'].value})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/')

    def test_unsupported_language_does_not_replace_selected_language(self):
        self.client.post('/i18n/setlang/', {'language':'fr', 'next':'/'})
        self.client.post('/i18n/setlang/', {'language':'invalid', 'next':'/'})
        self.assertEqual(self.client.get('/')['Content-Language'], 'fr')

    def test_translated_form_and_submission(self):
        for language in ['ar', 'hu', 'uk', 'fr', 'de']:
            self.client.post('/i18n/setlang/', {'language':language, 'next':'/contact/'})
            with override(language):
                self.assertContains(self.client.get('/contact/'), gettext('Full name'))
            response = self.client.post('/contact/', enquiry_data(email=f'{language}@example.org'))
            self.assertRedirects(response, '/contact/thanks/')
        self.assertEqual(Enquiry.objects.count(), 5)

    def test_rate_limit_retry_header_does_not_depend_on_translation(self):
        self.client.post('/i18n/setlang/', {'language':'ar', 'next':'/contact/'})
        with patch('trade.antispam.rate_allowed', return_value=False):
            response = self.client.post('/contact/', enquiry_data())
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response['Retry-After'], '600')

    def test_unknown_editor_labels_fall_back_and_are_escaped(self):
        TradeDirection.objects.filter(published=True).update(title='<custom & direction>')
        self.client.post('/i18n/setlang/', {'language':'ar', 'next':'/'})
        self.assertContains(self.client.get('/'), '&lt;custom &amp; direction&gt;')
        self.assertNotContains(self.client.get('/'), '<custom & direction>')

    @override_settings(DEBUG=False, SITE_URL='https://www.euroafrica.example', ALLOWED_HOSTS=['www.euroafrica.example'])
    def test_translated_404(self):
        self.client.cookies['django_language'] = 'de'
        response = self.client.get('/not-a-published-page/', secure=True, HTTP_HOST='www.euroafrica.example')
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, 'Diese Seite wurde nicht gefunden', status_code=404)
