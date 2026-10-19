import io
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from trade import content_transfer as t
from trade.models import HomePage, TradeCategory, TradeDirection, ContentTranslation, Enquiry, SubmissionWindow


class ContentTransferTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_content', stdout=io.StringIO())
        call_command('seed_translations', stdout=io.StringIO())

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.media = self.root / 'media'
        self.settings_override = override_settings(MEDIA_ROOT=self.media)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        for name in t.media_references(t.state()):
            p = t.safe_path(self.media, name)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b'test media bytes')
        self.package = self.root / 'package'

    def export(self):
        return t.export_package(self.package)

    def apply(self, plan):
        plan_path = self.root / 'plan.json'
        t.write_json(plan_path, plan)
        with patch.object(t, 'require_postgres'), patch.object(t, 'check_backup'):
            return t.apply_package(self.package, plan_path, 'test-backup', self.root / 'journal.json')

    def test_utf8_round_trip_and_exclusions(self):
        text = 'العربية Magyar őű Українська Français été Deutsch Größe'
        HomePage.objects.filter(pk=1).update(hero_text=text)
        SubmissionWindow.objects.create(key='do-not-export')
        Enquiry.objects.create(name='Private customer', email='private@example.org', message='Do not export')
        data = self.export()
        raw = (self.package / 'content.json').read_bytes()
        self.assertIn(text, raw.decode('utf-8'))
        self.assertNotIn(b'Private customer', raw)
        self.assertEqual(set(data['records']), set(t.MODELS))
        self.assertEqual(t.load_package(self.package), data)

    def test_blank_file_reference_filled_without_mutating_preview(self):
        home = HomePage.objects.get(pk=1)
        HomePage.objects.filter(pk=1).update(hero_image='content/custom.webp')
        p = self.media / 'content/custom.webp';p.parent.mkdir(parents=True, exist_ok=True);p.write_bytes(b'image')
        self.export()
        HomePage.objects.filter(pk=1).update(hero_image='')
        before = t.digest(t.state())
        plan = t.plan_merge(t.load_package(self.package))
        self.assertEqual(t.digest(t.state()), before)
        self.assertTrue(any(op['model']=='homepage' and op['after']['hero_image']=='content/custom.webp' for op in plan['operations']))
        self.apply(plan)
        self.assertEqual(HomePage.objects.get(pk=1).hero_image.name, 'content/custom.webp')
        self.assertEqual(t.plan_merge(t.load_package(self.package))['operations'], [])

    def test_production_text_and_false_preserved_and_conflicts_reported(self):
        self.export()
        HomePage.objects.filter(pk=1).update(hero_heading='New production heading', show_about=False)
        plan = t.plan_merge(t.load_package(self.package))
        self.assertTrue(any(c['key']=='homepage:1:hero_heading' for c in plan['conflicts']))
        self.assertFalse(HomePage.objects.get(pk=1).show_about)
        self.assertGreater(len(plan['skipped_translations']), 0)
        self.assertFalse(any(op['model']=='homepage' for op in plan['operations']))

    def test_explicit_resolution_only_overwrites_reviewed_field(self):
        local = HomePage.objects.get(pk=1).hero_heading
        self.export()
        HomePage.objects.filter(pk=1).update(hero_heading='New production heading')
        plan = t.plan_merge(t.load_package(self.package), {'homepage:1:hero_heading':'local'})
        self.apply(plan)
        self.assertEqual(HomePage.objects.get(pk=1).hero_heading, local)

    def test_explicit_keep_can_preserve_intentionally_empty_production_field(self):
        self.export()
        HomePage.objects.filter(pk=1).update(hero_heading='')
        plan = t.plan_merge(t.load_package(self.package), {'homepage:1:hero_heading':'production'})
        self.assertFalse(any(op['model']=='homepage' for op in plan['operations']))
        self.assertEqual(plan['conflicts'][0]['decision'], 'production')

    def test_generic_translation_ids_remapped(self):
        category = TradeCategory.objects.first()
        data = self.export()
        source_id = category.pk
        new_id = 900
        # Simulate an independently seeded target with different row primary keys.
        ct = ContentType.objects.get_for_model(category)
        ContentTranslation.objects.filter(content_type=ct, object_id=source_id).delete()
        TradeCategory.objects.filter(pk=source_id).update(id=new_id)
        plan = t.plan_merge(data)
        creates = [op for op in plan['operations'] if op['model']=='contenttranslation']
        self.assertTrue(creates)
        self.assertTrue(all(op['after']['object_id']==new_id for op in creates))
        self.apply(plan)
        self.assertTrue(ContentTranslation.objects.filter(content_type=ct, object_id=new_id).exists())
        self.assertEqual(t.plan_merge(t.load_package(self.package))['operations'], [])

    def test_unrelated_pk_collision_does_not_overwrite_category(self):
        category = TradeCategory.objects.first()
        original_id = category.pk
        data = self.export()
        category.translations.all().delete()
        TradeCategory.objects.filter(pk=original_id).update(seed_key='production-only', slug='production-only')
        plan = t.plan_merge(data)
        op = next(op for op in plan['operations'] if op['model']=='tradecategory')
        self.assertIsNone(op['before'])
        self.assertNotEqual(op['pk'], original_id)
        self.apply(plan)
        self.assertEqual(TradeCategory.objects.get(pk=original_id).slug, 'production-only')

    def test_stale_reviewed_plan_aborts(self):
        self.export()
        plan = t.plan_merge(t.load_package(self.package))
        HomePage.objects.filter(pk=1).update(hero_heading='Concurrent edit')
        with self.assertRaisesMessage(CommandError, 'stale'):
            self.apply(plan)
        self.assertEqual(HomePage.objects.get(pk=1).hero_heading, 'Concurrent edit')

    def test_media_collision_never_overwrites_target(self):
        self.export()
        first = next(iter(t.media_references(t.state())))
        target = t.safe_path(self.media, first)
        target.write_bytes(b'new production file')
        with self.assertRaisesMessage(CommandError, 'collision'):
            t.load_package(self.package)
        self.assertEqual(target.read_bytes(), b'new production file')

    def test_path_traversal_rejected(self):
        for name in ('../secret', '/etc/passwd', 'C:/secret', 'a\\b', 'a/../b'):
            with self.assertRaises(CommandError):
                t.safe_path(self.media, name)

    def test_missing_file_aborts_export(self):
        HomePage.objects.filter(pk=1).update(hero_image='missing.webp')
        with self.assertRaisesMessage(CommandError, 'Referenced media missing'):
            self.export()
        self.assertFalse((self.package / 'content.json').exists())

    def test_missing_migrations_abort(self):
        with patch.object(t, 'schema', side_effect=CommandError('Pending migrations')):
            with self.assertRaisesMessage(CommandError, 'Pending migrations'):
                self.export()

    def test_production_writes_refuse_sqlite(self):
        with self.assertRaisesMessage(CommandError, 'require PostgreSQL'):
            t.apply_package(self.package, 'plan', 'backup', 'journal')
        with self.assertRaisesMessage(CommandError, 'require PostgreSQL'):
            t.postgres_backup(self.root / 'backup')

    def test_transaction_rolls_back_on_database_error(self):
        self.export()
        HomePage.objects.filter(pk=1).update(hero_heading='')
        plan = t.plan_merge(t.load_package(self.package))
        before = t.digest(t.state())
        execute = t.execute_operations
        def fail(ops):
            execute(ops)
            raise ValueError('Simulated failure')
        with patch.object(t, 'execute_operations', side_effect=fail):
            with self.assertRaises(ValueError):
                self.apply(plan)
        self.assertEqual(t.digest(t.state()), before)

    def test_journal_rollback_preserves_enquiries_and_files(self):
        self.export()
        HomePage.objects.filter(pk=1).update(hero_heading='')
        before = t.digest(t.state())
        plan = t.plan_merge(t.load_package(self.package))
        self.apply(plan)
        enquiry = Enquiry.objects.create(name='Live', email='live@example.org', message='Keep me')
        with patch.object(t, 'require_postgres'):
            t.rollback_journal(self.root / 'journal.json')
        self.assertEqual(t.digest(t.state()), before)
        self.assertTrue(Enquiry.objects.filter(pk=enquiry.pk).exists())

    def test_rollback_refuses_later_content_edits(self):
        self.export()
        plan = t.plan_merge(t.load_package(self.package))
        self.apply(plan)
        HomePage.objects.filter(pk=1).update(hero_text='Later content')
        with patch.object(t, 'require_postgres'):
            with self.assertRaisesMessage(CommandError, 'changed since merge'):
                t.rollback_journal(self.root / 'journal.json')

    def test_package_tampering_rejected(self):
        self.export()
        data = t.read_json(self.package / 'content.json')
        data['records']['homepage'][0]['hero_text'] = 'Changed'
        t.write_json(self.package / 'content.json', data)
        with self.assertRaisesMessage(CommandError, 'checksum'):
            t.load_package(self.package)

    def test_rollback_removes_only_imported_rows(self):
        category = TradeCategory.objects.first()
        self.export()
        category.translations.all().delete()
        category.delete()
        before = t.digest(t.state())
        plan = t.plan_merge(t.load_package(self.package))
        self.apply(plan)
        with patch.object(t, 'require_postgres'):
            t.rollback_journal(self.root / 'journal.json')
        self.assertEqual(t.digest(t.state()), before)

    def test_rollback_refuses_new_enquiry_dependency(self):
        category = TradeCategory.objects.first()
        pk = category.pk
        self.export()
        category.translations.all().delete()
        category.delete()
        plan = t.plan_merge(t.load_package(self.package))
        self.apply(plan)
        Enquiry.objects.create(name='Customer', email='live@example.org', message='Keep', category_id=pk)
        with patch.object(t, 'require_postgres'):
            with self.assertRaisesMessage(CommandError, 'New enquiries'):
                t.rollback_journal(self.root / 'journal.json')
        self.assertTrue(TradeCategory.objects.filter(pk=pk).exists())

    def test_backup_target_and_digest_checked(self):
        backup = self.root / 'backup'; backup.mkdir()
        (backup / 'database.dump').write_bytes(b'dump')
        from django.utils import timezone
        t.write_json(backup / 'backup.json', {'database':'other database', 'created_at':timezone.now().isoformat(), 'sha256':t.file_hash(backup/'database.dump')})
        with self.assertRaisesMessage(CommandError, 'does not match'):
            t.check_backup(backup)

    def test_expired_backup_rejected(self):
        backup = self.root / 'backup'; backup.mkdir()
        (backup / 'database.dump').write_bytes(b'dump')
        from django.utils import timezone
        from datetime import timedelta
        t.write_json(backup / 'backup.json', {'database':t.database_id(), 'created_at':(timezone.now()-timedelta(days=2)).isoformat(), 'sha256':t.file_hash(backup/'database.dump')})
        with self.assertRaisesMessage(CommandError, 'fresh PostgreSQL backup'):
            t.check_backup(backup)

    def test_failed_pg_dump_has_no_backup_receipt(self):
        from subprocess import CompletedProcess
        with patch.object(t, 'require_postgres'), patch.object(t, 'pg_environment', return_value={}), patch.object(t.subprocess, 'run', return_value=CompletedProcess([], 1)):
            with self.assertRaisesMessage(CommandError, 'backup validation failed'):
                t.postgres_backup(self.root/'backup')
        self.assertFalse((self.root/'backup/backup.json').exists())


    def migration_fixture(self):
        base = self.root / 'schema-fixture'
        migrations = base / 'trade' / 'migrations'
        migrations.mkdir(parents=True)
        contents = {
            '0014_example.py': '# Unicode: Magyar őű Українська\nVALUE = 1\n'.encode('utf-8'),
            '0015_example.json': '{\n  "text": "العربية", "literal": "\\r\\n", "value": 1\n}\n'.encode('utf-8'),
        }
        for name, content in contents.items():
            (migrations / name).write_bytes(content)
        return base, migrations, contents

    def test_schema_and_package_accept_only_line_ending_differences(self):
        base, migrations, contents = self.migration_fixture()
        with override_settings(BASE_DIR=base):
            expected = t.schema()
            self.assertEqual(expected, {name: t.file_hash(migrations / name) for name in contents})
            data = self.export()
            for ending in (b'\r\n', b'\r', b'\n'):
                with self.subTest(ending=ending):
                    for name, content in contents.items():
                        (migrations / name).write_bytes(content.replace(b'\n', ending))
                    self.assertEqual(t.schema(), expected)
                    self.assertEqual(t.load_package(self.package), data)
            for name, content in contents.items():
                endings = (b'\r\n', b'\r', b'\n')
                mixed = b''.join(line[:-1] + endings[i % 3] for i, line in enumerate(content.splitlines(keepends=True)))
                (migrations / name).write_bytes(mixed)
            self.assertEqual(t.schema(), expected)

    def test_real_migration_changes_still_reject_package(self):
        base, migrations, contents = self.migration_fixture()
        with override_settings(BASE_DIR=base):
            self.export()
            for name, content in contents.items():
                # Neither actual content, whitespace, nor a removed final newline is ignored.
                for changed in (content.replace(b'1', b'2'), content + b' ', content[:-1]):
                    with self.subTest(name=name, changed=changed):
                        (migrations / name).write_bytes(changed.replace(b'\n', b'\r\n'))
                        with self.assertRaisesMessage(CommandError, 'Trade migration files differ'):
                            t.load_package(self.package)
                        (migrations / name).write_bytes(content)

    def test_migration_file_set_changes_still_reject_package(self):
        base, migrations, contents = self.migration_fixture()
        with override_settings(BASE_DIR=base):
            self.export()
            first = next(iter(contents))
            (migrations / first).unlink()
            with self.assertRaisesMessage(CommandError, 'Trade migration files differ'):
                t.load_package(self.package)
            (migrations / first).write_bytes(contents[first])
            (migrations / '0016_extra.py').write_bytes(b'# new migration\n')
            with self.assertRaisesMessage(CommandError, 'Trade migration files differ'):
                t.load_package(self.package)

    def test_raw_binary_hashes_remain_line_ending_sensitive(self):
        path = self.root / 'binary.webp'
        path.write_bytes(b'image\ndata\n')
        original = t.file_hash(path)
        path.write_bytes(b'image\r\ndata\r\n')
        self.assertNotEqual(t.file_hash(path), original)
