import os
from pathlib import Path
from urllib.parse import urlparse, unquote, parse_qs
from dotenv import load_dotenv
from .config import canonical_origin

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')
ON_RENDER = os.getenv('RENDER', '').strip().lower() == 'true'
DEBUG = os.getenv('DEBUG', 'false' if ON_RENDER else 'true').strip().lower() == 'true'
SECRET_KEY = os.getenv('SECRET_KEY', 'local-development-only-not-for-deployment')
SITE_URL = canonical_origin(os.getenv('SITE_URL', 'http://127.0.0.1:8000'), production=not DEBUG)
INDEXABLE = os.getenv('INDEXABLE', 'false').lower() == 'true'
STAGING = os.getenv('STAGING', 'false').lower() == 'true'
STAGING_USER = os.getenv('STAGING_USER', '')
STAGING_PASSWORD = os.getenv('STAGING_PASSWORD', '')
GSC_VERIFICATION = os.getenv('GSC_VERIFICATION', '')
ALLOWED_HOSTS = [host.strip().lower().rstrip('.') for host in os.getenv('ALLOWED_HOSTS', '127.0.0.1,localhost,testserver').split(',') if host.strip()]
if not DEBUG and (len(SECRET_KEY) < 50 or len(set(SECRET_KEY)) < 5 or SECRET_KEY.startswith(('local-', 'replace-', 'django-insecure-')) or not os.getenv('DATABASE_URL')):
    raise ValueError('Production requires a unique random SECRET_KEY (50+ characters) and PostgreSQL DATABASE_URL')
if not DEBUG and (urlparse(SITE_URL).scheme != 'https' or '*' in ALLOWED_HOSTS or 'testserver' in ALLOWED_HOSTS):
    raise ValueError('Production requires HTTPS SITE_URL and explicit ALLOWED_HOSTS without testserver')
if not DEBUG and urlparse(SITE_URL).hostname not in ALLOWED_HOSTS:
    raise ValueError('The canonical SITE_URL hostname must be included in ALLOWED_HOSTS')
if STAGING and not (STAGING_USER and STAGING_PASSWORD):
    raise ValueError('Staging requires HTTP Basic authentication credentials')
INSTALLED_APPS = ['trade.apps.EuroAfricaAdminConfig', 'django.contrib.auth', 'django.contrib.contenttypes', 'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles', 'trade.apps.TradeConfig']
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware', 'whitenoise.middleware.WhiteNoiseMiddleware', 'django.contrib.sessions.middleware.SessionMiddleware', 'django.middleware.common.CommonMiddleware', 'django.middleware.csrf.CsrfViewMiddleware', 'django.contrib.auth.middleware.AuthenticationMiddleware', 'trade.middleware.SiteMiddleware', 'django.contrib.messages.middleware.MessageMiddleware', 'django.middleware.clickjacking.XFrameOptionsMiddleware']
ROOT_URLCONF = 'euroafrica.urls'
if DEBUG:
    MIDDLEWARE.remove('whitenoise.middleware.WhiteNoiseMiddleware')
TEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': [BASE_DIR / 'trade/templates'], 'APP_DIRS': True, 'OPTIONS': {'context_processors': ['django.template.context_processors.request', 'django.contrib.auth.context_processors.auth', 'django.contrib.messages.context_processors.messages', 'trade.context.site']}}]
WSGI_APPLICATION = 'euroafrica.wsgi.application'
if DEBUG:
    TEMPLATES[0]['APP_DIRS'] = False
    TEMPLATES[0]['OPTIONS']['loaders'] = [
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
    ]
db = os.getenv('DATABASE_URL')
if db:
    u = urlparse(db)
    if u.scheme not in ('postgres', 'postgresql'):
        raise ValueError('DATABASE_URL must use PostgreSQL')
    DATABASES = {'default': {'ENGINE': 'django.db.backends.postgresql', 'NAME': u.path.lstrip('/'), 'USER': unquote(u.username or ''), 'PASSWORD': unquote(u.password or ''), 'HOST': u.hostname, 'PORT': u.port or 5432, 'CONN_MAX_AGE': 60}}
    DATABASES['default']['OPTIONS'] = {key: values[-1] for key, values in parse_qs(u.query).items() if key in ('sslmode', 'sslrootcert', 'connect_timeout')}
else:
    DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}
AUTH_PASSWORD_VALIDATORS = [{'NAME': 'django.contrib.auth.password_validation.' + n} for n in ['UserAttributeSimilarityValidator', 'MinimumLengthValidator', 'CommonPasswordValidator', 'NumericPasswordValidator']]
LANGUAGE_CODE = 'en-gb'
TIME_ZONE = 'UTC'
USE_TZ = True
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = Path(os.getenv('MEDIA_ROOT') or BASE_DIR / 'media')
STORAGES = {'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'}, 'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage' if not DEBUG else 'django.contrib.staticfiles.storage.StaticFilesStorage'}}
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGIN_URL = '/admin/login/'
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend' if os.getenv('EMAIL_HOST') else ('django.core.mail.backends.console.EmailBackend' if DEBUG else 'django.core.mail.backends.smtp.EmailBackend'))
EMAIL_HOST = os.getenv('EMAIL_HOST', '')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'true').lower() == 'true'
EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', 'false').lower() == 'true'
EMAIL_TIMEOUT = 10
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'webmaster@localhost')
SERVER_EMAIL = os.getenv('SERVER_EMAIL', DEFAULT_FROM_EMAIL)
ENQUIRY_EMAIL = os.getenv('ENQUIRY_EMAIL', '')
CONTACT_NOTIFICATION_EMAIL = os.getenv('CONTACT_NOTIFICATION_EMAIL', ENQUIRY_EMAIL)
PASSWORD_RESET_TIMEOUT = 3600
if EMAIL_USE_TLS and EMAIL_USE_SSL:
    raise ValueError('Enable EMAIL_USE_TLS or EMAIL_USE_SSL, not both')
SECURE_SSL_REDIRECT = not DEBUG
SECURE_SSL_HOST = urlparse(SITE_URL).netloc if not DEBUG else None
USE_X_FORWARDED_HOST = False
PREPEND_WWW = False
APPEND_SLASH = True
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv('HSTS_INCLUDE_SUBDOMAINS', 'false').lower() == 'true'
SECURE_HSTS_PRELOAD = os.getenv('HSTS_PRELOAD', 'false').lower() == 'true'
SECURE_CONTENT_TYPE_NOSNIFF = True
TRUST_LOCAL_PROXY = os.getenv('TRUST_LOCAL_PROXY', 'false').lower() == 'true'
if ON_RENDER or TRUST_LOCAL_PROXY:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
X_FRAME_OPTIONS = 'DENY'
CSRF_TRUSTED_ORIGINS = [canonical_origin(origin, production=not DEBUG) for origin in os.getenv('CSRF_TRUSTED_ORIGINS', SITE_URL).split(',') if origin.strip()]
SERVE_MEDIA = ON_RENDER
DATA_UPLOAD_MAX_MEMORY_SIZE = 8 * 1024 * 1024

# No traceback email handler or request payload formatter: alerts contain event identifiers only.
LOGGING = {
    'version': 1, 'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'loggers': {
        'django': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False},
        'trade': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False},
    },
}
