"""Isolated production-mode application/static smoke test, not an infrastructure test.

Uses a disposable SQLite database; does NOT establish PostgreSQL or Nginx readiness.
Run check_production.py first to build the static manifest.
"""
import os
import secrets
import sys
import tempfile
from pathlib import Path
from io import StringIO

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.update(DJANGO_SETTINGS_MODULE='euroafrica.settings', DEBUG='false',
    SECRET_KEY=secrets.token_urlsafe(64), DATABASE_URL='postgresql://check:unused@127.0.0.1/check',
    SITE_URL='https://www.euroafrica.example', ALLOWED_HOSTS='www.euroafrica.example',
    STAGING='false', INDEXABLE='true')
from django.conf import settings
with tempfile.TemporaryDirectory() as directory:
    settings.DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': str(Path(directory) / 'test.sqlite3')}}
    settings.MEDIA_ROOT = Path(directory) / 'media'
    import django
    django.setup()
    from django.core.management import call_command
    from django.test import Client
    from django.contrib.staticfiles.storage import staticfiles_storage
    call_command('migrate', stdout=StringIO(), verbosity=0)
    call_command('seed_content', stdout=StringIO())
    client = Client(HTTP_HOST='www.euroafrica.example')
    for path in ('/', '/about/', '/contact/', '/sitemap.xml', '/admin/login/'):
        response = client.get(path, secure=True)
        assert response.status_code == 200, (path, response.status_code)
    response = client.get('/does-not-exist/', secure=True)
    assert response.status_code == 404
    assert b'floating-nav' in response.content
    for asset in ('trade/site.css', 'trade/admin.css', 'trade/logo.png'):
        url = staticfiles_storage.url(asset)
        response = client.get(url, secure=True)
        assert response.status_code == 200, (url, response.status_code)
        assert 'max-age=' in response['Cache-Control']
        print('Hashed static file served:', url)
    print('PASS: DEBUG=false HTML, login, real 404, sitemap, WhiteNoise hashed static and caching.')
    print('Not tested: actual PostgreSQL connection, Gunicorn, Nginx media HTTP, TLS, SMTP or backup restoration.')
    from django.db import connections
    connections.close_all()
