"""Offline editorial transfer: explicit UTF-8, conservative merges and verified media.

No users, enquiries, secrets, rate limits or initialization markers are transferred.
No model save/upload signals run: stored media names must remain byte-for-byte paths.
"""
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path, PurePosixPath
from datetime import timedelta

from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.management.base import CommandError
from django.core.serializers.json import DjangoJSONEncoder
from django.core.management.color import no_style
from django.db import connection, transaction, models
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone

MODELS = ('sitesettings', 'homepage', 'tradedirection', 'tradecategory',
          'contentpage', 'contactpage', 'categoryproduct', 'categorysection',
          'categoryimage', 'footerlink', 'homefeature', 'contentsection',
          'urlhistory', 'contenttranslation')
SINGLETONS = {'sitesettings', 'homepage', 'contactpage'}
ANCHORS = {'categoryproduct': ('category_id', 'name'),
           'categorysection': ('category_id', 'heading'),
           'categoryimage': ('category_id', 'image'),
           'homefeature': ('homepage_id', 'heading'),
           'contentsection': ('page_id', 'heading')}
EXCLUDED = ('enquiry', 'submissionwindow', 'submissionreceipt', 'stockimageinitialization')


def model(name):
    if name not in MODELS:
        raise CommandError('Unapproved content model.')
    return apps.get_model('trade', name)


def encode(data):
    return json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2, cls=DjangoJSONEncoder)


def digest(data):
    return hashlib.sha256(encode(data).encode('utf-8')).hexdigest()


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def migration_hash(path):
    """Hash migration text with universal LF endings; preserve all other bytes.

    Media, backups and package checksums continue to use the raw file_hash helper.
    """
    content = Path(path).read_bytes().replace(b'\r\n', b'\n').replace(b'\r', b'\n')
    return hashlib.sha256(content).hexdigest()


def write_json(path, data, exclusive=False):
    path = Path(path)
    # Never silently replace a reviewed plan, export, backup or rollback journal.
    with path.open('x' if exclusive else 'w', encoding='utf-8', newline='\n') as stream:
        if os.name != 'nt':
            os.chmod(path, 0o600)
        stream.write(encode(data) + '\n')


def read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError, UnicodeError) as exc:
        raise CommandError('Cannot read valid UTF-8 JSON input.') from exc


def safe_path(root, name):
    p = PurePosixPath(name)
    if not name or '\\' in name or ':' in name or p.is_absolute() or '..' in p.parts or str(p) != name:
        raise CommandError('Unsafe media path in input.')
    root = Path(root).resolve()
    target = root.joinpath(*p.parts)
    if not target.resolve().is_relative_to(root):
        raise CommandError('Media path escapes its root (including symlinks).')
    return target


def state():
    return {name: [row(obj) for obj in model(name).objects.order_by('pk')] for name in MODELS}


def row(obj):
    values = {}
    for field in obj._meta.concrete_fields:
        value = field.value_from_object(obj)
        values[field.attname] = str(value) if isinstance(field, models.FileField) else value
    return json.loads(encode(values))


def schema():
    executor = MigrationExecutor(connection)
    executor.loader.check_consistent_history(connection)
    if executor.migration_plan(executor.loader.graph.leaf_nodes()):
        raise CommandError('Pending migrations: back up, inspect migrate --plan, then apply reviewed migrations first.')
    migration_dir = Path(settings.BASE_DIR) / 'trade' / 'migrations'
    return {p.name: migration_hash(p) for p in sorted(migration_dir.iterdir())
            if p.suffix in ('.py', '.json') and p.name != '__init__.py'}


def require_postgres():
    if connection.vendor != 'postgresql':
        raise CommandError('Production writes require PostgreSQL. SQLite import/rollback is deliberately refused.')


def lock_tables():
    # Readers remain online; concurrent admin/enquiry writes wait briefly or we time out.
    if connection.vendor == 'postgresql':
        tables = [m._meta.db_table for m in apps.get_app_config('trade').get_models()]
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL lock_timeout = '5s'")
            cursor.execute('LOCK TABLE ' + ', '.join(connection.ops.quote_name(t) for t in tables)
                           + ' IN SHARE ROW EXCLUSIVE MODE')


def media_references(snapshot):
    paths = set()
    for name, rows in snapshot.items():
        fields = [f.attname for f in model(name)._meta.fields if isinstance(f, models.FileField)]
        paths.update(r[f] for r in rows for f in fields if r[f])
    return paths


def export_package(destination):
    destination = Path(destination)
    migration_hashes = schema()
    if destination.exists():
        raise CommandError('Export destination already exists; use a new directory.')
    with transaction.atomic():
        lock_tables()
        snapshot = state()
    # ContentType IDs are database-local; export stable app/model labels instead.
    for r in snapshot['contenttranslation']:
        ct = ContentType.objects.get(pk=r.pop('content_type_id'))
        if ct.app_label != 'trade' or ct.model not in MODELS:
            raise CommandError('Translation points outside the approved content models.')
        r['target_model'] = ct.model
    destination.mkdir(parents=True, mode=0o700)
    try:
        paths = media_references(snapshot)
        root = Path(settings.MEDIA_ROOT)
        for name in tuple(paths):
            if name.endswith('.webp'):
                for width in (480, 960):
                    variant = name[:-5] + f'-{width}.webp'
                    if safe_path(root, variant).is_file():
                        paths.add(variant)
        manifest = {}
        for name in sorted(paths):
            source = safe_path(root, name)
            if not source.is_file():
                raise CommandError(f'Referenced media missing: {name}')
            target = safe_path(destination / 'media', name)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            manifest[name] = {'sha256': file_hash(target), 'bytes': target.stat().st_size}
        data = {'format': 1, 'created_at': timezone.now().isoformat(), 'migrations': migration_hashes,
                'records': snapshot, 'media': manifest, 'excluded': list(EXCLUDED)}
        data['package_sha256'] = digest(data)
        write_json(destination / 'content.json', data, exclusive=True)
        return data
    except Exception:
        # Keep incomplete package for diagnosis, but no usable content.json is emitted.
        raise


def load_package(directory):
    directory = Path(directory)
    data = read_json(directory / 'content.json')
    claimed = data.pop('package_sha256', None)
    if data.get('format') != 1 or digest(data) != claimed:
        raise CommandError('Package checksum/version mismatch.')
    data['package_sha256'] = claimed
    if data['migrations'] != schema():
        raise CommandError('Trade migration files differ. Deploy/review matching code and migrations before merging.')
    if set(data['records']) != set(MODELS):
        raise CommandError('Unexpected or missing content models.')
    for name, info in data['media'].items():
        path = safe_path(directory / 'media', name)
        if not path.is_file() or path.stat().st_size != info['bytes'] or file_hash(path) != info['sha256']:
            raise CommandError(f'Missing or changed package media: {name}')
        existing = safe_path(settings.MEDIA_ROOT, name)
        if existing.exists() and (not existing.is_file() or file_hash(existing) != info['sha256']):
            raise CommandError(f'Media collision; production file will NOT be overwritten: {name}')
    if not media_references(data['records']).issubset(data['media']):
        raise CommandError('Media manifest does not cover all referenced files.')
    return data


def resolve_existing(name, incoming, current):
    if name in SINGLETONS:
        if incoming['id'] != 1 or len(current) > 1 or (current and current[0]['id'] != 1):
            raise CommandError('Invalid singleton identity.')
        return current[0] if current else None
    if name in ('tradedirection', 'tradecategory'):
        by_seed = [r for r in current if incoming.get('seed_key') and r['seed_key'] == incoming['seed_key']]
        by_slug = [r for r in current if r['slug'] == incoming['slug'] and
                   (name != 'tradecategory' or r['direction_id'] == incoming['direction_id'])]
        candidates = {r['id']: r for r in by_seed + by_slug}
        if len(candidates) > 1 or (by_slug and by_slug[0].get('seed_key') and incoming.get('seed_key')
                                   and by_slug[0]['seed_key'] != incoming['seed_key']):
            raise CommandError(f'Ambiguous seed/slug identity: {name} #{incoming["id"]}.')
        return next(iter(candidates.values()), None)
    keys = {'contentpage': ('slug',), 'footerlink': ('group', 'destination'),
            'urlhistory': ('path',), 'contenttranslation': ('content_type_id', 'object_id', 'language', 'field')}
    if name in ANCHORS:
        anchors = ANCHORS[name]
        same_pk = next((r for r in current if r['id'] == incoming['id']), None)
        matches = [r for r in current if all(r[f] == incoming[f] for f in anchors)]
        if same_pk and not all(same_pk[f] == incoming[f] for f in anchors):
            raise CommandError(f'Child PK identity conflict: {name} #{incoming["id"]}; reconcile explicitly before transfer.')
        if len(matches) > 1:
            raise CommandError(f'Ambiguous child identity: {name} #{incoming["id"]}.')
        return same_pk or (matches[0] if matches else None)
    matches = [r for r in current if all(r[f] == incoming[f] for f in keys[name])]
    if len(matches) > 1:
        raise CommandError(f'Duplicate natural identity: {name}.')
    return matches[0] if matches else None


def plan_merge(data, resolutions=None):
    resolutions = resolutions or {}
    if not isinstance(resolutions, dict) or any(v not in ('local', 'production') for v in resolutions.values()):
        raise CommandError('Resolutions must map conflict keys to local or production.')
    original = state()
    current = json.loads(encode(original))
    mapping, operations, conflicts, skipped, used = {}, [], [], [], set()
    for name in MODELS:
        seen_source, seen_target = set(), set()
        for source in data['records'][name]:
            incoming = dict(source)
            source_pk = incoming['id']
            if source_pk in seen_source:
                raise CommandError('Duplicate source primary key.')
            seen_source.add(source_pk)
            for field in model(name)._meta.fields:
                if isinstance(field, models.ForeignKey) and field.related_model._meta.app_label == 'trade':
                    incoming[field.attname] = mapping[(field.related_model._meta.model_name, incoming[field.attname])]
            if name == 'urlhistory':
                kind = incoming['kind'].lower()
                if kind not in ('tradecategory', 'tradedirection'):
                    raise CommandError('Unexpected URL history target.')
                incoming['object_id'] = mapping[(kind, incoming['object_id'])]
            if name == 'contenttranslation':
                target_name = incoming.pop('target_model')
                if target_name not in MODELS or (target_name, incoming['object_id']) not in mapping:
                    raise CommandError('Translation target is missing.')
                incoming['object_id'] = mapping[(target_name, incoming['object_id'])]
                # Read only: planning must not create content types.
                incoming['content_type_id'] = ContentType.objects.get(app_label='trade', model=target_name).pk
                from .content_fields import CONTENT_FIELDS
                if incoming['field'] not in CONTENT_FIELDS.get(target_name, ()) or incoming['language'] not in dict(settings.LANGUAGES) or incoming['language'] == 'en':
                    raise CommandError('Invalid translation field/language.')
                parent = next(r for r in current[target_name] if r['id'] == incoming['object_id'])
                if incoming['source_text'] != parent[incoming['field']]:
                    skipped.append({'model': name, 'source_pk': source_pk, 'target_model': target_name,
                                    'object_id': incoming['object_id'], 'field': incoming['field'],
                                    'language': incoming['language'], 'reason': 'source differs from retained production text'})
                    continue
            expected_fields = {f.attname for f in model(name)._meta.concrete_fields}
            if set(incoming) != expected_fields:
                raise CommandError(f'Field/schema mismatch: {name}.')
            existing = resolve_existing(name, incoming, current[name])
            if existing:
                target_pk = existing['id']
            else:
                occupied = {r['id'] for r in current[name]}
                target_pk = source_pk if source_pk not in occupied else max(occupied, default=0) + 1
            if target_pk in seen_target:
                raise CommandError('Multiple source records resolve to one target.')
            seen_target.add(target_pk)
            mapping[(name, source_pk)] = target_pk
            incoming['id'] = target_pk
            if existing is None:
                current[name].append(incoming)
                operations.append({'model': name, 'pk': target_pk, 'before': None, 'after': incoming})
                continue
            after = dict(existing)
            for field, value in incoming.items():
                if field in ('id', 'updated_at') or value == existing[field]:
                    continue
                key = f'{name}:{source_pk}:{field}'
                # NULL/empty text are fillable. False and zero are meaningful and preserved.
                if existing[field] in ('', None) and value not in ('', None) and key not in resolutions:
                    after[field] = value
                else:
                    choice = resolutions.get(key, 'production')
                    used.add(key)
                    conflicts.append({'key': key, 'model': name, 'target_pk': target_pk,
                                      'field': field, 'production': existing[field], 'local': value,
                                      'decision': choice, 'explicit': key in resolutions})
                    if choice == 'local':
                        # Changing identifiers would change live URLs/relations; do it in admin instead.
                        protected = {'slug', 'seed_key', 'direction_id', 'category_id', 'page_id', 'homepage_id',
                                     'path', 'kind', 'object_id', 'content_type_id', 'language', 'field', 'destination', 'group'}
                        if field in protected:
                            raise CommandError(f'Cannot force an identity/relationship change: {key}')
                        after[field] = value
            if after != existing:
                if name == 'contenttranslation' and after['source_text'] != parent[incoming['field']]:
                    raise CommandError('Translation resolution must include its matching source_text; do not mix translation versions.')
                operations.append({'model': name, 'pk': target_pk, 'before': dict(existing), 'after': after})
                existing.update(after)
    if set(resolutions) - used:
        raise CommandError('Unknown or obsolete resolution keys; regenerate the preview without them.')
    return {'format': 1, 'package_sha256': data['package_sha256'], 'database': database_id(),
            'before_sha256': digest(original), 'resolutions': resolutions, 'operations': operations,
            'conflicts': conflicts, 'skipped_translations': skipped,
            'source_counts': {k: len(v) for k, v in data['records'].items()},
            'before_counts': {k: len(v) for k, v in original.items()},
            'after_counts': {k: len(v) for k, v in current.items()}}


def database_id():
    cfg = connection.settings_dict
    return digest({k: str(cfg.get(k, '')) for k in ('ENGINE', 'NAME', 'HOST', 'PORT', 'USER')})


def pg_environment():
    require_postgres()
    cfg = connection.settings_dict
    env = {k: v for k, v in os.environ.items() if not k.startswith('PG')}
    for key, field in [('PGDATABASE', 'NAME'), ('PGHOST', 'HOST'), ('PGPORT', 'PORT'), ('PGUSER', 'USER'), ('PGPASSWORD', 'PASSWORD')]:
        if cfg.get(field):
            env[key] = str(cfg[field])
    for key in ('sslmode', 'sslrootcert', 'connect_timeout'):
        if key in cfg.get('OPTIONS', {}):
            env[{'sslmode': 'PGSSLMODE', 'sslrootcert': 'PGSSLROOTCERT', 'connect_timeout': 'PGCONNECT_TIMEOUT'}[key]] = str(cfg['OPTIONS'][key])
    return env


def postgres_backup(destination):
    require_postgres()
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False, mode=0o700)
    dump = destination / 'database.dump'
    for args in (['pg_dump', '--format=custom', '--no-owner', '--no-acl', '--file', str(dump)],
                 ['pg_restore', '--list', str(dump)]):
        try:
            result = subprocess.run(args, env=pg_environment(), capture_output=True, check=False)
        except OSError as exc:
            raise CommandError('Install matching PostgreSQL client tools; backup did not complete.') from exc
        if result.returncode:
            # PostgreSQL stderr can contain infrastructure identifiers; never echo credentials/settings.
            raise CommandError('PostgreSQL backup validation failed; no usable backup receipt was written.')
    if os.name != 'nt':
        os.chmod(dump, 0o600)
    receipt = {'database': database_id(), 'created_at': timezone.now().isoformat(), 'sha256': file_hash(dump)}
    write_json(destination / 'backup.json', receipt, exclusive=True)
    return receipt


def check_backup(directory):
    receipt = read_json(Path(directory) / 'backup.json')
    from django.utils.dateparse import parse_datetime
    created = parse_datetime(receipt['created_at'])
    if receipt['database'] != database_id() or receipt['sha256'] != file_hash(Path(directory) / 'database.dump'):
        raise CommandError('Backup does not match this database or has changed.')
    if not created or not timezone.now() - timedelta(hours=24) <= created <= timezone.now():
        raise CommandError('Create a fresh PostgreSQL backup (receipt expires after 24 hours).')


def install_media(directory, manifest):
    added = []
    for name, info in manifest.items():
        target = safe_path(settings.MEDIA_ROOT, name)
        root = Path(settings.MEDIA_ROOT).resolve()
        if not root.is_dir():
            raise CommandError('The configured production MEDIA_ROOT must already exist.')
        parent = root
        for part in target.relative_to(root).parts[:-1]:
            parent = parent / part
            try:
                parent.mkdir()
                # Public media must be traversable by Nginx even with a private backup umask.
                os.chmod(parent, 0o755)
            except FileExistsError:
                if not parent.is_dir():
                    raise CommandError('A media parent path is not a directory.')
        if target.exists():
            if file_hash(target) != info['sha256']:
                raise CommandError(f'Concurrent media collision: {name}')
            continue
        # Hard-link a fully written temp file without overwriting a concurrent upload.
        fd, temp = tempfile.mkstemp(prefix='.transfer-', dir=target.parent)
        try:
            with os.fdopen(fd, 'wb') as stream, safe_path(Path(directory) / 'media', name).open('rb') as source:
                shutil.copyfileobj(source, stream)
                stream.flush()
                os.fsync(stream.fileno())
            if file_hash(temp) != info['sha256']:
                raise CommandError('Media changed during copy.')
            os.chmod(temp, 0o644)
            try:
                os.link(temp, target)
                added.append(name)
            except FileExistsError:
                if file_hash(target) != info['sha256']:
                    raise CommandError(f'Concurrent media collision: {name}')
        finally:
            Path(temp).unlink(missing_ok=True)
    return added


def typed_row(name, values):
    result = {}
    for field in model(name)._meta.concrete_fields:
        value = values[field.attname]
        result[field.attname] = (field.target_field if isinstance(field, models.ForeignKey) else field).to_python(value)
    return result


def execute_operations(operations):
    for op in operations:
        cls = model(op['model'])
        values = typed_row(op['model'], op['after'])
        obj = cls(**values)
        # File validators describe NEW uploads; these are existing verified paths.
        obj.clean_fields(exclude=[f.name for f in cls._meta.fields if isinstance(f, models.FileField)])
        if op['before'] is None:
            cls.objects.bulk_create([obj])
        # QuerySet.update avoids URL/image/parent-touch signals and preserves timestamps.
        cls.objects.filter(pk=op['pk']).update(**{k: v for k, v in values.items() if k != 'id'})
    with connection.cursor() as cursor:
        for sql in connection.ops.sequence_reset_sql(no_style(), [model(n) for n in MODELS]):
            cursor.execute(sql)


def apply_package(directory, reviewed_plan, backup, journal):
    require_postgres()
    check_backup(backup)
    data = load_package(directory)
    approved = read_json(reviewed_plan)
    if Path(journal).exists():
        raise CommandError('Journal already exists; choose a new path.')
    # Copy first; failures can leave harmless unreferenced files, never broken DB paths.
    # No existing media is replaced or deleted, including during rollback.
    proposed = plan_merge(data, approved.get('resolutions'))
    if proposed != approved:
        raise CommandError('Reviewed plan is stale or modified. Generate/review a fresh plan.')
    added = install_media(directory, data['media'])
    with transaction.atomic():
        lock_tables()
        fresh = plan_merge(data, approved.get('resolutions'))
        if fresh != approved:
            raise CommandError('Production changed after preview. No database edits applied; regenerate plan.')
        execute_operations(fresh['operations'])
        journal_data = {'database': database_id(), 'package_sha256': data['package_sha256'],
                        'operations': fresh['operations'], 'after_sha256': digest(state()),
                        'added_media': added, 'created_at': timezone.now().isoformat()}
        journal_data['journal_sha256'] = digest(journal_data)
        write_json(journal, journal_data, exclusive=True)
    return fresh


def rollback_journal(path):
    require_postgres()
    schema()
    journal = read_json(path)
    if journal.pop('journal_sha256', None) != digest(journal):
        raise CommandError('Rollback journal checksum mismatch.')
    if journal['database'] != database_id():
        raise CommandError('Rollback journal belongs to another database.')
    with transaction.atomic():
        lock_tables()
        if digest(state()) != journal['after_sha256']:
            raise CommandError('Content changed since merge. Automatic rollback refused; reconcile the journal manually.')
        inserted = {(op['model'], op['pk']) for op in journal['operations'] if op['before'] is None}
        # Operational data is never rolled back. New enquiries can refer to new categories.
        category_ids = [pk for name, pk in inserted if name == 'tradecategory']
        if apps.get_model('trade', 'Enquiry').objects.filter(category_id__in=category_ids).exists():
            raise CommandError('New enquiries reference imported categories; automatic rollback refused.')
        for op in reversed(journal['operations']):
            cls = model(op['model'])
            if op['before'] is None:
                # Reverse dependency order, without cascading ORM signals/deletes.
                cls.objects.filter(pk=op['pk'])._raw_delete('default')
            else:
                values = typed_row(op['model'], op['before'])
                cls.objects.filter(pk=op['pk']).update(**{k: v for k, v in values.items() if k != 'id'})
    return len(journal['operations'])


def verify_media():
    missing = []
    paths = media_references(state())
    for name in sorted(paths):
        if not safe_path(settings.MEDIA_ROOT, name).is_file():
            missing.append(name)
    return {'referenced_files': len(paths), 'missing_files': missing,
            'counts': {name: model(name).objects.count() for name in MODELS}}
