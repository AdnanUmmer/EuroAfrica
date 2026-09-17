from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from trade.models import SubmissionWindow

class Command(BaseCommand):
    help = 'Delete expired anti-spam counters older than two hours; schedule hourly.'
    def handle(self, **options):
        count, _ = SubmissionWindow.objects.filter(created_at__lt=timezone.now() - timedelta(hours=2)).delete()
        self.stdout.write(f'Removed {count} expired counters.')
