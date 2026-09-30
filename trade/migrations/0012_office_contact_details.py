from django.db import migrations, models


def update_contacts(apps, schema_editor):
    SiteSettings = apps.get_model('trade', 'SiteSettings')
    SiteSettings.objects.using(schema_editor.connection.alias).update_or_create(
        pk=1,
        defaults={
            'phone': '+36 30 369 6643',
            'address': 'Budapest, Hungary',
            'africa_phone': '+254727909090',
            'africa_address': 'Nairobi, Kenya',
        },
    )


class Migration(migrations.Migration):
    dependencies = [('trade', '0011_approved_website_content')]
    operations = [
        migrations.AlterField(model_name='sitesettings', name='phone', field=models.CharField('headquarters phone', max_length=60, blank=True, default='+36 30 369 6643')),
        migrations.AlterField(model_name='sitesettings', name='address', field=models.TextField('headquarters address', blank=True, default='Budapest, Hungary')),
        migrations.AddField(model_name='sitesettings', name='africa_phone', field=models.CharField('Africa office phone', max_length=60, blank=True, default='+254727909090')),
        migrations.AddField(model_name='sitesettings', name='africa_address', field=models.TextField('Africa office address', blank=True, default='Nairobi, Kenya')),
        migrations.RunPython(update_contacts, migrations.RunPython.noop),
    ]
