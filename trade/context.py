from .models import SiteSettings, TradeDirection, ContentPage, TradeCategory, FooterLink
def site(request):
    if hasattr(request, '_site_context'): return request._site_context
    pages = set(ContentPage.objects.filter(published=True).values_list('slug', flat=True))
    directions = list(TradeDirection.objects.filter(published=True))
    valid_paths = {'/', '/contact/'} | {f'/{slug}/' for slug in pages} | {d.get_absolute_url() for d in directions}
    links = list(FooterLink.objects.filter(visible=True))
    if any(link.destination.count('/') > 2 for link in links):
        valid_paths |= {c.get_absolute_url() for c in TradeCategory.objects.filter(published=True, direction__published=True).select_related('direction')}
    footer_links = [link for link in links if link.destination.split('?')[0].split('#')[0] in valid_paths]
    request._site_context = {'site': SiteSettings.objects.first(), 'nav_directions': directions, 'privacy_published': 'privacy' in pages, 'about_published': 'about' in pages, 'footer_links': footer_links}
    return request._site_context
