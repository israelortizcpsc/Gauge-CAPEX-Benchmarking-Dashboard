"""
Seed the database with synthetic sustaining-capital projects.

The data is generated, not real. It is shaped to behave like real portfolios so
benchmarks are meaningful: better front-end loading (higher FEL) correlates
with lower cost growth and schedule slip, sectors have different cost
intensities, and there is realistic noise. A fixed seed makes runs
reproducible.

    python manage.py seed                # 2000 projects (default)
    python manage.py seed --count 500    # custom size
    python manage.py seed --clear        # wipe existing first
"""

from __future__ import annotations

import random

from django.core.management.base import BaseCommand
from django.db import transaction

from benchmarks import services
from benchmarks.models import (
    ProjectType,
    Region,
    Sector,
    Project,
)

# Per-sector baseline capex intensity ($M per capacity unit) and capacity
# range. These give the sectors distinguishable cost profiles.
SECTOR_PROFILE = {
    Sector.MINING: {"intensity": 0.45, "cap_range": (200, 4000), "unit": "kt/yr"},
    Sector.OIL_GAS: {"intensity": 0.80, "cap_range": (50, 1500), "unit": "kbbl/d"},
    Sector.CHEMICALS: {"intensity": 0.60, "cap_range": (100, 2500), "unit": "kt/yr"},
    Sector.POWER: {"intensity": 1.10, "cap_range": (50, 1200), "unit": "MW"},
    Sector.PULP_PAPER: {"intensity": 0.35, "cap_range": (150, 1800), "unit": "kt/yr"},
}

OPERATOR_PREFIXES = [
    "Northgate", "Meridian", "Cascade", "Atlas", "Granite", "Summit",
    "Cardinal", "Pioneer", "Keystone", "Vanguard", "Harbor", "Sterling",
]
OPERATOR_SUFFIXES = ["Resources", "Energy", "Industries", "Materials", "Operations"]

ASSET_NOUNS = {
    ProjectType.ASSET_REPLACEMENT: ["Mill", "Conveyor", "Furnace", "Compressor", "Boiler"],
    ProjectType.RELIABILITY: ["Pump Station", "Turbine", "Heat Exchanger", "Reactor"],
    ProjectType.COMPLIANCE: ["Scrubber", "Containment", "Tailings Upgrade", "Flare"],
    ProjectType.DEBOTTLENECK: ["Throughput", "Circuit", "Line", "Train"],
    ProjectType.INFRASTRUCTURE: ["Substation", "Pipeline", "Access Road", "Water System"],
}


def _fel_inputs(rng: random.Random) -> tuple[int, int, int]:
    """Three correlated 1..5 sub-scores around a project's overall maturity."""
    base = rng.triangular(1.5, 5.0, 3.4)
    return tuple(
        max(1, min(5, round(base + rng.uniform(-0.9, 0.9)))) for _ in range(3)
    )


class Command(BaseCommand):
    help = "Generate synthetic sustaining-capital projects and materialize benchmarks."

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=2000)
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument("--clear", action="store_true")

    def handle(self, *args, **options):
        rng = random.Random(options["seed"])
        count = options["count"]

        if options["clear"]:
            deleted, _ = Project.objects.all().delete()
            self.stdout.write(f"Cleared {deleted} existing rows.")

        sectors = list(Sector)
        regions = list(Region)
        types = list(ProjectType)

        projects: list[Project] = []
        for i in range(count):
            sector = rng.choices(sectors, weights=[30, 22, 20, 16, 12])[0]
            region = rng.choice(regions)
            ptype = rng.choice(types)
            profile = SECTOR_PROFILE[sector]

            capacity = round(rng.uniform(*profile["cap_range"]), 1)

            # Sanctioned budget = intensity * capacity, scaled by project type,
            # with lognormal-ish noise. Compliance work tends to be smaller.
            type_scale = {
                ProjectType.ASSET_REPLACEMENT: 1.0,
                ProjectType.RELIABILITY: 0.7,
                ProjectType.COMPLIANCE: 0.55,
                ProjectType.DEBOTTLENECK: 0.85,
                ProjectType.INFRASTRUCTURE: 0.95,
            }[ptype]
            base_cost = profile["intensity"] * capacity * type_scale
            capex_estimate = round(max(3.0, base_cost * rng.lognormvariate(0, 0.35)), 1)

            scope, eng, exe = _fel_inputs(rng)
            fel_mean = (scope + eng + exe) / 3.0  # 1..5

            # Better FEL -> tighter, lower cost growth. Map FEL 1->~+22%,
            # 5->~-2% expected, with noise. Same idea for schedule.
            cost_growth_mean = 0.27 - 0.06 * fel_mean
            cost_growth = rng.gauss(cost_growth_mean, 0.07)
            cost_growth = max(-0.15, cost_growth)
            capex_actual = round(capex_estimate * (1 + cost_growth), 1)

            schedule_planned = round(rng.uniform(6, 42), 1)
            slip_mean = 0.22 - 0.05 * fel_mean
            slip = max(-0.12, rng.gauss(slip_mean, 0.06))
            schedule_actual = round(schedule_planned * (1 + slip), 1)

            operator = (
                f"{rng.choice(OPERATOR_PREFIXES)} {rng.choice(OPERATOR_SUFFIXES)}"
            )
            noun = rng.choice(ASSET_NOUNS[ptype])
            name = f"{noun} {ptype.label.split()[0]} {i + 1:04d}"

            projects.append(
                Project(
                    name=name,
                    operator=operator,
                    sector=sector,
                    region=region,
                    project_type=ptype,
                    sanction_year=rng.randint(2014, 2024),
                    capacity=capacity,
                    capacity_unit=profile["unit"],
                    capex_estimate=capex_estimate,
                    capex_actual=capex_actual,
                    schedule_months_planned=schedule_planned,
                    schedule_months_actual=schedule_actual,
                    fel_scope=scope,
                    fel_engineering=eng,
                    fel_execution=exe,
                    # ~8% of projects flagged confidential to exercise scoping.
                    is_confidential=rng.random() < 0.08,
                    size_band="",  # set in save(); bulk_create bypasses save()
                )
            )

        # bulk_create skips Project.save(), so set size_band explicitly.
        from benchmarks.models import size_band_for

        for p in projects:
            p.size_band = size_band_for(p.capex_estimate)

        with transaction.atomic():
            Project.objects.bulk_create(projects, batch_size=500)

        self.stdout.write(self.style.SUCCESS(f"Created {len(projects)} projects."))

        written = services.rebuild_all()
        self.stdout.write(
            self.style.SUCCESS(f"Materialized {written} benchmark aggregates.")
        )
