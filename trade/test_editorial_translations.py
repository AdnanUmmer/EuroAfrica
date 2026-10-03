from io import StringIO
from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils.translation import override
from .models import ContentTranslation, HomePage, TradeCategory, CategoryProduct, Enquiry
from .content_fields import CONTENT_FIELDS
from .test_helpers import enquiry_data


@override_settings(DEBUG=True, STAGING=False, SECURE_SSL_REDIRECT=False,
                   TURNSTILE_SITE_KEY='', TURNSTILE_SECRET_KEY='',
                   CONTACT_NOTIFICATION_EMAIL='')
class EditorialTranslationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_content', stdout=StringIO())
        call_command('seed_translations', stdout=StringIO())

    def test_all_published_fields_have_current_translations(self):
        call_command('audit_translations', stdout=StringIO())
        for name, fields in CONTENT_FIELDS.items():
            for obj in apps.get_model('trade', name).objects.all():
                if hasattr(obj, 'published') and not obj.published:
                    continue
                for lang in ('ar','hu','uk','fr','de'):
                    with override(lang):
                        localized=obj.translated
                        for field in fields:
                            source=getattr(obj,field)
                            if source and source!='EuroAfrica':
                                row=obj.translations.get(language=lang,field=field)
                                self.assertEqual(localized[field],row.text)
                                self.assertEqual(row.source_text,source)

    def test_category_and_form_choices_are_translated(self):
        category=TradeCategory.objects.filter(published=True).first()
        for lang in ('ar','hu','uk','fr','de'):
            self.client.cookies['django_language']=lang
            with override(lang):
                title=category.translated['title']
                text=category.translated['overview']
            response=self.client.get(category.get_absolute_url())
            self.assertContains(response,title)
            self.assertContains(response,text.split('\n\n')[-1])
            self.assertNotContains(response,category.overview)
            self.assertContains(self.client.get('/contact/'),title)
            self.assertIn('application/ld+json',response.content.decode())

    def test_new_product_translation_is_server_rendered_and_source_preserved(self):
        category=TradeCategory.objects.filter(published=True).first()
        product=CategoryProduct.objects.create(category=category,name='Example item',description='Original product description.')
        ct=ContentType.objects.get_for_model(product)
        for field,text in [('name','Exemple de produit'),('description','Description française du produit.')]:
            ContentTranslation.objects.create(content_type=ct,object_id=product.pk,language='fr',field=field,text=text,source_text=getattr(product,field))
        self.client.cookies['django_language']='fr'
        response=self.client.get(category.get_absolute_url())
        self.assertContains(response,'Description française du produit.')
        self.assertNotContains(response,'Original product description.')
        product.refresh_from_db()
        self.assertEqual(product.description,'Original product description.')

    def test_stale_translation_falls_back_and_import_preserves_edits(self):
        home=HomePage.objects.get(pk=1)
        row=home.translations.get(language='fr',field='hero_heading')
        row.text='Texte édité';row.save()
        call_command('seed_translations',stdout=StringIO())
        row.refresh_from_db();self.assertEqual(row.text,'Texte édité')
        HomePage.objects.filter(pk=1).update(hero_heading='New owner heading')
        with override('fr'):
            self.assertEqual(HomePage.objects.get(pk=1).translated['hero_heading'],'New owner heading')

    def test_translated_html_is_escaped(self):
        home=HomePage.objects.get(pk=1)
        home.translations.filter(language='de',field='hero_heading').update(text='<script>alert(1)</script>')
        self.client.cookies['django_language']='de'
        self.assertContains(self.client.get('/'),'&lt;script&gt;alert(1)&lt;/script&gt;')
        self.assertNotContains(self.client.get('/'),'<script>alert(1)</script>')

    def test_seed_is_idempotent_and_does_not_touch_enquiries(self):
        enquiry=Enquiry.objects.create(name='Existing',email='existing@example.org',message='Retain this')
        count=ContentTranslation.objects.count()
        call_command('seed_translations',stdout=StringIO())
        self.assertEqual(ContentTranslation.objects.count(),count)
        enquiry.refresh_from_db();self.assertEqual(enquiry.message,'Retain this')
        for obj in TradeCategory.objects.filter(published=True):
            self.assertGreaterEqual(len(obj.overview.split()),70)

    def test_admin_can_edit_a_translation_without_altering_english(self):
        user=get_user_model().objects.create_user('translation-test',is_staff=True,is_superuser=True)
        self.client.force_login(user)
        home=HomePage.objects.get(pk=1)
        row=home.translations.get(language='fr',field='hero_heading')
        url=f'/admin/trade/contenttranslation/{row.pk}/change/'
        self.assertEqual(self.client.get(url).status_code,200)
        response=self.client.post(url,{'target':'homepage:1','language':'fr','field':'hero_heading','text':'Nouveau titre français','_save':'Save'})
        self.assertEqual(response.status_code,302)
        row.refresh_from_db();self.assertEqual(row.text,'Nouveau titre français')
        self.assertEqual(HomePage.objects.get(pk=1).hero_heading,home.hero_heading)

    def test_enquiry_survives_every_language(self):
        for lang in ('en','ar','hu','uk','fr','de'):
            self.client.cookies['django_language']=lang
            response=self.client.post('/contact/',enquiry_data(email=f'{lang}@example.org',message=f'Question {lang}'))
            self.assertEqual(response.status_code,302)
            self.assertEqual(response['Location'],'/contact/thanks/')
        self.assertEqual(Enquiry.objects.count(),6)
