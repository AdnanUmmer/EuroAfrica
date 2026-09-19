from urllib.parse import urlsplit
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from trade.models import ContentPage, HomePage, SiteSettings

class Command(BaseCommand):
    help = 'Fail until the production indexing and owner-content launch requirements are satisfied.'
    def handle(self, **options):
        issues = []
        from trade.antispam import turnstile_configured
        if not turnstile_configured(): issues.append('Configure real Turnstile keys before accepting live enquiries.')
        if settings.DEBUG: issues.append('DEBUG must be false.')
        if settings.STAGING: issues.append('STAGING must be false on the production site.')
        if not settings.INDEXABLE: issues.append('INDEXABLE must be true on production.')
        url = urlsplit(settings.SITE_URL)
        if url.scheme != 'https' or not url.hostname or url.hostname in ('localhost', '127.0.0.1') or url.hostname.endswith('.example'):
            issues.append('Set SITE_URL to the final HTTPS production domain.')
        if settings.DATABASES['default']['ENGINE'] != 'django.db.backends.postgresql': issues.append('Use PostgreSQL in production.')
        if not ContentPage.objects.filter(slug='privacy', published=True).exists(): issues.append('Review and publish the privacy notice before collecting live enquiries.')
        if ContentPage.objects.filter(slug='privacy', body__contains='OWNER REVIEW REQUIRED').exists(): issues.append('Replace the privacy review placeholder with the approved notice.')
        if not SiteSettings.objects.filter(pk=1).exclude(email='').exists(): issues.append('Configure a verified public contact email.')
        if not HomePage.objects.filter(pk=1).exclude(hero_image='').exists(): issues.append('Replace the homepage illustration with approved hero photography.')
        if issues: raise CommandError('\n'.join(issues))
        call_command('audit_seo', stdout=self.stdout)
        self.stdout.write(self.style.SUCCESS('Configuration checks passed. Complete live HTTP, Search Console, accessibility and performance checks in DEPLOYMENT.md.'))
