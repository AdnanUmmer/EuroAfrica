from django.conf import settings
from django.utils.translation import get_language, gettext_noop
from .models import SiteSettings, TradeDirection, ContentPage, TradeCategory, FooterLink

# Extraction markers for known database navigation labels and image fallbacks.
# Custom editorial labels still fall back to their stored text.
INTERFACE_LABELS = (
    gettext_noop('Africa to Europe'), gettext_noop('Europe to Africa'),
    gettext_noop('Africa → Europe'), gettext_noop('Europe → Africa'),
    gettext_noop('About EuroAfrica'), gettext_noop('Contact'), gettext_noop('Privacy'),
    gettext_noop('Markets in connection'), gettext_noop('Africa & Europe'),
    gettext_noop('Product diversity'),
)

def site(request):
    if hasattr(request, '_site_context'): return request._site_context
    pages = set(ContentPage.objects.filter(published=True).values_list('slug', flat=True))
    directions = list(TradeDirection.objects.filter(published=True))
    valid_paths = {'/', '/contact/'} | {f'/{slug}/' for slug in pages} | {d.get_absolute_url() for d in directions}
    links = list(FooterLink.objects.filter(visible=True))
    if any(link.destination.count('/') > 2 for link in links):
        valid_paths |= {c.get_absolute_url() for c in TradeCategory.objects.filter(published=True, direction__published=True).select_related('direction')}
    footer_links = [link for link in links if link.destination.split('?')[0].split('#')[0] in valid_paths]
    request._site_context = {'site_languages': settings.LANGUAGES, 'og_locale': {'en': 'en_GB', 'ar': 'ar_AR', 'hu': 'hu_HU', 'uk': 'uk_UA', 'fr': 'fr_FR', 'de': 'de_DE'}.get(get_language(), 'en_GB'), 'site': SiteSettings.objects.first(), 'nav_directions': directions, 'privacy_published': 'privacy' in pages, 'about_published': 'about' in pages, 'footer_links': footer_links}
    return request._site_context
