"""
Domain models for Gauge.

`Project` is one sustaining-capital project. `BenchmarkAggregate` is the
materialized, filter-keyed cache of peer-group distributions — precomputing it
keeps reads fast as the project count grows.

All figures are SYNTHETIC. See the README: no real client data is used.
"""

from __future__ import annotations

from django.db import models

from . import stats


class Sector(models.TextChoices):
    MINING = "mining", "Mining & Metals"
    OIL_GAS = "oil_gas", "Oil & Gas"
    CHEMICALS = "chemicals", "Chemicals"
    POWER = "power", "Power & Utilities"
    PULP_PAPER = "pulp_paper", "Pulp & Paper"


class Region(models.TextChoices):
    NORTH_AMERICA = "north_america", "North America"
    SOUTH_AMERICA = "south_america", "South America"
    EUROPE = "europe", "Europe"
    MIDDLE_EAST = "middle_east", "Middle East & Africa"
    ASIA_PACIFIC = "asia_pacific", "Asia Pacific"


class ProjectType(models.TextChoices):
    """Sustaining-capital work categories (not greenfield expansion)."""

    ASSET_REPLACEMENT = "asset_replacement", "Asset Replacement"
    RELIABILITY = "reliability", "Reliability & Integrity"
    COMPLIANCE = "compliance", "EH&S / Compliance"
    DEBOTTLENECK = "debottleneck", "Debottleneck"
    INFRASTRUCTURE = "infrastructure", "Infrastructure"


# Size bands by sanctioned capex (USD millions). Used as a peer-group
# dimension so a $10M reliability job isn't benchmarked against a $400M one.
SIZE_BANDS = (
    ("small", "Small (< $25M)", 0, 25),
    ("medium", "Medium ($25M-$100M)", 25, 100),
    ("large", "Large ($100M-$500M)", 100, 500),
    ("mega", "Mega (> $500M)", 500, float("inf")),
)


def size_band_for(capex_estimate: float) -> str:
    for key, _label, low, high in SIZE_BANDS:
        if low <= capex_estimate < high:
            return key
    return SIZE_BANDS[-1][0]


class Project(models.Model):
    name = models.CharField(max_length=160)
    operator = models.CharField(max_length=120, help_text="Synthetic owner/operator name")

    sector = models.CharField(max_length=20, choices=Sector.choices)
    region = models.CharField(max_length=20, choices=Region.choices)
    project_type = models.CharField(max_length=24, choices=ProjectType.choices)
    sanction_year = models.PositiveIntegerField()

    # Physical size - used to normalize cost into an intensity ($ per unit).
    capacity = models.FloatField(help_text="Nameplate capacity / throughput")
    capacity_unit = models.CharField(max_length=24, default="kt/yr")

    # Cost, USD millions.
    capex_estimate = models.FloatField(help_text="Sanctioned budget, USD millions")
    capex_actual = models.FloatField(help_text="Actual at completion, USD millions")

    # Schedule, months.
    schedule_months_planned = models.FloatField()
    schedule_months_actual = models.FloatField()

    # FEL sub-scores at sanction, each 1 (concept) .. 5 (fully defined).
    fel_scope = models.PositiveSmallIntegerField()
    fel_engineering = models.PositiveSmallIntegerField()
    fel_execution = models.PositiveSmallIntegerField()

    # Read-scoping flag: confidential projects are only visible to staff.
    is_confidential = models.BooleanField(default=False)

    # Denormalized for cheap filtering; kept in sync on save().
    size_band = models.CharField(max_length=10, editable=False, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["sector", "region", "project_type"]),
            models.Index(fields=["size_band"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_sector_display()})"

    def save(self, *args, **kwargs):
        self.size_band = size_band_for(self.capex_estimate)
        super().save(*args, **kwargs)

    # --- Derived benchmark metrics (computed, never stored as truth) --------

    @property
    def capex_intensity(self) -> float:
        """Actual cost per unit of capacity (USD M per capacity unit)."""
        return self.capex_actual / self.capacity if self.capacity else 0.0

    @property
    def cost_growth(self) -> float:
        """Actual vs sanctioned budget; 0.10 = 10% overrun."""
        if not self.capex_estimate:
            return 0.0
        return (self.capex_actual - self.capex_estimate) / self.capex_estimate

    @property
    def schedule_slip(self) -> float:
        """Actual vs planned duration; 0.10 = 10% late."""
        if not self.schedule_months_planned:
            return 0.0
        return (
            self.schedule_months_actual - self.schedule_months_planned
        ) / self.schedule_months_planned

    @property
    def fel(self) -> stats.FelReadiness:
        return stats.fel_readiness(
            self.fel_scope, self.fel_engineering, self.fel_execution
        )


# Metrics we benchmark. Keys map to Project properties above; the API and the
# aggregate cache both iterate this list so adding a metric is one line.
BENCHMARK_METRICS = ("capex_intensity", "cost_growth", "schedule_slip")


class BenchmarkAggregate(models.Model):
    """Materialized peer-group distributions, keyed by a filter signature.

    One row per distinct filter combination. `signature` is a canonical,
    order-independent encoding of the filters so the same peer group always
    resolves to the same row (and the same cache key).
    """

    signature = models.CharField(max_length=255, unique=True, db_index=True)
    filters = models.JSONField(default=dict)
    n = models.PositiveIntegerField()
    distributions = models.JSONField(
        default=dict, help_text="metric -> {n, mean, p10..p90}"
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.signature} (n={self.n})"
