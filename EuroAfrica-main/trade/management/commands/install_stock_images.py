"""Install licensed starter imagery only in empty content-image fields."""
import json
from pathlib import Path
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from trade.models import HomePage, TradeDirection, TradeCategory, ContentPage


class Command(BaseCommand):
    help = 'Fill empty image fields with bundled licensed stock photographs; preserve existing images and text.'

    def handle(self, *args, **options):
        folder = Path(settings.BASE_DIR) / 'assets/stock'
        manifest = {item['key']: item for item in json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))}
        homepage = HomePage.objects.first()
        targets = [(homepage, 'hero', 'trade'), (homepage, 'diversity', 'handicrafts-textiles')]
        targets += [(obj, 'image', 'fresh-fruits-vegetables' if obj.seed_key == 'africa-to-europe' else 'electrical-equipment-technology') for obj in TradeDirection.objects.all() if obj.seed_key in ('africa-to-europe', 'europe-to-africa')]
        targets += [(obj, 'image', obj.seed_key) for obj in TradeCategory.objects.all() if obj.seed_key in manifest]
        targets += [(obj, 'image', 'trade') for obj in ContentPage.objects.filter(slug='about')]
        count = 0
        for obj, prefix, key in targets:
            field = prefix if prefix == 'image' else prefix + '_image'
            if not obj or getattr(obj, field):
                continue
            item = manifest[key]
            setattr(obj, field, ContentFile((folder / item['file']).read_bytes(), name=item['file']))
            for suffix, value in [('alt', item['alt']), ('caption', f"Illustrative photograph by {item['author']} / Unsplash.")]:
                attribute = prefix + '_' + suffix
                if not getattr(obj, attribute):
                    setattr(obj, attribute, value)
            obj.save()
            count += 1
        self.stdout.write(self.style.SUCCESS(f'Added {count} images to empty fields. Existing images and copy preserved.'))
