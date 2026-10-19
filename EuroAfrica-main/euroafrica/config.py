"""Validate canonical origins before they can become redirect destinations."""
import ipaddress
from urllib.parse import urlsplit
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.validators import URLValidator


def normalized_authority(authority, scheme='https'):
    """Compare already validated Host headers by DNS name and effective port."""
    parsed = urlsplit(f'{scheme}://{authority}')
    return ((parsed.hostname or '').lower().rstrip('.'),
            parsed.port or (443 if scheme == 'https' else 80))


def canonical_origin(value, production=False):
    value = value.strip()
    try:
        parsed = urlsplit(value)
        hostname = (parsed.hostname or '').lower().rstrip('.')
        port = parsed.port
        if (parsed.scheme not in ('http', 'https') or not hostname or
                parsed.username is not None or parsed.password is not None or
                parsed.path not in ('', '/') or parsed.query or parsed.fragment):
            raise ValueError
        host = f'[{hostname}]' if ':' in hostname else hostname
        origin = f'{parsed.scheme}://{host}'
        if port and port != (443 if parsed.scheme == 'https' else 80):
            origin += f':{port}'
        URLValidator(schemes=['http', 'https'])(origin)
        if production:
            if parsed.scheme != 'https' or hostname == 'localhost' or hostname.endswith('.localhost'):
                raise ValueError
            try:
                address = ipaddress.ip_address(hostname)
            except ValueError:
                address = None
            if address and address.is_loopback:
                raise ValueError
        return origin
    except (ValueError, ValidationError):
        raise ImproperlyConfigured('SITE_URL must be a valid origin without credentials, path, query or fragment; production requires a non-local HTTPS origin.') from None
