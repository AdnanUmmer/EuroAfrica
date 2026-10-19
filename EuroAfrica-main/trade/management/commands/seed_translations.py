from importlib import import_module
from types import SimpleNamespace
from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import connections, transaction


class Command(BaseCommand):
    help = 'Install missing reviewed translations and expand unchanged starter descriptions; preserve owner edits.'

    def add_arguments(self, parser):
        parser.add_argument('--database', default='default')

    def handle(self, *args, **options):
        alias = options['database']
        with transaction.atomic(using=alias):
            import_module('trade.migrations.0015_editorial_translations').install(apps, SimpleNamespace(connection=connections[alias]))
        self.stdout.write(self.style.SUCCESS('Reviewed translations installed; existing translations and custom source text preserved.'))
