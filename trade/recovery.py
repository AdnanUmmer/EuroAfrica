"""Django's signed, expiring reset flow, restricted to active staff accounts."""
import logging
import time
from urllib.parse import urlsplit
from django.conf import settings
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.views import PasswordResetView
from django.db import transaction
from django.db.models import F
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils.crypto import salted_hmac
from .models import SubmissionWindow


class StaffPasswordResetForm(PasswordResetForm):
    def get_users(self, email):
        return (user for user in super().get_users(email) if user.is_staff)

    def save(self, **kwargs):
        origin = urlsplit(settings.SITE_URL)
        kwargs.update(domain_override=origin.netloc, use_https=origin.scheme == 'https', from_email=settings.DEFAULT_FROM_EMAIL)
        return super().save(**kwargs)

    def send_mail(self, subject_template_name, email_template_name, context, from_email, to_email, html_email_template_name=None):
        from django.core.mail import EmailMultiAlternatives
        from django.template.loader import render_to_string
        subject = ''.join(render_to_string(subject_template_name, context).splitlines())
        body = render_to_string(email_template_name, context)
        try:
            EmailMultiAlternatives(subject, body, from_email, [to_email]).send()
        except Exception:
            logging.getLogger(__name__).warning('Admin password reset delivery failed; check email service configuration.')


class StaffPasswordResetView(PasswordResetView):
    form_class = StaffPasswordResetForm
    success_url = reverse_lazy('admin_password_reset_done')
    email_template_name = 'registration/staff_reset_email.txt'
    subject_template_name = 'registration/staff_reset_subject.txt'

    def form_valid(self, form):
        # Identical response for nonexistent, non-staff, throttled and valid users.
        key = salted_hmac('staff-reset', f"{form.cleaned_data['email'].casefold()}/{int(time.time() // 3600)}").hexdigest()
        with transaction.atomic():
            window, _ = SubmissionWindow.objects.get_or_create(key=key)
            SubmissionWindow.objects.filter(pk=window.pk).update(attempts=F('attempts') + 1)
            window.refresh_from_db()
        if window.attempts > 5:
            return HttpResponseRedirect(self.get_success_url())
        return super().form_valid(form)
