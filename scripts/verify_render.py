"""Reproduce the migration-only 404, then verify Render proxy requests on a fresh DB.
Database is disposable SQLite; production PostgreSQL configuration is left intact.
"""
import os
import secrets
import sys
import tempfile
from pathlib import Path
from io import StringIO
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.update(DJANGO_SETTINGS_MODULE='euroafrica.settings', RENDER='true', DEBUG='False',
    SECRET_KEY=secrets.token_urlsafe(64), DATABASE_URL='postgresql://check:unused@127.0.0.1/check',
    SITE_URL='https://euroafrica-1u37.onrender.com./', ALLOWED_HOSTS='euroafrica-1u37.onrender.com',
    CSRF_TRUSTED_ORIGINS='https://euroafrica-1u37.onrender.com', STAGING='false', INDEXABLE='false')
from django.conf import settings
with tempfile.TemporaryDirectory() as directory:
    settings.DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': str(Path(directory) / 'verify.sqlite3')}}
    settings.MEDIA_ROOT = Path(directory) / 'media'
    import django
    django.setup()
    from django.core.management import call_command
    from django.test import Client, override_settings
    from django.urls import resolve
    from django.contrib.staticfiles.storage import staticfiles_storage
    from django.db import connections
    from trade.models import HomePage, SiteSettings, ContactPage, TradeCategory
    from trade.views import home
    try:
        assert resolve('/').func is home
        print('PASS: / resolves to trade.views.home -> trade/home.html')
        call_command('migrate', 'auth', stdout=StringIO(), verbosity=0)
        call_command('migrate', 'trade', '0005', stdout=StringIO(), verbosity=0)
        client = Client(HTTP_HOST='euroafrica-1u37.onrender.com', HTTP_X_FORWARDED_PROTO='https')
        from django.db.migrations.executor import MigrationExecutor
        from unittest.mock import patch
        old_apps = MigrationExecutor(connections['default']).loader.project_state([('trade', '0005_footer_defaults')]).apps
        old_home = old_apps.get_model('trade', 'HomePage')
        from django.test import RequestFactory
        from django.http import Http404
        with patch('trade.views.HomePage', old_home):
            try:
                home(RequestFactory().get('/'))
            except Http404:
                pass
            else:
                raise AssertionError('Missing homepage must raise Http404')
        assert old_home.objects.count() == 0
        print('REPRODUCED: historical 0005 model, HomePage rows=0, homepage raises Http404')
        call_command('migrate', 'trade', '0007', stdout=StringIO(), verbosity=0)
        from django.db.migrations.executor import MigrationExecutor
        historical = MigrationExecutor(connections['default']).loader.project_state([('trade', '0007_stockimageinitialization')]).apps
        legacy = historical.get_model('trade', 'Enquiry').objects.create(name='Migration check', email='check@example.org', message='Preserve this enquiry', status='resolved')
        call_command('migrate', stdout=StringIO(), verbosity=0)
        from trade.models import Enquiry
        preserved = Enquiry.objects.get(pk=legacy.pk)
        assert preserved.message == 'Preserve this enquiry' and preserved.status == 'resolved' and preserved.privacy_consent_at is None
        print('PASS: new enquiry migration preserves historical enquiries/statuses without inventing consent')
        for model in (HomePage, SiteSettings, ContactPage): assert model.objects.filter(pk=1).exists()
        for path in ('/', '/contact/'):
            response = client.get(path)
            assert response.status_code == 200 and 'Location' not in response, (path,response.status_code)
            assert b'EuroAfrica' in response.content
            print(f'PASS: migrations only, proxy HTTPS GET {path} = 200, no redirect')
        obj=HomePage.objects.get(pk=1);obj.hero_heading='Owner content stays';obj.save()
        call_command('seed_content', stdout=StringIO())
        call_command('seed_content', stdout=StringIO())
        obj.refresh_from_db();assert obj.hero_heading=='Owner content stays'
        assert TradeCategory.objects.filter(published=True).count()==10
        print('PASS: content release and repeated seed preserve later edits; 10 approved categories')
        for category in TradeCategory.objects.filter(published=True).select_related('direction'):
            assert client.get(category.get_absolute_url()).status_code==200
        assert client.get('/about/').status_code==200
        assert client.get('/not-a-real-page/').status_code==404
        assert client.get('/').content.count(b'<h1>')==1
        assert b'href="https://euroafrica-1u37.onrender.com/"' in client.get('/').content
        https_response=client.get('/')
        assert 'max-age=' in https_response['Strict-Transport-Security']
        http_response=client.get('/', HTTP_X_FORWARDED_PROTO='http')
        assert http_response.status_code==301 and http_response['Location']=='https://euroafrica-1u37.onrender.com/'
        for host in ('euroafrica-1u37.onrender.com.', 'EuroAfrica-1u37.onrender.com.:443'):
            response=client.get('/', HTTP_HOST=host)
            assert response.status_code==200 and 'Location' not in response
            response=client.get('/', HTTP_HOST=host, HTTP_X_FORWARDED_PROTO='http')
            assert response.status_code==301 and response['Location']=='https://euroafrica-1u37.onrender.com/'
            assert '.com./' not in response['Location']
            final=client.get(response['Location'])
            assert final.status_code==200 and 'Location' not in final
        assert settings.SITE_URL=='https://euroafrica-1u37.onrender.com'
        assert settings.SECURE_SSL_HOST=='euroafrica-1u37.onrender.com'
        response=client.get('/', HTTP_X_FORWARDED_HOST='euroafrica-1u37.onrender.com.')
        assert response.status_code==200 and 'Location' not in response
        print('PASS: all categories/About, canonical, HSTS, unknown 404, HTTP -> correct HTTPS 301')
        print('PASS: dotted SITE_URL/Host, default HTTPS port, ignored forwarded host, one-hop HTTP chain')
        for asset in ('trade/site.css','trade/admin.css','trade/logo.png'):
            response=client.get(staticfiles_storage.url(asset));assert response.status_code==200
            assert 'max-age=' in response['Cache-Control']
            response.close()
        print('PASS: WhiteNoise hashed CSS/logo with production storage and caching')
        import json
        with override_settings(MEDIA_ROOT=settings.BASE_DIR / 'media'):
            call_command('link_stock_images', stdout=StringIO())
            call_command('link_stock_images', stdout=StringIO())
            output = StringIO()
            call_command('audit_media', http=True, stdout=output)
            report = json.loads(output.getvalue())
            assert len(report['files']) == 13
            for row in report['files']:
                assert row['exists'] and row['status'] == 200 and row['content_type'] == 'image/webp', row
                for variant in row['srcset'].split(', '):
                    if variant:
                        response = client.get(variant.split(' ')[0])
                        assert response.status_code == 200
                        response.close()
            evidence = settings.BASE_DIR / 'qa'
            evidence.mkdir(exist_ok=True)
            (evidence / 'render-media-audit.json').write_text(output.getvalue(), encoding='utf-8')
            assert b'/media/content/' in client.get('/').content
        with override_settings(INDEXABLE=True):
            call_command('audit_seo', simulate_indexing=True)
        print('PASS: 13 database image references and every emitted srcset URL return 200; repeat linking is safe')
        assert b'/admin/password_reset/' in client.get('/admin/login/').content
        assert client.get('/admin/password_reset/').status_code == 200
        print('PASS: production admin recovery routes and login link')
        from PIL import Image
        settings.MEDIA_ROOT.mkdir();Image.new('RGB',(2,2),'navy').save(settings.MEDIA_ROOT/'test.webp','WEBP')
        response=client.get('/media/test.webp');assert response.status_code==200 and response['Content-Type']=='image/webp';response.close()
        assert client.get('/media/missing.webp').status_code==404
        assert client.get('/media/../secret.webp').status_code==404
        assert client.get('/media/secret.txt').status_code==404
        print('PASS: Render media delivery; traversal, non-images and missing files rejected')
        print('NOTE: no live Render database changes; real PostgreSQL/infrastructure not exercised.')
    finally:
        connections.close_all()
