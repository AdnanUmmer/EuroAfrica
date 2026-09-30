import re
import tempfile
from io import BytesIO, StringIO
from pathlib import Path

from PIL import Image
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.forms.widgets import CheckboxInput, FileInput
from django.test import RequestFactory, TestCase, override_settings
from django.urls import path

from euroafrica.urls import urlpatterns as project_urls
from .admin import CategoryAdmin
from .media import image as media_file
from .models import TradeCategory


urlpatterns = [path('media/<path:path>', media_file)] + project_urls


@override_settings(
    DEBUG=True,
    STAGING=False,
    SITE_URL='https://euroafrica-1u37.onrender.com',
    ALLOWED_HOSTS=['testserver', 'euroafrica-1u37.onrender.com'],
    SECURE_SSL_REDIRECT=False,
    ROOT_URLCONF=__name__,
)
class TobaccoContentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_content', stdout=StringIO())
        cls.tobacco = TradeCategory.objects.get(seed_key='tobacco-products')

    def test_supplied_media_is_seeded_and_displayed(self):
        self.assertEqual(self.tobacco.hero_image.name, 'content/tobacco-section.jpeg')
        self.assertEqual(self.tobacco.brochure.name, 'brochures/tobacco-catalogue.pdf')
        self.assertTrue(self.tobacco.hero_image.storage.exists(self.tobacco.hero_image.name))
        self.assertTrue(self.tobacco.brochure.storage.exists(self.tobacco.brochure.name))
        image_response = self.client.get(self.tobacco.hero_image.url)
        self.assertEqual(image_response.status_code, 200)
        self.assertEqual(image_response['Content-Type'], 'image/jpeg')
        self.assertEqual(
            b''.join(image_response.streaming_content),
            Path(settings.MEDIA_ROOT, self.tobacco.hero_image.name).read_bytes(),
        )
        image_response.close()
        brochure_response = self.client.get(self.tobacco.brochure.url)
        self.assertEqual(brochure_response.status_code, 200)
        self.assertEqual(brochure_response['Content-Type'], 'application/pdf')
        self.assertIn('attachment', brochure_response['Content-Disposition'])
        self.assertEqual(
            b''.join(brochure_response.streaming_content),
            Path(settings.MEDIA_ROOT, self.tobacco.brochure.name).read_bytes(),
        )
        brochure_response.close()

        response = self.client.get(self.tobacco.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.tobacco.hero_image.url)
        self.assertContains(response, self.tobacco.brochure.url)
        self.assertContains(response, 'Download Brochure')
        hero = response.content.decode().split('<section class="category-hero', 1)[1].split('</section>', 1)[0]
        self.assertRegex(hero, re.compile(r'<div class="visual category-art tobacco-art">.*?src="/media/content/tobacco-section\.jpeg"', re.S))
        self.assertNotIn('illustration.svg', hero)

    def test_uploaded_category_image_is_used_in_cards(self):
        response = self.client.get(self.tobacco.direction.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.tobacco.hero_image.url)

    def test_brochure_is_optional_on_frontend(self):
        TradeCategory.objects.filter(pk=self.tobacco.pk).update(brochure='')
        response = self.client.get(self.tobacco.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Download Brochure')
        self.assertNotContains(response, 'href=""')

    def test_brochure_field_is_only_in_tobacco_admin(self):
        category_admin = CategoryAdmin(TradeCategory, admin.site)
        request = RequestFactory().get('/admin/trade/tradecategory/')
        request.user = AnonymousUser()

        def fields_for(obj):
            return [
                field
                for _, options in category_admin.get_fieldsets(request, obj)
                for field in options['fields']
            ]

        self.assertIn('brochure', fields_for(self.tobacco))
        another = TradeCategory.objects.exclude(pk=self.tobacco.pk).first()
        self.assertNotIn('brochure', fields_for(another))
        tobacco_form = category_admin.get_form(request, self.tobacco)
        self.assertEqual(tobacco_form.base_fields['hero_image'].label, 'Tobacco section image')

    def test_admin_managed_image_and_pdf_can_be_replaced_and_cleared(self):
        image_bytes = BytesIO()
        Image.new('RGB', (60, 90), 'black').save(image_bytes, format='JPEG')
        pdf_bytes = b'%PDF-1.7\nreplacement brochure\n%%EOF'
        with tempfile.TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            category = TradeCategory.objects.get(pk=self.tobacco.pk)
            category.hero_image = SimpleUploadedFile('replacement.jpeg', image_bytes.getvalue(), content_type='image/jpeg')
            category.brochure = SimpleUploadedFile('replacement.pdf', pdf_bytes, content_type='application/pdf')
            category.full_clean()
            category.save()
            category.refresh_from_db()
            image_name = category.hero_image.name
            brochure_name = category.brochure.name
            self.assertTrue(category.hero_image.storage.exists(image_name))
            self.assertTrue(category.brochure.storage.exists(brochure_name))
            self.assertTrue(image_name.endswith('.webp'))
            self.assertEqual(category.hero_image.width / category.hero_image.height, 2 / 3)
            self.assertEqual(Path(directory, brochure_name).read_bytes(), pdf_bytes)

            category.hero_image = ''
            category.brochure = ''
            category.save()
            category.refresh_from_db()
            self.assertFalse(category.hero_image)
            self.assertFalse(category.brochure)

    def test_admin_change_form_replaces_and_removes_image_and_brochure(self):
        user = get_user_model().objects.create_superuser('tobacco-admin', 'admin@example.org', 'Secure-Test-Password42!')
        self.client.force_login(user)
        url = f'/admin/trade/tradecategory/{self.tobacco.pk}/change/'

        def current_form_data():
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            form = response.context['adminform'].form
            data = {}
            for name, field in form.fields.items():
                if isinstance(field.widget, FileInput):
                    continue
                value = form[name].value()
                if value is None:
                    continue
                data[name] = ('on' if value else '') if isinstance(field.widget, CheckboxInput) else value
            for prefix in ('products', 'sections', 'gallery'):
                data.update({
                    f'{prefix}-TOTAL_FORMS': '0',
                    f'{prefix}-INITIAL_FORMS': '0',
                    f'{prefix}-MIN_NUM_FORMS': '0',
                    f'{prefix}-MAX_NUM_FORMS': '1000',
                })
            data['_save'] = 'Save'
            return data

        image_bytes = BytesIO()
        Image.new('RGB', (72, 108), 'black').save(image_bytes, format='JPEG')
        pdf_bytes = Path(settings.BASE_DIR, 'media', 'brochures', 'tobacco-catalogue.pdf').read_bytes()
        original_image = self.tobacco.hero_image.name
        original_brochure = self.tobacco.brochure.name
        with tempfile.TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            response = self.client.post(url, {
                **current_form_data(),
                'hero_image': SimpleUploadedFile('admin-image.jpeg', image_bytes.getvalue(), content_type='image/jpeg'),
                'brochure': SimpleUploadedFile('admin-brochure.pdf', pdf_bytes, content_type='application/pdf'),
            })
            self.assertEqual(response.status_code, 302, getattr(response, 'context', None))
            self.tobacco.refresh_from_db()
            self.assertNotEqual(self.tobacco.hero_image.name, original_image)
            self.assertNotEqual(self.tobacco.brochure.name, original_brochure)
            self.assertTrue(self.tobacco.hero_image.storage.exists(self.tobacco.hero_image.name))
            self.assertEqual(Path(directory, self.tobacco.brochure.name).read_bytes(), pdf_bytes)
            public_page = self.client.get(self.tobacco.get_absolute_url())
            self.assertContains(public_page, self.tobacco.hero_image.url)
            self.assertContains(public_page, self.tobacco.brochure.url)
            self.assertContains(public_page, 'Download Brochure')

            response = self.client.post(url, {
                **current_form_data(),
                'hero_image-clear': 'on',
                'brochure-clear': 'on',
            })
            self.assertEqual(response.status_code, 302, getattr(response, 'context', None))
            self.tobacco.refresh_from_db()
            self.assertFalse(self.tobacco.hero_image)
            self.assertFalse(self.tobacco.brochure)
            public_page = self.client.get(self.tobacco.get_absolute_url())
            self.assertNotContains(public_page, 'Download Brochure')

    def test_non_pdf_and_misnamed_uploads_are_rejected(self):
        category = TradeCategory.objects.get(pk=self.tobacco.pk)
        category.brochure = SimpleUploadedFile('document.pdf', b'not a PDF')
        with self.assertRaises(ValidationError):
            category.full_clean()
        category.brochure = SimpleUploadedFile('document.txt', b'%PDF-1.7\n%%EOF')
        with self.assertRaises(ValidationError):
            category.full_clean()

    def test_pdf_is_served_as_download_and_unsafe_types_remain_blocked(self):
        with tempfile.TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            Path(directory, 'brochure.pdf').write_bytes(b'%PDF-1.7\n%%EOF')
            Path(directory, 'unsafe.html').write_text('<script/>', encoding='utf-8')
            response = self.client.get('/media/brochure.pdf')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response['Content-Type'], 'application/pdf')
            self.assertIn('attachment', response['Content-Disposition'])
            response.close()
            self.assertEqual(self.client.get('/media/unsafe.html').status_code, 404)
