import hashlib
import json
import logging
import time
from xml.etree.ElementTree import Element, SubElement, tostring
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import F, Max
from django.http import Http404, HttpResponse, HttpResponsePermanentRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.crypto import salted_hmac
from .models import *
from .forms import EnquiryForm

def visible_categories(): return TradeCategory.objects.filter(published=True, direction__published=True).select_related('direction')

def render_page(request, template, obj, **context):
    from .context import site as site_context
    site = site_context(request)['site']
    title = getattr(obj, 'title', getattr(obj, 'hero_heading', 'EuroAfrica'))
    description = getattr(obj, 'summary', getattr(obj, 'introduction', getattr(obj, 'hero_text', '')))
    canonical = settings.SITE_URL + context.pop('canonical_path', request.path)
    crumbs = [('Home', '/')]
    if isinstance(obj, TradeCategory): crumbs.append((obj.direction.title, obj.direction.get_absolute_url()))
    if request.path != '/': crumbs.append((title, getattr(obj, 'get_absolute_url', lambda: request.path)()))
    graph = [{'@type': 'Organization', '@id': settings.SITE_URL + '/#organization', 'name': site.site_name, 'url': settings.SITE_URL + '/'}, {'@type': 'WebSite', '@id': settings.SITE_URL + '/#website', 'name': site.site_name, 'url': settings.SITE_URL + '/'}]
    if len(crumbs) > 1:
        graph.append({'@type': 'BreadcrumbList', 'itemListElement': [{'@type': 'ListItem', 'position': i + 1, 'name': label, 'item': settings.SITE_URL + path} for i, (label, path) in enumerate(crumbs)]})
    social = obj.social_image or site.social_image
    noindex = not settings.INDEXABLE or settings.STAGING or not getattr(obj, 'indexable', True) or (isinstance(obj, TradeCategory) and not obj.direction.indexable) or context.get('preview') or context.get('thanks')
    response = render(request, template, dict(context, obj=obj, title=obj.seo_title or (site.seo_title if isinstance(obj, HomePage) else '') or f'{title} | {site.site_name}', description=obj.meta_description or description[:300] or site.meta_description, canonical=canonical, breadcrumbs=crumbs, noindex=noindex, social_url=settings.SITE_URL + social.url if social else '', social_alt=obj.social_image_alt or site.social_image_alt, gsc=settings.GSC_VERIFICATION, structured=json.dumps({'@context': 'https://schema.org', '@graph': graph}).replace('<', '\\u003c')))
    if noindex: response['X-Robots-Tag'] = 'noindex, nofollow'
    return response

def home(request):
    return render_page(request, 'trade/home.html', get_object_or_404(HomePage, pk=1), categories=visible_categories().filter(featured=True))

def old_url(request):
    history = URLHistory.objects.filter(path=request.path).first()
    if history:
        model = {'TradeCategory': TradeCategory, 'TradeDirection': TradeDirection}.get(history.kind)
        obj = model.objects.filter(pk=history.object_id, published=True).first() if model else None
        if obj and (not isinstance(obj, TradeCategory) or obj.direction.published) and obj.get_absolute_url() != request.path:
            return HttpResponsePermanentRedirect(obj.get_absolute_url())
    raise Http404

def direction(request, slug):
    obj = TradeDirection.objects.filter(slug=slug, published=True).first()
    if not obj: return old_url(request)
    return render_page(request, 'trade/direction.html', obj, categories=visible_categories().filter(direction=obj), opposite=TradeDirection.objects.filter(published=True).exclude(pk=obj.pk).first())

def category(request, direction_slug, slug):
    obj = visible_categories().prefetch_related('products', 'sections', 'gallery').filter(direction__slug=direction_slug, slug=slug).first()
    if not obj: return old_url(request)
    return render_page(request, 'trade/category.html', obj, related=visible_categories().filter(direction=obj.direction).exclude(pk=obj.pk)[:3])

def page(request, slug):
    return render_page(request, 'trade/page.html', get_object_or_404(ContentPage, slug=slug, published=True))

@login_required
def preview(request, kind, pk):
    model = {'tradecategory': TradeCategory, 'tradedirection': TradeDirection, 'contentpage': ContentPage}.get(kind)
    if not model or not request.user.has_perm('trade.view_' + kind): raise Http404
    obj = get_object_or_404(model, pk=pk)
    template = {'tradecategory': 'category', 'tradedirection': 'direction', 'contentpage': 'page'}[kind]
    return render_page(request, f'trade/{template}.html', obj, preview=True, canonical_path=obj.get_absolute_url(), categories=visible_categories().filter(direction=obj) if model == TradeDirection else [])

def contact(request):
    obj = get_object_or_404(ContactPage, pk=1)
    form = EnquiryForm(request.POST or None, initial={'category': request.GET.get('category')})
    if request.method == 'POST':
        # Database-backed, shared across workers. Trust only REMOTE_ADDR; configure nginx real IP handling.
        address = request.META.get('REMOTE_ADDR', '')
        if settings.TRUST_LOCAL_PROXY and address in ('127.0.0.1', '::1'):
            address = request.META.get('HTTP_X_REAL_IP', address)
        key = salted_hmac('contact-rate', f'{address}/{int(time.time() // 3600)}').hexdigest()
        with transaction.atomic():
            window, _ = SubmissionWindow.objects.get_or_create(key=key)
            SubmissionWindow.objects.filter(pk=window.pk).update(attempts=F('attempts') + 1)
            window.refresh_from_db()
        if window.attempts > 10:
            response = render(request, 'trade/rate_limit.html', status=429)
            response['Retry-After'] = '3600'
            return response
        if form.is_valid():
            enquiry = form.save()
            if settings.CONTACT_NOTIFICATION_EMAIL:
                try:
                    message = '\n'.join([
                        f'Enquiry #{enquiry.pk}', f'Name: {enquiry.name}', f'Email: {enquiry.email}',
                        f'Company: {enquiry.company}', f'Phone: {enquiry.phone}',
                        f'Category: {enquiry.category or "General enquiry"}', f'Submitted: {enquiry.created_at.isoformat()}',
                        '', enquiry.message, '', f'Review: {settings.SITE_URL}/admin/trade/enquiry/{enquiry.pk}/change/',
                    ])
                    send_mail('New EuroAfrica enquiry', message, settings.DEFAULT_FROM_EMAIL, [settings.CONTACT_NOTIFICATION_EMAIL])
                except Exception:
                    logging.getLogger(__name__).warning('Notification failed for saved enquiry %s', enquiry.pk)
            return redirect('thanks')
    return render_page(request, 'trade/contact.html', obj, form=form)

def thanks(request): return render_page(request, 'trade/contact.html', get_object_or_404(ContactPage, pk=1), thanks=True, canonical_path='/contact/')

def sitemap(request):
    root = Element('urlset', xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')
    if settings.INDEXABLE and not settings.STAGING:
        objects = list(TradeDirection.objects.filter(published=True, indexable=True)) + list(visible_categories().filter(indexable=True, direction__indexable=True)) + list(ContentPage.objects.filter(published=True, indexable=True)) + list(ContactPage.objects.all())
        site = SiteSettings.objects.first()
        homepage = HomePage.objects.first()
        if homepage:
            node = SubElement(root, 'url')
            SubElement(node, 'loc').text = settings.SITE_URL + '/'
            dates = [homepage.updated_at] + [o.updated_at for o in objects]
            if site: dates.append(site.updated_at)
            SubElement(node, 'lastmod').text = max(dates).isoformat()
        for obj in objects:
            node = SubElement(root, 'url')
            SubElement(node, 'loc').text = settings.SITE_URL + obj.get_absolute_url()
            SubElement(node, 'lastmod').text = max(obj.updated_at, site.updated_at).isoformat() if site else obj.updated_at.isoformat()
    return HttpResponse(tostring(root, encoding='utf-8', xml_declaration=True), content_type='application/xml')

def robots(request):
    body = 'User-agent: *\nDisallow: /\n'
    if settings.INDEXABLE and not settings.STAGING:
        body = f'User-agent: *\nDisallow: /admin/\nDisallow: /preview/\nDisallow: /contact/thanks/\nSitemap: {settings.SITE_URL}/sitemap.xml\n'
    return HttpResponse(body, content_type='text/plain')
