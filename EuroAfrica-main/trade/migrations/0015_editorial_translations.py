"""Install the reviewed multilingual release without replacing owner edits."""
import json
from pathlib import Path
from django.db import migrations


def install(apps, schema_editor):
    alias = schema_editor.connection.alias
    data = json.loads(Path(__file__).with_suffix('.json').read_text(encoding='utf-8'))
    Translation = apps.get_model('trade', 'ContentTranslation')
    ContentType = apps.get_model('contenttypes', 'ContentType')
    for name, fields in data['fields'].items():
        Model = apps.get_model('trade', name)
        ct, _ = ContentType.objects.using(alias).get_or_create(app_label='trade', model=name)
        for obj in Model.objects.using(alias).all():
            if name == 'tradecategory' and obj.overview in data['expansions']:
                obj.overview = data['expansions'][obj.overview]
                Model.objects.using(alias).filter(pk=obj.pk).update(overview=obj.overview)
            for field in fields:
                source = getattr(obj, field)
                for language, text in data['translations'].get(source, {}).items():
                    Translation.objects.using(alias).get_or_create(
                        content_type_id=ct.pk, object_id=obj.pk, language=language, field=field,
                        defaults={'text': text, 'source_text': source},
                    )


class Migration(migrations.Migration):
    dependencies = [('trade', '0014_contenttranslation')]
    operations = [migrations.RunPython(install, migrations.RunPython.noop)]
