"""Read-only crawl of rendered pages. Does not change production indexing."""
import json
import time
from collections import Counter
from html.parser import HTMLParser
from urllib.parse import urlsplit
from xml.etree import ElementTree
from contextlib import nullcontext
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.test import Client, override_settings
from trade.models import HomePage, ContactPage, ContentPage, TradeDirection, TradeCategory


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.meta = {}; self.links = []; self.images = []; self.canonical = []; self.h1 = 0
        self.title = ''; self.in_title = False; self.in_json = False; self.structured = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'title': self.in_title = True
        if tag == 'h1': self.h1 += 1
        if tag == 'meta': self.meta[a.get('name', a.get('property', ''))] = a.get('content', '')
        if tag == 'link' and a.get('rel') == 'canonical': self.canonical.append(a.get('href'))
        if tag == 'a': self.links.append(a.get('href', ''))
        if tag == 'img': self.images.append(a)
        if tag == 'script' and a.get('type') == 'application/ld+json': self.in_json = True

    def handle_endtag(self, tag):
        if tag == 'title': self.in_title = False
        if tag == 'script': self.in_json = False

    def handle_data(self, data):
        if self.in_title: self.title += data
        if self.in_json: self.structured.append(json.loads(data))


class Command(BaseCommand):
    help = 'Audit rendered SEO, canonical URLs, sitemap membership, navigation and image markup.'

    def add_arguments(self, parser):
        parser.add_argument('--simulate-indexing', action='store_true', help='Temporarily enable indexing only inside this audit process.')
        parser.add_argument('--json', action='store_true')

    def handle(self, **options):
        context = override_settings(INDEXABLE=True, STAGING=False) if options['simulate_indexing'] else nullcontext()
        with context:
            self.audit(options)

    def audit(self, options):
        client = Client(HTTP_HOST=urlsplit(settings.SITE_URL).netloc, HTTP_X_FORWARDED_PROTO='https')
        objects = list(HomePage.objects.all()) + list(ContactPage.objects.all()) + list(ContentPage.objects.filter(published=True)) + list(TradeDirection.objects.filter(published=True)) + list(TradeCategory.objects.filter(published=True, direction__published=True).select_related('direction'))
        rows = []; errors = []; links = set(); expected_sitemap = set()
        for obj in objects:
            path = '/' if isinstance(obj, HomePage) else obj.get_absolute_url()
            started = time.perf_counter(); response = client.get(path, secure=True); elapsed = (time.perf_counter() - started) * 1000
            parser = PageParser(); parser.feed(response.content.decode())
            canonical = settings.SITE_URL + path
            indexable = settings.INDEXABLE and not settings.STAGING and getattr(obj, 'indexable', True) and (not isinstance(obj, TradeCategory) or obj.direction.indexable)
            if indexable: expected_sitemap.add(canonical)
            if response.status_code != 200: errors.append(f'{path}: HTTP {response.status_code}')
            if parser.h1 != 1: errors.append(f'{path}: expected exactly one H1')
            if parser.canonical != [canonical]: errors.append(f'{path}: incorrect canonical')
            if not parser.title or not parser.meta.get('description'): errors.append(f'{path}: missing title/description')
            if indexable and ('noindex' in parser.meta.get('robots', '') or 'noindex' in response.get('X-Robots-Tag', '')): errors.append(f'{path}: unexpectedly noindex')
            types = {item.get('@type') for data in parser.structured for item in data.get('@graph', [])}
            if not {'Organization', 'WebSite'}.issubset(types) or (path != '/' and 'BreadcrumbList' not in types): errors.append(f'{path}: missing structured data')
            for image in parser.images:
                if not image.get('width') or not image.get('height') or 'alt' not in image: errors.append(f'{path}: missing image dimensions/alt attribute')
            links.update(urlsplit(link).path for link in parser.links if link.startswith('/'))
            rows.append(dict(path=path, title=parser.title, description=parser.meta.get('description'), images=len(parser.images), html_bytes=len(response.content), render_ms=round(elapsed, 1)))
        for field in ('title', 'description'):
            duplicates = [value for value, count in Counter(row[field] for row in rows).items() if count > 1]
            if duplicates: errors.append(f'Duplicate {field}: {duplicates}')
        for row in rows:
            if row['path'] != '/' and row['path'] not in links: errors.append(f"Orphan page: {row['path']}")
        response = client.get('/sitemap.xml', secure=True)
        actual = {node.text for node in ElementTree.fromstring(response.content).iter('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')}
        if actual != expected_sitemap: errors.append('Sitemap differs from published, indexable canonical pages')
        result = dict(simulated_indexing=options['simulate_indexing'], pages=rows, sitemap_urls=len(actual), errors=errors,
                      note='In-process timings are diagnostics, not Lighthouse or real-user Core Web Vitals.')
        self.stdout.write(json.dumps(result, indent=2) if options['json'] else f"Audited {len(rows)} pages and {len(actual)} sitemap URLs; {len(errors)} errors. " + ' '.join(errors))
        if errors: raise CommandError('SEO audit failed.')
