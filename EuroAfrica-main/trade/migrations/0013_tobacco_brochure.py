from django.db import migrations, models
import trade.validators


def initialize_tobacco_media(apps, schema_editor):
    Category = apps.get_model('trade', 'TradeCategory')
    manager = Category.objects.using(schema_editor.connection.alias)
    category = manager.filter(seed_key='tobacco-products').first() or manager.filter(slug='tobacco-products').first()
    if not category:
        return
    updates = {}
    if not category.hero_image:
        updates['hero_image'] = 'content/tobacco-section.jpeg'
    if not category.brochure:
        updates['brochure'] = 'brochures/tobacco-catalogue.pdf'
    if updates:
        manager.filter(pk=category.pk).update(**updates)


class Migration(migrations.Migration):
    dependencies = [('trade', '0012_office_contact_details')]

    operations = [
        migrations.AddField(
            model_name='tradecategory',
            name='brochure',
            field=models.FileField(
                blank=True,
                help_text='Optional PDF document; maximum 25 MB.',
                upload_to='brochures/%Y/%m/',
                validators=[trade.validators.validate_pdf],
                verbose_name='Brochure / PDF',
            ),
        ),
        migrations.RunPython(initialize_tobacco_media, migrations.RunPython.noop),
    ]
