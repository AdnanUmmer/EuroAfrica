import json
import time
from datetime import timedelta
from io import StringIO
from unittest.mock import patch, MagicMock
from urllib.error import URLError
from django.contrib.auth.models import User, Permission
from django.core import mail
from django.core.management import call_command
from django.test import TestCase, SimpleTestCase, RequestFactory, Client, override_settings
from django.utils import timezone
from . import antispam
from .models import Enquiry, SubmissionReceipt, SubmissionWindow, TradeCategory
from .test_helpers import enquiry_data


@override_settings(DEBUG=True, STAGING=False, ON_RENDER=False, SECURE_SSL_REDIRECT=False,
                   SITE_URL='https://www.euroafrica.example', TURNSTILE_SITE_KEY='', TURNSTILE_SECRET_KEY='',
                   CONTACT_NOTIFICATION_EMAIL='owner@example.org', DEFAULT_FROM_EMAIL='verified@example.org',
                   EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class EnquirySecurityTests(TestCase):
    @classmethod
    def setUpTestData(cls): call_command('seed_content', stdout=StringIO())

    def post(self, data=None, **kwargs):
        return self.client.post('/contact/', data or enquiry_data(), **kwargs)

    def test_valid_saved_before_mail_with_fixed_headers_and_consent(self):
        data=enquiry_data(name='Zoë 李', to='attacker@example.org', from_email='spoof@example.org')
        self.assertEqual(self.post(data).status_code,302)
        obj=Enquiry.objects.get();self.assertEqual(obj.status,'new');self.assertIsNotNone(obj.privacy_consent_at)
        message=mail.outbox[0]
        self.assertEqual(message.to,['owner@example.org']);self.assertEqual(message.from_email,'verified@example.org')
        self.assertEqual(message.reply_to,['visitor@example.org']);self.assertIn('Zoë 李',message.body)
        self.assertEqual(len(mail.outbox),1)

    def test_honeypot_timing_and_consent_rejections(self):
        cases=[{'website':'spam'}, {'form_token':antispam.timing_token()}, {'form_token':'tampered'},
               {'privacy_consent':''}, {'form_token':''}]
        for changes in cases:
            with self.subTest(changes=changes):
                self.assertEqual(self.post(enquiry_data(**changes)).status_code,200)
        self.assertFalse(Enquiry.objects.exists());self.assertEqual(len(mail.outbox),0)

    def test_expired_timing_token(self):
        with patch('trade.antispam.time.time',return_value=time.time()-7201):token=antispam.timing_token()
        self.post(enquiry_data(form_token=token));self.assertFalse(Enquiry.objects.exists())

    def test_validation_and_header_injection(self):
        cases=[{'email':'bad'}, {'message':'  \n '}, {'message':'x'*5001}, {'name':' '*5}, {'name':'x'*121},
               {'company':'x'*181}, {'email':'a@example.org\r\nBcc: bad@example.org'}, {'category':'9999999'}, {'category':''}]
        for changes in cases:
            self.post(enquiry_data(**changes))
        self.assertFalse(Enquiry.objects.exists());self.assertEqual(len(mail.outbox),0)

    def test_duplicate_normalization_and_replay_do_not_email_twice(self):
        first=enquiry_data(message='A   sample question')
        self.assertEqual(self.post(first).status_code,302)
        self.assertEqual(self.post(enquiry_data(email='VISITOR@example.org',message=' a sample QUESTION ')).status_code,302)
        changed=dict(first,message='Changed text with replayed form token')
        self.assertEqual(self.post(changed).status_code,302)
        self.assertEqual(Enquiry.objects.count(),1);self.assertEqual(len(mail.outbox),1)
        self.assertEqual(SubmissionReceipt.objects.count(),2)

    def test_save_once_rechecks_duplicate_and_rolls_back_errors(self):
        from .forms import EnquiryForm
        form=EnquiryForm(enquiry_data());self.assertTrue(form.is_valid())
        keys=antispam.receipt_keys(form.cleaned_data)
        with patch.object(Enquiry,'save',side_effect=RuntimeError('database failure')):
            with self.assertRaises(RuntimeError):antispam.save_once(form,keys)
        self.assertEqual(SubmissionReceipt.objects.count(),0)
        self.assertIsNotNone(antispam.save_once(form,keys))
        self.assertIsNone(antispam.save_once(form,keys));self.assertEqual(Enquiry.objects.count(),1)

    def test_ip_and_email_limits_return_429_without_more_mail(self):
        with override_settings(CONTACT_IP_LIMIT=2):
            self.post(enquiry_data(message='First message'))
            self.post(enquiry_data(message='Second message'))
            response=self.post(enquiry_data(message='Third message'))
            self.assertEqual(response.status_code,429);self.assertEqual(response['Retry-After'],'600')
        self.assertEqual(len(mail.outbox),2)
        SubmissionWindow.objects.all().delete()
        with override_settings(CONTACT_EMAIL_LIMIT=1):
            self.post(enquiry_data(message='Fourth message'),REMOTE_ADDR='192.0.2.1')
            response=self.post(enquiry_data(message='Fifth message'),REMOTE_ADDR='192.0.2.2')
            self.assertEqual(response.status_code,429);self.assertEqual(response['Retry-After'],'3600')
        self.assertEqual(len(mail.outbox),3)

    def test_smtp_failure_preserves_record_and_retry_is_duplicate(self):
        data=enquiry_data()
        with patch('trade.views.EmailMessage.send',side_effect=OSError('SMTP unavailable')):
            self.assertEqual(self.post(data).status_code,302)
        self.assertEqual(self.post(data).status_code,302)
        self.assertEqual(Enquiry.objects.count(),1);self.assertEqual(len(mail.outbox),0)

    @override_settings(DEBUG=False, TURNSTILE_SITE_KEY='', TURNSTILE_SECRET_KEY='', ALLOWED_HOSTS=['www.euroafrica.example'])
    def test_production_fails_closed_without_keys_and_still_serves_pages(self):
        self.client.defaults['HTTP_HOST']='www.euroafrica.example'
        self.assertEqual(self.client.get('/',secure=True).status_code,200)
        response=self.post(secure=True);self.assertEqual(response.status_code,503)
        self.assertFalse(Enquiry.objects.exists());self.assertEqual(len(mail.outbox),0)

    @override_settings(TURNSTILE_SITE_KEY='public-widget', TURNSTILE_SECRET_KEY='private-test-secret')
    def test_widget_csp_and_secret_not_exposed(self):
        response=self.client.get('/contact/')
        self.assertContains(response,'data-sitekey="public-widget"');self.assertNotContains(response,'private-test-secret')
        self.assertIn('frame-src https://challenges.cloudflare.com',response['Content-Security-Policy'])
        self.assertNotIn('challenges.cloudflare.com',self.client.get('/')['Content-Security-Policy'])
        self.assertContains(response,'type="text" name="website"')
        self.assertContains(response,'aria-hidden="true"');self.assertContains(response,'tabindex="-1"')
        self.assertIn('no-store',response['Cache-Control'])

    @override_settings(TURNSTILE_SITE_KEY='public-widget', TURNSTILE_SECRET_KEY='private-test-secret')
    def test_turnstile_gate_prevents_save_and_mail(self):
        with patch('trade.antispam.verify_turnstile',return_value=False):self.post()
        self.assertFalse(Enquiry.objects.exists());self.assertEqual(len(mail.outbox),0)
        with patch('trade.antispam.verify_turnstile',return_value=True):self.post()
        self.assertEqual(Enquiry.objects.count(),1);self.assertEqual(len(mail.outbox),1)

    def test_csrf_and_admin_escape_permissions_actions(self):
        self.assertEqual(Client(enforce_csrf_checks=True).post('/contact/',enquiry_data()).status_code,403)
        self.post(enquiry_data(message='<script>alert(1)</script>'))
        obj=Enquiry.objects.get();other=Enquiry.objects.create(name='Other',email='other@example.org',message='Other')
        path='/admin/trade/enquiry/'
        self.assertEqual(self.client.get(path).status_code,302)
        staff=User.objects.create_user('enquiry-editor',is_staff=True)
        staff.user_permissions.add(*Permission.objects.filter(content_type__app_label='trade',codename__in=['view_enquiry','change_enquiry']))
        self.client.force_login(staff)
        response=self.client.get(f'{path}{obj.pk}/change/')
        self.assertContains(response,'&lt;script&gt;');self.assertNotContains(response,'<script>alert(1)</script>')
        for action,status in [('mark_read','read'),('mark_replied','replied'),('mark_spam','spam'),('archive','archived')]:
            self.assertEqual(self.client.post(path,{'action':action,'_selected_action':[obj.pk]}).status_code,302)
            obj.refresh_from_db();other.refresh_from_db()
            self.assertEqual(obj.status,status);self.assertEqual(other.status,'new')
        self.assertContains(self.client.get(path,{'q':'visitor@example.org','status__exact':'archived'}),'visitor@example.org')
        viewer=User.objects.create_user('enquiry-viewer',is_staff=True)
        viewer.user_permissions.add(Permission.objects.get(codename='view_enquiry'))
        self.client.force_login(viewer)
        self.client.post(path,{'action':'mark_spam','_selected_action':[obj.pk]})
        obj.refresh_from_db();self.assertEqual(obj.status,'archived')

    def test_cleanup_removes_only_expired_hashes(self):
        SubmissionReceipt.objects.create(key='old',expires_at=timezone.now()-timedelta(seconds=1))
        SubmissionReceipt.objects.create(key='current',expires_at=timezone.now()+timedelta(hours=1))
        call_command('clear_rate_windows',stdout=StringIO())
        self.assertEqual(list(SubmissionReceipt.objects.values_list('key',flat=True)),['current'])


@override_settings(DEBUG=False, SITE_URL='https://www.euroafrica.example',
                   TURNSTILE_SITE_KEY='public-widget', TURNSTILE_SECRET_KEY='private-test-secret')
class TurnstileVerificationTests(SimpleTestCase):
    def response(self, data):
        response=MagicMock();response.__enter__.return_value.read.return_value=json.dumps(data).encode();return response

    def test_valid_action_hostname_and_request(self):
        with patch('trade.antispam.urlopen',return_value=self.response({'success':True,'hostname':'www.euroafrica.example','action':'enquiry'})) as api:
            self.assertTrue(antispam.verify_turnstile('test-response'))
        request=api.call_args.args[0]
        self.assertEqual(request.full_url,'https://challenges.cloudflare.com/turnstile/v0/siteverify')
        self.assertIn(b'response=test-response',request.data);self.assertNotIn(b'remoteip',request.data)
        self.assertEqual(api.call_args.kwargs['timeout'],5)

    def test_rejected_expired_duplicate_wrong_action_host_and_malformed(self):
        cases=[{'success':False}, {'success':False,'error-codes':['timeout-or-duplicate']},
               {'success':True,'hostname':'attacker.example','action':'enquiry'},
               {'success':True,'hostname':'www.euroafrica.example','action':'login'}, [], {'success':'true'}]
        for result in cases:
            with patch('trade.antispam.urlopen',return_value=self.response(result)):
                self.assertFalse(antispam.verify_turnstile('test-response'))

    def test_missing_oversized_network_and_invalid_json(self):
        with patch('trade.antispam.urlopen') as api:
            self.assertFalse(antispam.verify_turnstile(''));self.assertFalse(antispam.verify_turnstile('x'*2049));api.assert_not_called()
        for error in (TimeoutError(),URLError('unavailable'),ValueError('invalid JSON')):
            with patch('trade.antispam.urlopen',side_effect=error):self.assertFalse(antispam.verify_turnstile('token'))

    def test_dummy_keys_cannot_enable_production(self):
        with override_settings(TURNSTILE_SECRET_KEY='1x0000000000000000000000000000000AA'):
            self.assertFalse(antispam.turnstile_configured());self.assertFalse(antispam.verify_turnstile('token'))

    def test_untrusted_headers_and_render_rightmost_hop(self):
        request=RequestFactory().get('/',REMOTE_ADDR='192.0.2.10',HTTP_X_FORWARDED_FOR='198.51.100.99, 203.0.113.4')
        with override_settings(ON_RENDER=False):self.assertEqual(antispam.client_address(request),'192.0.2.10')
        with override_settings(ON_RENDER=True):
            self.assertEqual(antispam.client_address(request),'203.0.113.4')
            request.META['HTTP_X_FORWARDED_FOR']='spoof, 203.0.113.4'
            self.assertEqual(antispam.client_address(request),'203.0.113.4')
            request.META['HTTP_X_FORWARDED_FOR']='not-an-ip'
            self.assertEqual(antispam.client_address(request),'unknown')
