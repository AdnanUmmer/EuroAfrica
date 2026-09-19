from io import StringIO
import json
from unittest.mock import patch
from django.core.management import call_command
from django.test import TestCase, override_settings
from .models import TradeCategory, TradeDirection, CategorySection, HomePage, SiteSettings


@override_settings(DEBUG=True, INDEXABLE=True, STAGING=False, SECURE_SSL_REDIRECT=False,
                   SITE_URL='https://www.euroafrica.example', ALLOWED_HOSTS=['testserver','www.euroafrica.example'])
class SEOReadinessTests(TestCase):
    @classmethod
    def setUpTestData(cls):call_command('seed_content',stdout=StringIO())

    def test_rendered_audit_all_pages_and_unique_content(self):
        output=StringIO();call_command('audit_seo',simulate_indexing=True,json=True,stdout=output)
        report=json.loads(output.getvalue());self.assertEqual(report['errors'],[])
        self.assertEqual(len(report['pages']),18);self.assertEqual(report['sitemap_urls'],18)
        self.assertEqual(CategorySection.objects.count(),13)
        self.assertEqual(len(set(CategorySection.objects.values_list('text',flat=True))),13)

    def test_direction_context_sharing_defaults_and_admin_overrides(self):
        obj=TradeCategory.objects.first()
        response=self.client.get(obj.get_absolute_url())
        self.assertContains(response,f'{obj.direction.title} | EuroAfrica</title>')
        self.assertContains(response,'name="twitter:card"')
        self.assertContains(response,'property="og:image"')
        obj.seo_title='An owner title';obj.meta_description='An owner description';obj.save()
        response=self.client.get(obj.get_absolute_url())
        self.assertContains(response,'<title>An owner title</title>')
        self.assertContains(response,'content="An owner description"')

    def test_query_variants_canonicalize_and_no_false_schema(self):
        response=self.client.get('/?utm_source=test')
        self.assertContains(response,'rel="canonical" href="https://www.euroafrica.example/"')
        self.assertNotContains(response,'"@type": "Product"')
        self.assertNotContains(response,'aggregateRating')

    def test_disabled_indexing_retained_and_no_orphan_categories(self):
        with override_settings(INDEXABLE=False):
            self.assertIn('noindex',self.client.get('/')['X-Robots-Tag'])
            self.assertNotContains(self.client.get('/sitemap.xml'),'<loc>')
        for category in TradeCategory.objects.select_related('direction'):
            self.assertContains(self.client.get(category.direction.get_absolute_url()),category.get_absolute_url())

    def test_seed_does_not_recreate_removed_or_edited_guidance(self):
        category=TradeCategory.objects.first();category.overview='Owner copy';category.save()
        CategorySection.objects.filter(category=category).delete()
        other=CategorySection.objects.first();other.text='Owner guidance';other.save()
        call_command('seed_content',stdout=StringIO())
        category.refresh_from_db();other.refresh_from_db()
        self.assertEqual(category.overview,'Owner copy');self.assertEqual(other.text,'Owner guidance')
        self.assertFalse(category.sections.exists())

    def test_migration_preserves_owner_copy_and_enriches_only_untouched(self):
        import importlib
        from django.apps import apps
        from django.db import connection
        migration=importlib.import_module('trade.migrations.0009_category_guidance')
        first,second=list(TradeCategory.objects.all()[:2])
        CategorySection.objects.filter(category__in=[first,second]).delete()
        second.overview='Owner revision';second.save()
        from types import SimpleNamespace
        editor=SimpleNamespace(connection=connection)
        migration.enrich(apps,editor)
        self.assertTrue(first.sections.exists());self.assertFalse(second.sections.exists())
        migration_count=CategorySection.objects.count()
        migration.enrich(apps,editor)
        self.assertEqual(CategorySection.objects.count(),migration_count)

    def test_sitemap_lastmod_reflects_parent_navigation_change(self):
        from datetime import timedelta
        from django.utils import timezone
        from xml.etree import ElementTree
        category=TradeCategory.objects.first()
        newer=timezone.now()+timedelta(seconds=5)
        TradeDirection.objects.filter(pk=category.direction_id).update(updated_at=newer)
        sitemap=ElementTree.fromstring(self.client.get('/sitemap.xml').content)
        ns={'s':'http://www.sitemaps.org/schemas/sitemap/0.9'}
        record=next(n for n in sitemap if n.find('s:loc',ns).text.endswith(category.get_absolute_url()))
        self.assertEqual(record.find('s:lastmod',ns).text,newer.isoformat())
