from django.db import migrations

def add_footer_links(apps, schema_editor):
    FooterLink = apps.get_model('trade', 'FooterLink')
    if FooterLink.objects.exists(): return
    for i, (label, destination, group) in enumerate([
        ('Home', '/', 'explore'), ('About EuroAfrica', '/about/', 'explore'), ('Contact', '/contact/', 'explore'),
        ('Africa to Europe', '/africa-to-europe/', 'trade'), ('Europe to Africa', '/europe-to-africa/', 'trade'),
        ('Privacy notice', '/privacy/', 'legal')]):
        FooterLink.objects.create(label=label, destination=destination, group=group, order=i)

class Migration(migrations.Migration):
    dependencies = [('trade', '0004_footerlink_alter_sitesettings_options_and_more')]
    operations = [migrations.RunPython(add_footer_links, migrations.RunPython.noop)]
