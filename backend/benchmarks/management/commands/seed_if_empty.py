"""Seed only when the database has no projects.

Used on container boot so the live demo self-populates on first deploy but
isn't reseeded (and thus reshuffled) on every restart. Honors SEED_ON_START=0
to skip entirely.
"""

import os

from django.core.management import call_command
from django.core.management.base import BaseCommand

from benchmarks.models import Project


class Command(BaseCommand):
    help = "Seed synthetic projects only if none exist yet."

    def handle(self, *args, **options):
        if os.environ.get("SEED_ON_START", "1") == "0":
            self.stdout.write("SEED_ON_START=0, skipping seed.")
            return
        if Project.objects.exists():
            self.stdout.write(f"{Project.objects.count()} projects already present; skipping.")
            return
        self.stdout.write("Empty database, seeding...")
        call_command("seed", count=int(os.environ.get("SEED_COUNT", "2000")))
