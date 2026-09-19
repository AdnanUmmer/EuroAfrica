from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from trade.models import SubmissionWindow, SubmissionReceipt

class Command(BaseCommand):
    help = 'Delete expired anti-spam counters older than two hours; schedule hourly.'
    def handle(self, **options):
        count, _ = SubmissionWindow.objects.filter(created_at__lt=timezone.now() - timedelta(hours=2)).delete()
        receipts, _ = SubmissionReceipt.objects.filter(expires_at__lte=timezone.now()).delete()
        self.stdout.write(f'Removed {count} expired counters and {receipts} expired receipts.')
