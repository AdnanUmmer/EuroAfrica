"""Read-only mapping of database file references; safe to run in Render Shell."""
import json
from django.apps import apps
from django.db.models import FileField
from django.core.management.base import BaseCommand
from django.test import Client
from django.conf import settings
from urllib.parse import urlsplit


class Command(BaseCommand):
    help = 'Report file references, missing originals/derivatives and optional in-process HTTP checks. Does not modify data.'

    def add_arguments(self, parser):
        parser.add_argument('--http', action='store_true')

    def handle(self, **options):
        from trade.templatetags.trade_images import image_srcset
        client = Client(HTTP_HOST=urlsplit(settings.SITE_URL).netloc, HTTP_X_FORWARDED_PROTO='https')
        rows = []
        for model in apps.get_app_config('trade').get_models():
            fields = [field for field in model._meta.fields if isinstance(field, FileField)]
            if not fields: continue
            for obj in model.objects.all():
                for field in fields:
                    file = getattr(obj, field.name)
                    if not file: continue
                    row = dict(model=model.__name__, pk=obj.pk, field=field.name, database=file.name,
                               filesystem=file.path, url=file.url, exists=file.storage.exists(file.name))
                    row['srcset'] = image_srcset(file)
                    if options['http']:
                        response = client.get(file.url, secure=True)
                        row.update(status=response.status_code, content_type=response.get('Content-Type'))
                        response.close()
                    rows.append(row)
        self.stdout.write(json.dumps({'database_engine':settings.DATABASES['default']['ENGINE'], 'media_root':str(settings.MEDIA_ROOT), 'files':rows}, indent=2))
