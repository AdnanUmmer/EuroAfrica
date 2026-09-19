"""Shared metadata defaults; explicit editorial overrides always win."""
import re
from django.conf import settings
from django.templatetags.static import static
from .models import HomePage, ContactPage, TradeCategory, TradeDirection
from .templatetags.trade_images import image_available


def metadata(obj, site):
    heading = getattr(obj, 'title', getattr(obj, 'hero_heading', site.site_name))
    if isinstance(obj, TradeCategory):
        default_title = f'{heading} | {obj.direction.title} | {site.site_name}'
    elif isinstance(obj, TradeDirection):
        default_title = f'{heading} Trade Categories | {site.site_name}'
    elif isinstance(obj, ContactPage):
        default_title = f'Contact {site.site_name} | Africa–Europe Trade Enquiries'
    else:
        default_title = f'{heading} | {site.site_name}'
    title = obj.seo_title or (site.seo_title if isinstance(obj, HomePage) else '') or default_title
    fallback = getattr(obj, 'summary', getattr(obj, 'introduction', getattr(obj, 'hero_text', ''))) or site.meta_description
    fallback = re.sub(r'\s+', ' ', fallback).strip()
    if len(fallback) > 165:
        fallback = fallback[:162].rsplit(' ', 1)[0] + '…'
    description = obj.meta_description or fallback
    candidates = [(obj.social_image, obj.social_image_alt),
                  (getattr(obj, 'hero_image', None), getattr(obj, 'hero_alt', '')),
                  (getattr(obj, 'image', None), getattr(obj, 'image_alt', '')),
                  (site.social_image, site.social_image_alt)]
    for image, alt in candidates:
        if image_available(image):
            return dict(title=title, description=description, social_url=settings.SITE_URL + image.url,
                        social_alt=alt, social_width=image.width, social_height=image.height)
    return dict(title=title, description=description, social_url=settings.SITE_URL + static('trade/logo.png'),
                social_alt=site.logo_alt, social_width=0, social_height=0)
