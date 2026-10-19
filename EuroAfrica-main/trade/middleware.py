import base64
import secrets
from urllib.parse import urlsplit
from django.conf import settings
from django.http import HttpResponse, HttpResponsePermanentRedirect
from euroafrica.config import canonical_origin, normalized_authority

class SiteMiddleware:
    def __init__(self, get_response): self.get_response = get_response
    def __call__(self, request):
        if settings.STAGING:
            expected = 'Basic ' + base64.b64encode(f'{settings.STAGING_USER}:{settings.STAGING_PASSWORD}'.encode()).decode()
            if not secrets.compare_digest(request.headers.get('Authorization', ''), expected):
                response = HttpResponse('Authentication required', status=401)
                response['WWW-Authenticate'] = 'Basic realm="EuroAfrica staging"'
                response['X-Robots-Tag'] = 'noindex, nofollow'
                return response
        if not settings.DEBUG:
            # get_host() validates ALLOWED_HOSTS before normalization. Never use
            # X-Forwarded-Host or an unvalidated incoming host as a destination.
            request_host = request.get_host()
            origin = canonical_origin(settings.SITE_URL, production=True)
            canonical = urlsplit(origin)
            if normalized_authority(request_host, request.scheme) != normalized_authority(canonical.netloc, canonical.scheme):
                return HttpResponsePermanentRedirect(origin + request.get_full_path())
        response = self.get_response(request)
        if not settings.INDEXABLE or settings.STAGING or request.path.startswith(('/admin/', '/preview/', '/contact/thanks/')) or response.status_code >= 400:
            response['X-Robots-Tag'] = 'noindex, nofollow'
        if request.path.startswith(('/admin/', '/preview/', '/contact/')):
            response['Cache-Control'] = 'private, no-store'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Content-Security-Policy'] = "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; font-src 'self'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
        if request.path == '/contact/' and settings.TURNSTILE_SITE_KEY:
            response['Content-Security-Policy'] = response['Content-Security-Policy'].replace("script-src 'self'", "script-src 'self' https://challenges.cloudflare.com") + "; frame-src https://challenges.cloudflare.com; connect-src 'self' https://challenges.cloudflare.com"
        return response
