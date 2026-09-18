from django.db import migrations


def ensure_required_content(apps, schema_editor):
    # Schema creation alone previously left / and /contact/ returning 404.
    # Historical model defaults are frozen in preceding migrations. Never update
    # existing records or seed an owner's deleted categories during migration.
    for name in ('SiteSettings', 'HomePage', 'ContactPage'):
        apps.get_model('trade', name).objects.using(schema_editor.connection.alias).get_or_create(pk=1)


class Migration(migrations.Migration):
    dependencies = [('trade', '0005_footer_defaults')]
    operations = [migrations.RunPython(ensure_required_content, migrations.RunPython.noop)]
