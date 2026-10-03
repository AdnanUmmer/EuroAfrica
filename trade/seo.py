from django.utils.translation import gettext as _
"""Shared metadata defaults; explicit editorial overrides always win."""
import re
from django.conf import settings
from django.templatetags.static import static
from .models import HomePage, ContactPage, TradeCategory, TradeDirection
from .templatetags.trade_images import image_available


def metadata(obj, site):
    copy = obj.translated
    brand = site.translated
    heading = copy.get('title', copy.get('hero_heading', site.site_name))
    if isinstance(obj, TradeCategory):
        default_title = f"{heading} | {obj.direction.translated['title']} | {site.site_name}"
    elif isinstance(obj, TradeDirection):
        default_title = _('%(heading)s Trade Categories | %(brand)s') % {'heading': heading, 'brand': site.site_name}
    elif isinstance(obj, ContactPage):
        default_title = _('Contact %(brand)s | Africaâ€“Europe Trade Enquiries') % {'brand': site.site_name}
    else:
        default_title = f'{heading} | {site.site_name}'
    title = copy['seo_title'] or (brand['seo_title'] if isinstance(obj, HomePage) else '') or default_title
    fallback = copy.get('summary', copy.get('introduction', copy.get('hero_text', ''))) or brand['meta_description']
    fallback = re.sub(r'\s+', ' ', fallback).strip()
    if len(fallback) > 165:
        fallback = fallback[:162].rsplit(' ', 1)[0] + 'â€¦'
    description = copy['meta_description'] or fallback
    candidates = [(obj.social_image, copy['social_image_alt']),
                  (getattr(obj, 'hero_image', None), copy.get('hero_alt', '')),
                  (getattr(obj, 'image', None), copy.get('image_alt', '')),
                  (site.social_image, brand['social_image_alt'])]
    for image, alt in candidates:
        if image_available(image):
            return dict(title=title, description=description, social_url=settings.SITE_URL + image.url,
                        social_alt=alt, social_width=image.width, social_height=image.height)
    return dict(title=title, description=description, social_url=settings.SITE_URL + static('trade/logo.png'),
                social_alt=brand['logo_alt'], social_width=0, social_height=0)
