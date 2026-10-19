import json
from pathlib import Path
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen, HTTPRedirectHandler, build_opener
import hashlib
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import override
from django.utils.html import escape
from trade import content_transfer as transfer


class SameOriginRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlsplit(req.full_url).netloc != urlsplit(newurl).netloc or urlsplit(newurl).scheme != 'https':
            raise CommandError('HTTP verification redirected outside the canonical HTTPS origin.')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def check_http():
    origin = settings.SITE_URL.rstrip('/')
    if urlsplit(origin).scheme != 'https':
        raise CommandError('--http requires the real HTTPS SITE_URL, not localhost.')
    opener = build_opener(SameOriginRedirect())
    checked = 0
    pages = [(transfer.model('homepage').objects.get(pk=1), '/', 'hero_heading'),
             (transfer.model('contactpage').objects.get(pk=1), '/contact/', 'title')]
    for name in ('tradedirection', 'tradecategory', 'contentpage'):
        for obj in transfer.model(name).objects.filter(published=True):
            if name == 'tradecategory' and not obj.direction.published:
                continue
            pages.append((obj, obj.get_absolute_url(), 'title' if name != 'tradedirection' else 'heading'))
    for lang, _ in settings.LANGUAGES:
        for obj, path, field in pages:
            req = Request(origin + quote(path, safe='/'), headers={'Cookie': f'{settings.LANGUAGE_COOKIE_NAME}={lang}', 'User-Agent': 'EuroAfrica-content-verification/1'})
            with opener.open(req, timeout=30) as response:
                html = response.read().decode('utf-8')
                if response.status != 200 or response.url != req.full_url:
                    raise CommandError('Page verification did not reach the expected page.')
            with override(lang):
                expected = str(escape(obj.translated[field]))
            if f'lang="{lang}"' not in html or f'dir="{"rtl" if lang == "ar" else "ltr"}"' not in html or expected not in html:
                raise CommandError(f'HTTP language/content check failed: {lang} {path}')
            checked += 1
    paths = transfer.media_references(transfer.state())
    for name in tuple(paths):
        if name.endswith('.webp'):
            paths.update(name[:-5] + f'-{w}.webp' for w in (480, 960)
                         if transfer.safe_path(settings.MEDIA_ROOT, name[:-5] + f'-{w}.webp').is_file())
    if settings.MEDIA_URL != '/media/':
        raise CommandError('Expected /media/ URL for the existing VPS architecture.')
    for name in sorted(paths):
        url = origin + '/media/' + quote(name, safe='/')
        with opener.open(Request(url, headers={'User-Agent': 'EuroAfrica-content-verification/1'}), timeout=30) as response:
            h = hashlib.sha256()
            for block in iter(lambda: response.read(1024 * 1024), b''):
                h.update(block)
            if response.status != 200 or h.hexdigest() != transfer.file_hash(transfer.safe_path(settings.MEDIA_ROOT, name)):
                raise CommandError(f'HTTPS media differs from disk: {name}')
    return {'https_pages_checked': checked, 'https_media_checked': len(paths)}


class Command(BaseCommand):
    help = 'Preview-first UTF-8 editorial/media transfer. Production writes require PostgreSQL and a backup.'

    def add_arguments(self, parser):
        commands = parser.add_subparsers(dest='action', required=True)
        export = commands.add_parser('export')
        export.add_argument('--output', required=True)
        backup = commands.add_parser('backup')
        backup.add_argument('--output', required=True)
        preview = commands.add_parser('plan')
        preview.add_argument('--package', required=True)
        preview.add_argument('--output', required=True)
        preview.add_argument('--resolutions')
        apply = commands.add_parser('apply')
        apply.add_argument('--package', required=True)
        apply.add_argument('--plan', required=True)
        apply.add_argument('--backup', required=True)
        apply.add_argument('--journal', required=True)
        rollback = commands.add_parser('rollback')
        rollback.add_argument('--journal', required=True)
        rollback.add_argument('--confirm', action='store_true')
        verify = commands.add_parser('verify')
        verify.add_argument('--package')
        verify.add_argument('--output', required=True)
        verify.add_argument('--http', action='store_true')

    def handle(self, **options):
        action = options['action']
        try:
            if action == 'export':
                data = transfer.export_package(options['output'])
                self.stdout.write(f'UTF-8 package created: {sum(map(len, data["records"].values()))} records, {len(data["media"])} media files.')
            elif action == 'backup':
                transfer.postgres_backup(options['output'])
                self.stdout.write('PostgreSQL custom-format backup and checksum receipt created; archive listing verified.')
            elif action == 'plan':
                data = transfer.load_package(options['package'])
                choices = transfer.read_json(options['resolutions']) if options['resolutions'] else None
                plan = transfer.plan_merge(data, choices)
                transfer.write_json(options['output'], plan, exclusive=True)
                self.summarize(plan)
                self.stdout.write('Preview only. No database or production media changes.')
            elif action == 'apply':
                plan = transfer.apply_package(options['package'], options['plan'], options['backup'], options['journal'])
                self.summarize(plan)
                self.stdout.write('Merge committed. Keep the rollback journal and PostgreSQL backup private.')
            elif action == 'rollback':
                if not options['confirm']:
                    raise CommandError('Rollback requires --confirm; first review the journal. Later content edits cause a refusal.')
                count = transfer.rollback_journal(options['journal'])
                self.stdout.write(f'Reversed {count} merge operations. Existing files and all operational data retained.')
            elif action == 'verify':
                transfer.schema()
                report = transfer.verify_media()
                if options['package']:
                    plan = transfer.plan_merge(transfer.load_package(options['package']))
                    report.update(pending_operations=len(plan['operations']), conflicts=plan['conflicts'],
                                  skipped_translations=plan['skipped_translations'], source_counts=plan['source_counts'])
                # Explain untranslated values instead of treating matching counts as proof.
                from trade.content_fields import CONTENT_FIELDS
                from django.contrib.contenttypes.models import ContentType
                gaps = []
                for name, fields in CONTENT_FIELDS.items():
                    for obj in transfer.model(name).objects.all():
                        if hasattr(obj, 'published') and not obj.published:
                            continue
                        parent = getattr(obj, 'category', None) or getattr(obj, 'page', None)
                        if parent is not None and not parent.published:
                            continue
                        for field in fields:
                            source = getattr(obj, field)
                            if not source or source == 'EuroAfrica':
                                continue
                            for lang, _ in settings.LANGUAGES:
                                if lang == 'en':
                                    continue
                                if not obj.translations.filter(language=lang, field=field, source_text=source).exclude(text='').exists():
                                    gaps.append({'model': name, 'pk': obj.pk, 'field': field, 'language': lang})
                report['translation_gaps'] = gaps
                report['categories_without_image'] = list(transfer.model('tradecategory').objects.filter(published=True, image='', hero_image='').values('id', 'slug'))
                transfer.write_json(options['output'], report, exclusive=True)
                if options['http']:
                    report.update(check_http())
                    transfer.write_json(options['output'], report)
                self.stdout.write(json.dumps(report['counts'], sort_keys=True))
                self.stdout.write(f'Referenced files: {report["referenced_files"]}; missing: {len(report["missing_files"])}; translation gaps: {len(gaps)}; remaining merge operations: {report.get("pending_operations", 0)}.')
                if report['missing_files'] or gaps or report.get('pending_operations'):
                    raise CommandError('Verification found unresolved gaps; inspect the UTF-8 report. No data was changed.')
        except CommandError:
            raise
        except (OSError, ValueError, KeyError, ValidationError) as exc:
            # Inputs can be malformed; avoid a traceback exposing database connection information.
            raise CommandError(f'Transfer stopped safely ({type(exc).__name__}); inspect inputs and file permissions.') from exc

    def summarize(self, plan):
        created = sum(op['before'] is None for op in plan['operations'])
        self.stdout.write(f'Creates: {created}; updates: {len(plan["operations"])-created}; recorded conflicts: {len(plan["conflicts"])}; skipped source-mismatched translations: {len(plan["skipped_translations"])}.')
