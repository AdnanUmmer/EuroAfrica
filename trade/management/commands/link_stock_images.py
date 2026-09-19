"""Link committed, verified default photos without writing to the filesystem."""
import json
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from trade.models import HomePage, TradeDirection, TradeCategory, ContentPage, StockImageInitialization


class Command(BaseCommand):
    help = 'Initialize default image references once; preserve owner uploads and subsequent clears.'

    def handle(self, **options):
        manifest = json.loads((Path(settings.BASE_DIR) / 'assets/stock/bindings.json').read_text(encoding='utf-8'))
        home = HomePage.objects.first()
        targets = [(home, 'hero', 'trade'), (home, 'diversity', 'handicrafts-textiles')]
        targets += [(obj, 'image', 'fresh-fruits-vegetables' if obj.seed_key == 'africa-to-europe' else 'electrical-equipment-technology') for obj in TradeDirection.objects.filter(seed_key__in=['africa-to-europe','europe-to-africa'])]
        targets += [(obj, 'image', obj.seed_key) for obj in TradeCategory.objects.filter(seed_key__in=manifest)]
        targets += [(obj, 'image', 'trade') for obj in ContentPage.objects.filter(slug='about')]
        changed = 0
        for obj, prefix, key in targets:
            if not obj: continue
            field = prefix if prefix == 'image' else prefix + '_image'
            item = manifest[key]
            # Only repository files verified as stock are eligible. No uploads,
            # conversion, directory creation or /var/data access during build.
            if not (Path(settings.BASE_DIR) / 'media' / item['path']).is_file():
                self.stderr.write(f'Missing bundled stock file for {key}; skipped.')
                continue
            with transaction.atomic():
                fresh = type(obj).objects.select_for_update().get(pk=obj.pk)
                _, first = StockImageInitialization.objects.get_or_create(key=f'{obj._meta.model_name}:{obj.pk}:{field}')
                current = getattr(fresh, field)
                repair_known = current.name in item['known_paths'] and not current.storage.exists(current.name)
                if not ((first and not current) or repair_known): continue
                updates = {field: item['path']}
                for suffix, value in [('alt', item['alt']), ('caption', f"Illustrative photograph by {item['author']} / Unsplash.")]:
                    attribute = prefix + '_' + suffix
                    if not getattr(fresh, attribute): updates[attribute] = value
                # Assign the committed filename, avoiding the upload UUID signal.
                from django.utils import timezone
                updates['updated_at'] = timezone.now()
                type(obj).objects.filter(pk=obj.pk).update(**updates)
                changed += 1
        self.stdout.write(f'Linked {changed} default images; owner files and later clears preserved.')
