"""Local read-only crawl and response timings. Run with the Django server on port 8000."""
import json
import statistics
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import urlopen
from urllib.parse import urljoin, urlsplit

BASE = 'http://127.0.0.1:8000'
class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.links = []; self.assets = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a' and attrs.get('href'): self.links.append(attrs['href'])
        if tag == 'img' and attrs.get('src'): self.assets.append(attrs['src'])
        if tag == 'link' and attrs.get('rel') == 'stylesheet': self.assets.append(attrs['href'])

queue = ['/']; visited = set(); assets = set(); errors = []; pages = []
while queue:
    path = queue.pop(0)
    if path in visited: continue
    visited.add(path)
    try:
        with urlopen(BASE + path) as response: body = response.read().decode()
        parser = Links(); parser.feed(body)
        pages.append(path)
        for link in parser.links:
            url = urlsplit(urljoin(BASE + path, link))
            if url.netloc == urlsplit(BASE).netloc and not url.path.startswith('/admin/'):
                queue.append(url.path)
        assets.update(parser.assets)
    except Exception as exc: errors.append({'path': path, 'error': str(exc)})
asset_bytes = 0
for asset in assets:
    try:
        with urlopen(urljoin(BASE, asset)) as response: asset_bytes += len(response.read())
    except Exception as exc: errors.append({'asset': asset, 'error': str(exc)})
timings = {}
for path in ['/', '/africa-to-europe/', '/africa-to-europe/cut-flowers/', '/contact/']:
    values = []
    for _ in range(10):
        started = time.perf_counter()
        with urlopen(BASE + path) as response: body = response.read()
        values.append((time.perf_counter() - started) * 1000)
    timings[path] = {'median_response_ms': round(statistics.median(values), 2), 'max_response_ms': round(max(values), 2), 'html_bytes': len(body)}
result = {'pages_reached': len(pages), 'pages': pages, 'unique_assets': len(assets), 'asset_bytes': asset_bytes, 'errors': errors, 'local_unthrottled_http_timings': timings, 'note': 'Django development server, local SQLite, 10 samples per route. Not Lighthouse or field Core Web Vitals.'}
Path('qa').mkdir(exist_ok=True)
Path('qa/audit.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
if errors: raise SystemExit(1)
