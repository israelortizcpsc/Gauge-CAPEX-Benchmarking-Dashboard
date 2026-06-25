"""
Export a frozen snapshot of the public API to static JSON.

GitHub Pages can't run Django, so the hosted demo serves these files instead of
a live backend. Crucially, the numbers are still the *real* server-computed
ones — this command drives the actual API endpoints via Django's test client and
dumps their responses verbatim, so the snapshot can't drift from the live math.

The demo UI filters by sector and project type, so we export every combination
of those two dimensions (1 + 5 + 5 + 25 = 36 peer groups), plus a per-project
benchmark for every project that appears in those lists.

    python manage.py export_static
    python manage.py export_static --out ../frontend/public/demo-api
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from django.core.management.base import BaseCommand
from django.test import Client
from django.urls import reverse

from benchmarks.models import ProjectType, Sector


def sig_filename(filters: dict) -> str:
    """Canonical filename for a peer group — must match the TS client's
    sigFile(). Dimensions in fixed order, `dim-value`, joined by `__`."""
    order = ("sector", "region", "project_type", "size_band")
    parts = [f"{d}-{filters[d]}" for d in order if filters.get(d)]
    return "all" if not parts else "__".join(parts)


class Command(BaseCommand):
    help = "Export a static JSON snapshot of the public API for the Pages demo."

    def add_arguments(self, parser):
        parser.add_argument("--out", default="../frontend/public/demo-api")

    def handle(self, *args, **options):
        # Bulk export trips the API's anon rate throttle; disable it for this run
        # so the snapshot contains real data, not "Too Many Requests" bodies.
        # DRF reads throttle_classes off the view class (captured at import), so
        # override_settings won't reach it — patch the class attribute directly.
        from rest_framework.views import APIView

        original = APIView.throttle_classes
        APIView.throttle_classes = []
        try:
            self._export(options)
        finally:
            APIView.throttle_classes = original

    def _export(self, options):
        out = Path(options["out"]).resolve()
        if out.exists():
            shutil.rmtree(out)
        for sub in ("portfolio", "benchmarks", "projects", "project-benchmark"):
            (out / sub).mkdir(parents=True, exist_ok=True)

        client = Client()

        def dump(path: Path, data) -> None:
            path.write_text(json.dumps(data, separators=(",", ":")))

        # meta
        dump(out / "meta.json", client.get(reverse("meta")).json())

        # Sector × project-type combinations the demo UI can request.
        combos: list[dict] = [{}]
        combos += [{"sector": s.value} for s in Sector]
        combos += [{"project_type": t.value} for t in ProjectType]
        combos += [
            {"sector": s.value, "project_type": t.value}
            for s in Sector
            for t in ProjectType
        ]

        project_ids: set[int] = set()
        for filters in combos:
            name = sig_filename(filters)
            qs = {**filters, "ordering": "name"}

            dump(out / "portfolio" / f"{name}.json",
                 client.get(reverse("portfolio"), filters).json())
            dump(out / "benchmarks" / f"{name}.json",
                 client.get(reverse("benchmarks"), filters).json())

            projects = client.get(reverse("project-list"), qs).json()
            dump(out / "projects" / f"{name}.json", projects)
            for row in projects.get("results", []):
                project_ids.add(row["id"])

        # Per-project benchmark payloads for every project the picker can show.
        for pid in sorted(project_ids):
            url = reverse("project-benchmark", args=[pid])
            dump(out / "project-benchmark" / f"{pid}.json", client.get(url).json())

        total = 1 + 4 * len(combos) - 3 * len(combos) + len(project_ids)
        self.stdout.write(self.style.SUCCESS(
            f"Exported snapshot to {out}: meta + {len(combos)} peer groups "
            f"+ {len(project_ids)} project benchmarks."
        ))
