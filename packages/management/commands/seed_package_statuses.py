from django.core.management.base import BaseCommand
from packages.models import PackageStatus

class Command(BaseCommand):
    help = "Seed initial package statuses"

    def handle(self, *args, **kwargs):
        statuses = ['Pending', 'Sent', 'Received','Delivered', 'Canceled']
        for name in statuses:
            obj, created = PackageStatus.objects.get_or_create(name=name)
            status = "Created" if created else "Exists"
            self.stdout.write(self.style.SUCCESS(f"[{status}] PackageStatus: {obj.name}"))
