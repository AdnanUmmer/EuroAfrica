import importlib
import json
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from html import unescape
import re
from django.apps import apps
from django.conf import settings
from django.core import mail
from django.core.management import call_command
from django.db import connection
from django.test import TestCase, override_settings
from .models import HomePage, TradeCategory, TradeDirection, Enquiry, URLHistory, HomeFeature, ContentSection
from .test_helpers import enquiry_data


@override_settings(DEBUG=True, STAGING=False, SECURE_SSL_REDIRECT=False, TURNSTILE_SITE_KEY='',TURNSTILE_SECRET_KEY='',
                   EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',CONTACT_NOTIFICATION_EMAIL='owner@example.org')
class ApprovedContentTests(TestCase):
    @classmethod
    def setUpTestData(cls):call_command('seed_content',stdout=StringIO())

    def test_all_approved_copy_is_rendered_and_old_copy_absent(self):
        data=json.loads((Path(settings.BASE_DIR)/'trade/approved_content.json').read_text(encoding='utf-8'))
        migration=importlib.import_module('trade.migrations.0011_approved_website_content')
        self.assertEqual(data,json.loads(json.dumps(migration.DATA)))
        urls=['/','/about/','/contact/']+[d.get_absolute_url() for d in TradeDirection.objects.all()]+[c.get_absolute_url() for c in TradeCategory.objects.filter(published=True)]
        text=''
        for url in urls:
            response=self.client.get(url);self.assertEqual(response.status_code,200)
            page=response.content.decode();self.assertEqual(len(re.findall(r'<h1[ >]',page)),1)
            text+=' '+unescape(re.sub('<[^>]+>',' ',page))
        text=' '.join(text.split())
        for key,value in data['home'].items():
            if isinstance(value,str) and not key.endswith('_url'):
                self.assertIn(' '.join(value.split()),text,key)
        for item in data['categories']:
            for key in ('title','summary','overview','link_label'):
                self.assertIn(' '.join(item[key].split()),text,item['slug'])
        self.assertIn('€41 billion',text)
        for old in ('supplied examples','OWNER REVIEW REQUIRED','A shared perspective on trade','A conversation starts here'):
            self.assertNotIn(old,text)
        self.assertEqual(HomeFeature.objects.count(),4);self.assertEqual(ContentSection.objects.count(),2)

    def test_release_archives_legacy_preserves_enquiry_and_redirects_directly(self):
        direction=TradeDirection.objects.get(seed_key='africa-to-europe')
        old=TradeCategory.objects.create(direction=direction,seed_key='beverages',slug='owner-drinks',title='Old drinks',summary='Old',overview='Old',published=True,image='owner/drinks.webp')
        enquiry=Enquiry.objects.create(name='Existing',email='existing@example.org',category=old,message='Keep this',status='replied')
        URLHistory.objects.create(path='/africa-to-europe/older-drinks/',kind='TradeCategory',object_id=old.pk)
        migration=importlib.import_module('trade.migrations.0011_approved_website_content')
        migration.install(apps,SimpleNamespace(connection=connection))
        old.refresh_from_db();enquiry.refresh_from_db()
        self.assertFalse(old.published);self.assertEqual(old.image.name,'owner/drinks.webp')
        self.assertEqual(enquiry.category_id,old.pk);self.assertEqual(enquiry.status,'replied')
        target=TradeCategory.objects.get(seed_key='agricultural-commodities')
        for path in (old.get_absolute_url(),'/africa-to-europe/older-drinks/'):
            response=self.client.get(path);self.assertEqual(response.status_code,301)
            self.assertEqual(response['Location'],target.get_absolute_url())
            self.assertEqual(self.client.get(response['Location']).status_code,200)
        home=HomePage.objects.get(pk=1);home.hero_heading='Later owner edit';home.save()
        HomeFeature.objects.all().delete()
        call_command('seed_content',stdout=StringIO());home.refresh_from_db()
        self.assertEqual(home.hero_heading,'Later owner edit');self.assertEqual(HomeFeature.objects.count(),0)

    def test_extended_enquiry_and_email_fields(self):
        category=TradeCategory.objects.get(seed_key='machinery-appliances')
        data=enquiry_data(interest='europe-to-africa',category=category.pk,market='Kenya')
        self.assertEqual(self.client.post('/contact/',data).status_code,302)
        record=Enquiry.objects.get();self.assertEqual(record.market,'Kenya');self.assertEqual(record.interest,'europe-to-africa')
        self.assertIn('Kenya',mail.outbox[0].body);self.assertIn('Europe → Africa Trade',mail.outbox[0].body)
        self.assertEqual(mail.outbox[0].reply_to,['visitor@example.org'])
        self.assertEqual(self.client.post('/contact/',data).status_code,302)
        self.assertEqual(len(mail.outbox),1)

    def test_invalid_interest_market_and_cross_direction_rejected(self):
        category=TradeCategory.objects.get(seed_key='machinery-appliances')
        for updates in ({'interest':''},{'interest':'not-real'},{'market':'x'*121},{'interest':'africa-to-europe','category':category.pk}):
            response=self.client.post('/contact/',enquiry_data(**updates))
            self.assertEqual(response.status_code,200);self.assertFalse(Enquiry.objects.exists())
        self.assertEqual(len(mail.outbox),0)
