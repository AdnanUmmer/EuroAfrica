"""Layered enquiry protection shared across PostgreSQL-backed workers."""
import ipaddress
import json
import logging
import secrets
import time
import unicodedata
from datetime import timedelta
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen
from django.conf import settings
from django.core import signing
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.utils.crypto import salted_hmac
from .models import SubmissionWindow, SubmissionReceipt

logger = logging.getLogger(__name__)
GENERIC_ERROR = 'We could not verify your enquiry. Please wait a moment and try again.'


def timing_token():
    return signing.dumps({'issued': time.time(), 'nonce': secrets.token_urlsafe(24)}, salt='enquiry-form')


def valid_timing(token):
    try:
        payload = signing.loads(token, salt='enquiry-form', max_age=settings.CONTACT_TOKEN_MAX_AGE)
        elapsed = time.time() - payload['issued']
        return bool(payload['nonce']) and settings.CONTACT_MIN_SECONDS <= elapsed <= settings.CONTACT_TOKEN_MAX_AGE
    except (signing.BadSignature, KeyError, TypeError, ValueError):
        return False


def client_address(request):
    # Outside Render, never trust arbitrary forwarded headers. Render terminates
    # public traffic at its proxy; read only its rightmost appended hop. Extra
    # intermediaries may share a bucket, but a supplied left prefix cannot evade it.
    address = request.META.get('REMOTE_ADDR', '')
    if settings.ON_RENDER:
        forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
        if forwarded and len(forwarded) <= 2048:
            address = forwarded.split(',')[-1].strip()
    try:
        return str(ipaddress.ip_address(address))
    except ValueError:
        return 'unknown'


def rate_allowed(identity, scope, limit, seconds):
    key = salted_hmac('enquiry-rate', f'{scope}/{identity}/{int(time.time() // seconds)}').hexdigest()
    with transaction.atomic():
        row, _ = SubmissionWindow.objects.get_or_create(key=key)
        SubmissionWindow.objects.filter(pk=row.pk).update(attempts=F('attempts') + 1)
        row.refresh_from_db()
    return row.attempts <= limit


def receipt_keys(data):
    normalized = ' '.join(unicodedata.normalize('NFKC', data['message']).split()).casefold()
    scope = '/'.join([data.get('interest', 'general'), str(getattr(data.get('category'), 'pk', 'general')), ' '.join(data.get('market', '').casefold().split())])
    return sorted([
        salted_hmac('enquiry-duplicate', data['email'].casefold() + '/' + scope + '/' + normalized).hexdigest(),
        salted_hmac('enquiry-replay', data['form_token']).hexdigest(),
    ])


def already_received(keys):
    return SubmissionReceipt.objects.filter(key__in=keys, expires_at__gt=timezone.now()).exists()


def save_once(form, keys):
    # The unique keys + row locks serialize concurrent duplicates on PostgreSQL.
    # Database errors roll back both the receipt and enquiry; SMTP is outside.
    with transaction.atomic():
        now = timezone.now()
        rows = []
        for key in keys:
            row, created = SubmissionReceipt.objects.get_or_create(key=key, defaults={'expires_at': now})
            row = SubmissionReceipt.objects.select_for_update().get(pk=row.pk)
            if not created and row.expires_at > now:
                return None
            rows.append(row)
        enquiry = form.save(commit=False)
        enquiry.privacy_consent_at = now
        enquiry.save()
        for row in rows:
            row.expires_at = now + timedelta(hours=2)
            row.save(update_fields=['expires_at'])
        return enquiry


def turnstile_required():
    return not settings.DEBUG or bool(settings.TURNSTILE_SITE_KEY or settings.TURNSTILE_SECRET_KEY)


def turnstile_configured():
    keys = (settings.TURNSTILE_SITE_KEY, settings.TURNSTILE_SECRET_KEY)
    # Official dummy keys must never open a production submission endpoint.
    return all(keys) and (settings.DEBUG or not any(k.startswith(('1x000000', '2x000000', '3x000000')) for k in keys))


def verify_turnstile(token):
    if not turnstile_required():
        return True  # Local DEBUG only; cannot be enabled via a production bypass flag.
    if not turnstile_configured():
        logger.warning('Enquiry verification unavailable: configuration.')
        return False
    if not token or len(token) > 2048:
        logger.info('Enquiry verification rejected: missing or oversized token.')
        return False
    body = urlencode({'secret': settings.TURNSTILE_SECRET_KEY, 'response': token}).encode()
    request = Request('https://challenges.cloudflare.com/turnstile/v0/siteverify', data=body, headers={'Content-Type': 'application/x-www-form-urlencoded'})
    try:
        with urlopen(request, timeout=5) as response:
            result = json.loads(response.read(16384))
        if not isinstance(result, dict):
            raise ValueError('Invalid response')
        expected_host = urlsplit(settings.SITE_URL).hostname
        valid = (result.get('success') is True and result.get('hostname', '').lower().rstrip('.') == expected_host
                 and result.get('action') == 'enquiry')
        if not valid:
            codes = result.get('error-codes', [])
            reason = 'expired-or-replayed' if 'timeout-or-duplicate' in codes else 'rejected'
            logger.info('Enquiry verification %s.', reason)
        return valid
    except (OSError, ValueError, TypeError, AttributeError):
        logger.warning('Enquiry verification unavailable: network or response failure.')
        return False
