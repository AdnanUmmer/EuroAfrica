import json
import re
import tempfile
from datetime import timedelta
from io import BytesIO, StringIO
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.models import User, Group
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, Client, override_settings
from django.urls import path
from euroafrica.urls import urlpatterns as project_urls
from .media import image as media_image
from .test_helpers import enquiry_data
from .models import HomePage, TradeCategory, TradeDirection, Enquiry, StockImageInitialization
from .templatetags.trade_images import image_srcset

urlpatterns = [path('media/<path:path>', media_image)] + project_urls

@override_settings(DEBUG=True, STAGING=False, SITE_URL='https://euroafrica-1u37.onrender.com',
    ALLOWED_HOSTS=['testserver','euroafrica-1u37.onrender.com'], SECURE_SSL_REDIRECT=False,
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend', DEFAULT_FROM_EMAIL='sender@example.org')
class RecoveryAndEmailTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_content', stdout=StringIO())
        cls.staff=User.objects.create_user('recovery-staff',email='staff@example.org',password='Old-Example-Password42!',is_staff=True)
        User.objects.create_user('ordinary',email='ordinary@example.org',password='Test-Example-Password42!')

    def request_reset(self,email='staff@example.org'):
        return self.client.post('/admin/password_reset/',{'email':email})

    def test_login_contains_recovery_link_and_unknown_email_is_generic(self):
        self.assertContains(self.client.get('/admin/login/'),'href="/admin/password_reset/"')
        valid=self.request_reset();self.assertEqual(valid.status_code,302)
        for email in ('missing@example.org','ordinary@example.org'):
            self.assertEqual(self.request_reset(email)['Location'],valid['Location'])
        self.assertEqual(len(mail.outbox),1)
        self.assertEqual(mail.outbox[0].to,['staff@example.org'])
        self.assertEqual(mail.outbox[0].from_email,'sender@example.org')
        self.assertIn('https://euroafrica-1u37.onrender.com/admin/reset/',mail.outbox[0].body)
        self.assertNotIn('127.0.0.1',mail.outbox[0].body)

    def test_reset_valid_used_invalid_expired_and_old_password(self):
        self.request_reset()
        url=re.search(r'https://[^\s]+/admin/reset/[^\s]+',mail.outbox[0].body).group(0)
        response=self.client.get(url);self.assertEqual(response.status_code,302)
        form_url=response['Location']
        self.assertTrue(self.client.get(form_url).context['validlink'])
        response=self.client.post(form_url,{'new_password1':'New-Example-Password73!','new_password2':'New-Example-Password73!'})
        self.assertEqual(response.status_code,302)
        self.staff.refresh_from_db()
        self.assertFalse(self.staff.check_password('Old-Example-Password42!'))
        self.assertTrue(self.staff.check_password('New-Example-Password73!'))
        self.assertFalse(Client().get(url).context['validlink'])
        self.assertFalse(self.client.get('/admin/reset/MQ/invalid-token/').context['validlink'])
        self.request_reset()
        newer=re.search(r'https://[^\s]+/admin/reset/[^\s]+',mail.outbox[-1].body).group(0)
        later=default_token_generator._now()+timedelta(seconds=settings.PASSWORD_RESET_TIMEOUT+1)
        with patch.object(default_token_generator,'_now',return_value=later):
            self.assertFalse(Client().get(newer).context['validlink'])
        self.assertTrue(self.client.login(username='recovery-staff',password='New-Example-Password73!'))

    def test_inactive_staff_and_unusable_password_excluded(self):
        self.staff.is_active=False;self.staff.save();self.request_reset()
        self.assertEqual(len(mail.outbox),0)
        self.staff.is_active=True;self.staff.set_unusable_password();self.staff.save();self.request_reset()
        self.assertEqual(len(mail.outbox),0)

    def test_reset_delivery_failure_and_rate_limit(self):
        with patch('django.core.mail.EmailMultiAlternatives.send',side_effect=RuntimeError('SMTP unavailable')):
            self.assertEqual(self.request_reset().status_code,302)
        for _ in range(6):self.request_reset()
        self.assertEqual(len(mail.outbox),4)
        self.assertEqual(Client(enforce_csrf_checks=True).post('/admin/password_reset/',{'email':'staff@example.org'}).status_code,403)

    @override_settings(CONTACT_NOTIFICATION_EMAIL='receiver@example.org')
    def test_enquiry_notification_fields_and_recipient(self):
        data=enquiry_data(company='Example Company',phone='123',message='A plain text question.')
        response=self.client.post('/contact/',data)
        self.assertEqual(response.status_code,302)
        self.assertEqual(Enquiry.objects.count(),1)
        self.assertEqual(len(mail.outbox),1)
        self.assertEqual(mail.outbox[0].to,['receiver@example.org'])
        self.assertEqual(mail.outbox[0].from_email,'sender@example.org')
        for key in ('name','email','company','phone','message'):self.assertIn(data[key],mail.outbox[0].body)
        self.assertIn('/admin/trade/enquiry/',mail.outbox[0].body)

    def test_admin_login_logout_and_default_action_permissions(self):
        self.staff.groups.add(Group.objects.get(name='Editor'))
        self.assertEqual(self.client.get('/admin/').status_code,302)
        response=self.client.post('/admin/login/',{'username':self.staff.username,'password':'Old-Example-Password42!','next':'/admin/'})
        self.assertEqual(response.status_code,302)
        self.assertEqual(self.client.get('/admin/').status_code,200)
        category=TradeCategory.objects.create(direction=TradeDirection.objects.first(),title='Disposable',slug='disposable',summary='Temporary',overview='Temporary')
        other=TradeCategory.objects.exclude(pk=category.pk).count()
        response=self.client.post('/admin/trade/tradecategory/',{'action':'delete_selected','_selected_action':[str(category.pk)],'post':'yes'})
        self.assertEqual(response.status_code,302)
        self.assertFalse(TradeCategory.objects.filter(pk=category.pk).exists())
        self.assertEqual(TradeCategory.objects.count(),other)
        self.assertEqual(self.client.get('/admin/logout/').status_code,405)
        self.client.post('/admin/logout/')
        self.assertEqual(self.client.get('/admin/').status_code,302)
        viewer=User.objects.create_user('view-only',is_staff=True)
        from django.contrib.auth.models import Permission
        viewer.user_permissions.add(Permission.objects.get(codename='view_tradecategory'))
        self.client.force_login(viewer)
        target=TradeCategory.objects.first()
        self.client.post('/admin/trade/tradecategory/',{'action':'delete_selected','_selected_action':[str(target.pk)],'post':'yes'})
        self.assertTrue(TradeCategory.objects.filter(pk=target.pk).exists())

@override_settings(DEBUG=True, STAGING=False, ROOT_URLCONF=__name__, SECURE_SSL_REDIRECT=False)
class MediaReadinessTests(TestCase):
    @classmethod
    def setUpTestData(cls): call_command('seed_content',stdout=StringIO())

    def test_formats_missing_unsafe_and_traversal(self):
        with tempfile.TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            for suffix,fmt,mime in [('jpg','JPEG','image/jpeg'),('jpeg','JPEG','image/jpeg'),('png','PNG','image/png'),('webp','WEBP','image/webp')]:
                Image.new('RGB',(10,10),'navy').save(Path(directory)/f'photo.{suffix}',fmt)
                response=self.client.get(f'/media/photo.{suffix}')
                self.assertEqual(response.status_code,200);self.assertEqual(response['Content-Type'],mime);response.close()
            (Path(directory)/'unsafe.html').write_text('<script/>')
            for url in ('/media/unsafe.html','/media/missing.webp','/media/../outside.webp','/media/%00.webp'):
                self.assertEqual(self.client.get(url).status_code,404,url)

    def test_defaults_link_once_preserve_upload_and_clear(self):
        with override_settings(MEDIA_ROOT=Path(settings.BASE_DIR)/'media'):
            home=HomePage.objects.get(pk=1);home.hero_heading='Owner edit';home.save()
            call_command('link_stock_images',stdout=StringIO())
            home.refresh_from_db();self.assertEqual(home.hero_heading,'Owner edit')
            self.assertTrue(home.hero_image.storage.exists(home.hero_image.name))
            for obj in [home]+list(TradeCategory.objects.all()):
                file=obj.hero_image if isinstance(obj,HomePage) else obj.image
                if not file:
                    self.assertContains(self.client.get(obj.get_absolute_url()), 'illustration.svg')
                    continue
                response=self.client.get(file.url);self.assertEqual(response.status_code,200);response.close()
                for variant in image_srcset(file).split(', '):
                    if variant:
                        response=self.client.get(variant.split(' ')[0]);self.assertEqual(response.status_code,200);response.close()
            home.hero_image='';home.save()
            category=TradeCategory.objects.first();category.image='owner/missing.webp';category.save()
            call_command('link_stock_images',stdout=StringIO())
            home.refresh_from_db();category.refresh_from_db()
            self.assertFalse(home.hero_image)
            self.assertEqual(category.image.name,'owner/missing.webp')

    def test_existing_owner_path_preserved_on_first_link(self):
        home=HomePage.objects.get(pk=1);home.hero_image='owner/custom.webp';home.save()
        call_command('link_stock_images',stdout=StringIO());home.refresh_from_db()
        self.assertEqual(home.hero_image.name,'owner/custom.webp')

    def test_srcset_missing_derivatives_and_missing_original_fallback(self):
        with tempfile.TemporaryDirectory() as directory, override_settings(MEDIA_ROOT=directory):
            Image.new('RGB',(1400,1000),'navy').save(Path(directory)/'original.webp','WEBP')
            home=HomePage.objects.get(pk=1);home.hero_image='original.webp';home.save()
            self.assertNotIn('-480.webp',image_srcset(home.hero_image))
            self.assertIn('1400w',image_srcset(home.hero_image))
            home.hero_image='gone.webp';home.save()
            self.assertEqual(image_srcset(home.hero_image),'')
            self.assertContains(self.client.get('/'),'illustration.svg')
