from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from trade.content_fields import CONTENT_FIELDS
from django.conf import settings


class Command(BaseCommand):
    help = 'Report missing or stale translations in public editorial content.'

    def handle(self, *args, **options):
        missing=[]; checked=0
        for name, fields in CONTENT_FIELDS.items():
            for obj in apps.get_model('trade',name).objects.all():
                if hasattr(obj,'published') and not obj.published:continue
                parent=getattr(obj,'category',None) or getattr(obj,'page',None)
                if parent and not parent.published:continue
                if name=='footerlink' and not obj.visible:continue
                rows={(r.language,r.field):r for r in obj.translations.all()}
                for field in fields:
                    source=getattr(obj,field)
                    if not source or source=='EuroAfrica':continue
                    for language,_ in settings.LANGUAGES:
                        if language=='en':continue
                        checked+=1
                        row=rows.get((language,field))
                        if not row or not row.text.strip() or row.source_text!=source:
                            missing.append(f'{name} #{obj.pk}: {field} ({language})')
        if missing:
            raise CommandError('Missing or stale translations:\n'+'\n'.join(missing))
        self.stdout.write(self.style.SUCCESS(f'{checked} public field translations checked; no missing or stale translations.'))
