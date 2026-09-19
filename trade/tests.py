import json
import re
from io import StringIO, BytesIO
from unittest.mock import patch
from xml.etree import ElementTree
from django.test import TestCase, SimpleTestCase, Client, override_settings
from django.core.management import call_command
from django.contrib.auth.models import User, Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from .models import *
from .validators import validate_image


class CanonicalConfigurationTests(SimpleTestCase):
    def test_render_origin_normalized(self):
        from euroafrica.config import canonical_origin
        self.assertEqual(canonical_origin(' https://EuroAfrica-1u37.onrender.com.:443/ ', production=True), 'https://euroafrica-1u37.onrender.com')

    def test_invalid_production_redirect_destinations_rejected(self):
        from euroafrica.config import canonical_origin
        from django.core.exceptions import ImproperlyConfigured
        for origin in ('https://localhost', 'https://127.0.0.1', 'https://[::1]', 'http://example.com', 'https://example.com/missing/', 'https://user:password@example.com', 'https://example.com?next=bad', 'https://example.com#fragment', 'https://bad hostname', '[https://example.com](https://example.com)'):
            with self.subTest(origin=origin), self.assertRaises(ImproperlyConfigured):
                canonical_origin(origin, production=True)

    def test_local_development_origin_remains_supported(self):
        from euroafrica.config import canonical_origin
        self.assertEqual(canonical_origin('http://127.0.0.1:8000/'), 'http://127.0.0.1:8000')

@override_settings(DEBUG=True, INDEXABLE=True, SITE_URL='https://www.euroafrica.example')
class WebsiteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_content', stdout=StringIO())
    def test_seed_structure_and_preserve_edits(self):
        self.assertEqual(list(TradeDirection.objects.values_list('categories__direction').distinct()).__len__(), 2)
        self.assertEqual(TradeCategory.objects.count(), 13)
        self.assertEqual(TradeDirection.objects.get(slug='africa-to-europe').categories.count(), 7)
        self.assertEqual(TradeDirection.objects.get(slug='europe-to-africa').categories.count(), 6)
        obj = TradeCategory.objects.first()
        obj.summary = 'Owner revision'
        obj.slug = 'owner-changed-slug'
        obj.save()
        count = CategoryProduct.objects.count()
        call_command('seed_content', stdout=StringIO())
        obj.refresh_from_db()
        self.assertEqual(obj.summary, 'Owner revision')
        self.assertEqual(TradeCategory.objects.count(), 13)
        self.assertEqual(CategoryProduct.objects.count(), count)
    def test_public_pages_metadata_and_json(self):
        paths = ['/', '/about/', '/contact/'] + [o.get_absolute_url() for o in TradeDirection.objects.all()] + [o.get_absolute_url() for o in TradeCategory.objects.all()]
        titles, descriptions = set(), set()
        for path in paths:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)
            html = response.content.decode()
            self.assertEqual(len(re.findall('<h1[ >]', html)), 1, path)
            self.assertIn(f'href="https://www.euroafrica.example{path}"', html)
            title = re.search(r'<title>(.*?)</title>', html).group(1)
            desc = re.search(r'name="description" content="(.*?)"', html).group(1)
            self.assertNotIn(title, titles)
            self.assertNotIn(desc, descriptions)
            titles.add(title); descriptions.add(desc)
            graph = json.loads(re.search(r'application/ld\+json">(.*?)</script>', html).group(1))
            self.assertTrue(all(n['@type'] in ['Organization', 'WebSite', 'BreadcrumbList'] for n in graph['@graph']))
            self.assertNotIn('nuclear reactors', html)
    def test_drafts_do_not_leak(self):
        obj = TradeCategory.objects.first()
        obj.published = False
        obj.save()
        self.assertEqual(self.client.get(obj.get_absolute_url()).status_code, 404)
        for path in ['/', obj.direction.get_absolute_url(), '/sitemap.xml', '/contact/']:
            self.assertNotContains(self.client.get(path), obj.get_absolute_url())
        self.assertEqual(self.client.get('/privacy/').status_code, 404)
        direction = TradeDirection.objects.last()
        direction.published = False
        direction.save()
        self.assertEqual(self.client.get(direction.categories.first().get_absolute_url()).status_code, 404)
    def test_preview_requires_permission(self):
        obj = TradeCategory.objects.first()
        obj.published = False; obj.save()
        path = f'/preview/tradecategory/{obj.pk}/'
        self.assertEqual(self.client.get(path).status_code, 302)
        user = User.objects.create_user('reader', password='test-only-password')
        self.client.force_login(user)
        self.assertEqual(self.client.get(path).status_code, 404)
        user.groups.add(Group.objects.get(name='Editor'))
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['X-Robots-Tag'], 'noindex, nofollow')
        self.assertIn('no-store', response['Cache-Control'])
    def test_editor_permissions_and_admin(self):
        user = User.objects.create_user('editor', password='test-only-password', is_staff=True)
        user.groups.add(Group.objects.get(name='Editor'))
        self.assertTrue(user.has_perm('trade.change_tradecategory'))
        self.assertFalse(user.has_perm('auth.change_user'))
        self.assertFalse(user.has_perm('trade.change_urlhistory'))
        self.client.force_login(user)
        for model in ['homepage', 'sitesettings', 'contactpage', 'tradecategory', 'tradedirection', 'contentpage']:
            obj = {'homepage': HomePage, 'sitesettings': SiteSettings, 'contactpage': ContactPage, 'tradecategory': TradeCategory, 'tradedirection': TradeDirection, 'contentpage': ContentPage}[model].objects.first()
            self.assertEqual(self.client.get(f'/admin/trade/{model}/{obj.pk}/change/').status_code, 200)
    def test_edits_render_and_are_escaped(self):
        home = HomePage.objects.get(pk=1)
        home.hero_heading = 'A new owner heading'
        home.hero_text = '<script>alert(1)</script>'
        home.save()
        self.assertContains(self.client.get('/'), 'A new owner heading')
        self.assertContains(self.client.get('/'), '&lt;script&gt;')
    def test_enquiry_preselection_valid_and_invalid(self):
        obj = TradeCategory.objects.first()
        self.assertContains(self.client.get('/contact/', {'category': obj.pk}), f'value="{obj.pk}" selected')
        response = self.client.post('/contact/', {'name': 'A', 'email': 'bad', 'message': 'Hello'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Enquiry.objects.count(), 0)
        response = self.client.post('/contact/', {'name': 'A', 'email': 'a@example.org', 'message': 'Hello', 'category': obj.pk})
        self.assertRedirects(response, '/contact/thanks/')
        self.assertEqual(Enquiry.objects.count(), 1)
        self.assertEqual(self.client.get('/contact/thanks/')['X-Robots-Tag'], 'noindex, nofollow')
    @override_settings(CONTACT_NOTIFICATION_EMAIL='owner@example.org')
    @patch('trade.views.send_mail', side_effect=RuntimeError('SMTP unavailable'))
    def test_email_failure_preserves_submission(self, mocked):
        response = self.client.post('/contact/', {'name': 'A', 'email': 'a@example.org', 'message': 'Hello'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Enquiry.objects.count(), 1)
        mocked.assert_called_once()
    def test_honeypot_csrf_and_rate_limit(self):
        data = {'name': 'A', 'email': 'a@example.org', 'message': 'Hello', 'website': 'spam'}
        self.client.post('/contact/', data)
        self.assertEqual(Enquiry.objects.count(), 0)
        self.assertEqual(Client(enforce_csrf_checks=True).post('/contact/', data).status_code, 403)
        for _ in range(9): self.client.post('/contact/', {})
        self.assertEqual(self.client.post('/contact/', {}).status_code, 429)
    def test_redirect_history_has_no_chains(self):
        obj = TradeCategory.objects.first()
        old = obj.get_absolute_url()
        obj.slug = 'changed-once'; obj.save()
        intermediate = obj.get_absolute_url()
        obj.slug = 'changed-twice'; obj.save()
        for path in [old, intermediate]:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 301)
            self.assertEqual(response['Location'], obj.get_absolute_url())
        direction = obj.direction
        old_category = obj.get_absolute_url()
        direction.slug = 'new-direction'; direction.save()
        obj.refresh_from_db()
        self.assertEqual(self.client.get(old_category)['Location'], obj.get_absolute_url())
        self.assertEqual(self.client.get(old)['Location'], obj.get_absolute_url())
        obj.published = False; obj.save()
        self.assertEqual(self.client.get(old).status_code, 404)
    def test_sitemap_and_noindex(self):
        root = ElementTree.fromstring(self.client.get('/sitemap.xml').content)
        self.assertEqual(len(root), 18)
        for node in root:
            self.assertTrue(node[0].text.startswith('https://www.euroafrica.example/'))
            self.assertTrue(node[1].text)
        obj = TradeCategory.objects.first(); obj.indexable = False; obj.save()
        self.assertNotContains(self.client.get('/sitemap.xml'), obj.get_absolute_url())
        self.assertEqual(self.client.get(obj.get_absolute_url())['X-Robots-Tag'], 'noindex, nofollow')
        with override_settings(INDEXABLE=False):
            self.assertEqual(len(ElementTree.fromstring(self.client.get('/sitemap.xml').content)), 0)
            self.assertContains(self.client.get('/robots.txt'), 'Disallow: /')
    def test_missing_pages_and_slash(self):
        self.assertEqual(self.client.get('/not-a-page/').status_code, 404)
        self.assertEqual(self.client.get('/africa-to-europe').status_code, 301)
        self.assertEqual(self.client.get('/pages/about/').status_code, 404)
    @override_settings(STAGING=True, STAGING_USER='test', STAGING_PASSWORD='secret')
    def test_staging_authentication(self):
        self.assertEqual(self.client.get('/').status_code, 401)
        response = self.client.get('/', HTTP_AUTHORIZATION='Basic dGVzdDpzZWNyZXQ=')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['X-Robots-Tag'], 'noindex, nofollow')
    def test_upload_validation(self):
        with self.assertRaises(ValidationError):
            validate_image(SimpleUploadedFile('bad.svg', b'<svg/>', content_type='image/svg+xml'))
    def test_admin_edit_is_public(self):
        user = User.objects.create_user('content-editor', is_staff=True)
        user.groups.add(Group.objects.get(name='Editor'))
        self.client.force_login(user)
        obj = ContentPage.objects.get(slug='about')
        response = self.client.post(f'/admin/trade/contentpage/{obj.pk}/change/', {'title': 'About our markets', 'slug': 'about', 'summary': 'Owner-edited introduction.', 'body': 'Owner-edited body.', 'published': 'on', 'indexable': 'on', 'order': 0, 'image_position': 'center', '_save': 'Save'})
        self.assertEqual(response.status_code, 302)
        self.assertContains(self.client.get('/about/'), 'Owner-edited body.')
    def test_modified_date_tracks_product_changes(self):
        obj = TradeCategory.objects.first()
        before = obj.updated_at
        product = obj.products.first(); product.name = 'Edited product'; product.save()
        obj.refresh_from_db()
        self.assertGreater(obj.updated_at, before)
    def test_upload_is_reencoded_and_responsive(self):
        import tempfile
        from PIL import Image
        from .templatetags.trade_images import image_srcset
        buffer = BytesIO(); Image.new('RGB', (1800, 1200), '#bb9659').save(buffer, 'JPEG')
        with tempfile.TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            obj = TradeCategory.objects.first()
            obj.image = SimpleUploadedFile('sample.jpg', buffer.getvalue(), content_type='image/jpeg')
            obj.save()
            self.assertTrue(obj.image.name.endswith('.webp'))
            self.assertEqual(obj.image.width, 1600)
            self.assertIn('480w', image_srcset(obj.image))
            self.assertTrue(obj.image.storage.exists(obj.image.name[:-5] + '-480.webp'))
    @override_settings(DEBUG=False, ALLOWED_HOSTS=['alternate.example', 'www.euroafrica.example'])
    def test_production_host_redirect(self):
        response = self.client.get('/about/', HTTP_HOST='alternate.example', secure=True)
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response['Location'], 'https://www.euroafrica.example/about/')
        response = self.client.get('/about/', HTTP_HOST='www.euroafrica.example', secure=True)
        self.assertEqual(response.status_code, 200)
    def test_reserved_direction_slug(self):
        obj = TradeDirection.objects.first(); obj.slug = 'contact'
        with self.assertRaises(ValidationError): obj.full_clean()

    def test_editor_upload_replacement_and_footer(self):
        import tempfile
        from PIL import Image
        user = User.objects.create_user('image-editor', is_staff=True)
        user.groups.add(Group.objects.get(name='Editor'))
        self.client.force_login(user)
        obj = ContentPage.objects.get(slug='about')
        data = {'title': obj.title, 'slug': 'about', 'summary': obj.summary, 'body': 'Edited through admin.', 'published': 'on', 'indexable': 'on', 'order': 0, 'image_position': 'top', 'image_alt': 'Test landscape', 'image_caption': 'Temporary test caption', '_save': 'Save'}
        with tempfile.TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            names = []
            for colour in ('navy', 'gold'):
                buffer = BytesIO(); Image.new('RGB', (1400, 1000), colour).save(buffer, 'JPEG')
                data['image'] = SimpleUploadedFile('replace.jpg', buffer.getvalue(), content_type='image/jpeg')
                response = self.client.post(f'/admin/trade/contentpage/{obj.pk}/change/', data)
                self.assertEqual(response.status_code, 302)
                obj.refresh_from_db(); names.append(obj.image.name)
                response = self.client.get('/about/')
                self.assertContains(response, obj.image.url)
                self.assertContains(response, 'focus-top')
                self.assertContains(response, 'Temporary test caption')
                self.assertContains(response, 'Edited through admin.')
            self.assertNotEqual(*names)
            self.assertTrue(obj.image.storage.exists(names[0]))
            self.assertContains(self.client.get('/admin/images/'), obj.image.url)
        self.assertTrue(user.has_perm('trade.change_footerlink'))
        FooterLink.objects.create(label='Custom About link', destination='/about/')
        FooterLink.objects.create(label='Private policy', destination='/privacy/')
        self.assertContains(self.client.get('/'), 'Custom About link')
        self.assertNotContains(self.client.get('/'), 'Private policy')
        self.assertEqual(self.client.get('/admin/auth/user/').status_code, 403)
        self.assertEqual(self.client.get('/admin/auth/group/').status_code, 403)

    def test_admin_dashboard_images_and_validation(self):
        user = User.objects.create_user('admin-editor', is_staff=True)
        user.groups.add(Group.objects.get(name='Editor'))
        self.client.force_login(user)
        self.assertContains(self.client.get('/admin/'), 'Published categories')
        self.assertContains(self.client.get('/admin/images/'), 'Website images')
        response = self.client.post('/admin/trade/footerlink/add/', {'label': 'Unsafe', 'destination': 'https://external.example/', 'group': 'explore', 'order': 0, 'visible': 'on'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(FooterLink.objects.filter(label='Unsafe').count(), 0)

    def test_sitemap_queries_are_bounded(self):
        from django.test.utils import CaptureQueriesContext
        from django.db import connection
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get('/sitemap.xml')
        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(queries), 7)

@override_settings(DEBUG=False, SITE_URL='https://euroafrica-1u37.onrender.com',
    ALLOWED_HOSTS=['euroafrica-1u37.onrender.com','alternate.example'],
    SECURE_SSL_REDIRECT=True, SECURE_SSL_HOST='euroafrica-1u37.onrender.com',
    SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO','https'), USE_X_FORWARDED_HOST=False,
    STAGING=False)
class RenderRedirectTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_content', stdout=StringIO())

    def test_render_https_home_200_without_self_redirect(self):
        response=self.client.get('/', HTTP_HOST='euroafrica-1u37.onrender.com', HTTP_X_FORWARDED_PROTO='https')
        self.assertEqual(response.status_code,200)
        self.assertNotIn('Location',response)

    def test_trailing_dot_and_default_port_are_safe(self):
        for host in ('euroafrica-1u37.onrender.com.', 'EuroAfrica-1u37.onrender.com.:443', 'euroafrica-1u37.onrender.com:443'):
            with self.subTest(host=host):
                response=self.client.get('/',HTTP_HOST=host,HTTP_X_FORWARDED_PROTO='https')
                self.assertEqual(response.status_code,200)
                self.assertNotIn('Location',response)

    def test_http_redirects_once_to_canonical_https(self):
        for host in ('euroafrica-1u37.onrender.com','euroafrica-1u37.onrender.com.','alternate.example'):
            with self.subTest(host=host):
                response=self.client.get('/',HTTP_HOST=host,HTTP_X_FORWARDED_PROTO='http')
                self.assertEqual(response.status_code,301)
                self.assertEqual(response['Location'],'https://euroafrica-1u37.onrender.com/')
                self.assertNotIn('.com./',response['Location'])
                final=self.client.get(response['Location'],HTTP_HOST='euroafrica-1u37.onrender.com',HTTP_X_FORWARDED_PROTO='https')
                self.assertEqual(final.status_code,200)
                self.assertNotIn('Location',final)

    @override_settings(SITE_URL='https://euroafrica-1u37.onrender.com./')
    def test_middleware_normalizes_destination_even_with_dotted_override(self):
        response=self.client.get('/?source=test',HTTP_HOST='alternate.example',HTTP_X_FORWARDED_PROTO='https')
        self.assertEqual(response.status_code,301)
        self.assertEqual(response['Location'],'https://euroafrica-1u37.onrender.com/?source=test')
        self.assertNotIn('.com./',response['Location'])

    def test_forwarded_host_cannot_supply_redirect_destination(self):
        response=self.client.get('/',HTTP_HOST='euroafrica-1u37.onrender.com',HTTP_X_FORWARDED_HOST='euroafrica-1u37.onrender.com.',HTTP_X_FORWARDED_PROTO='https')
        self.assertEqual(response.status_code,200)
        self.assertNotIn('Location',response)

    def test_unapproved_host_is_rejected(self):
        response=self.client.get('/',HTTP_HOST='unapproved.example',HTTP_X_FORWARDED_PROTO='https')
        self.assertEqual(response.status_code,400)


class RenderStartupTests(SimpleTestCase):
    def test_wsgi_starts_without_media_directory_or_disk(self):
        import os, secrets, subprocess, sys
        from pathlib import Path
        environment=os.environ.copy()
        environment.update(DEBUG='False', RENDER='true', SECRET_KEY=secrets.token_urlsafe(64),
            DATABASE_URL='postgresql://unused:unused@127.0.0.1/unused',
            SITE_URL='https://euroafrica-1u37.onrender.com./',
            ALLOWED_HOSTS='euroafrica-1u37.onrender.com',
            CSRF_TRUSTED_ORIGINS='https://euroafrica-1u37.onrender.com',STAGING='false')
        code='''
from unittest.mock import patch
with patch('dotenv.load_dotenv'), patch('pathlib.Path.mkdir', side_effect=PermissionError('No disk')), patch('os.makedirs', side_effect=PermissionError('No disk')), patch('django.core.management.call_command', side_effect=AssertionError('No startup commands')):
    from euroafrica.wsgi import application
    from django.conf import settings
    assert callable(application)
    assert settings.SITE_URL == 'https://euroafrica-1u37.onrender.com'
    assert settings.SECURE_SSL_HOST == 'euroafrica-1u37.onrender.com'
    assert settings.SECURE_PROXY_SSL_HEADER == ('HTTP_X_FORWARDED_PROTO', 'https')
    assert settings.USE_X_FORWARDED_HOST is False
    print('WSGI startup passed without filesystem writes')
'''
        for media_root in (None, '/var/data/media'):
            with self.subTest(media_root=media_root):
                if media_root is None: environment.pop('MEDIA_ROOT',None)
                else: environment['MEDIA_ROOT']=media_root
                result=subprocess.run([sys.executable,'-c',code],cwd=Path(__file__).resolve().parent.parent,env=environment,capture_output=True,text=True,timeout=30)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_start_script_only_executes_gunicorn(self):
        from pathlib import Path
        source=(Path(__file__).resolve().parent.parent/'start.sh').read_text(encoding='utf-8')
        commands=[line for line in source.splitlines() if line.strip() and not line.startswith('#')]
        self.assertEqual(commands,['set -o errexit','exec gunicorn euroafrica.wsgi:application --bind "0.0.0.0:${PORT:-10000}"'])
