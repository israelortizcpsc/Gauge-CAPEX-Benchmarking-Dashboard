"""
Pure statistics for CAPEX benchmarking.

This module is deliberately framework-free: no Django, no DRF, no models. All
benchmark math (percentiles, ranks, cost gaps, FEL readiness) lives here so it
can be unit-tested in isolation and reused on any client without drift. The API
layer is the *only* place these numbers are computed, which keeps a single
source of truth — every client that hits the API gets identical figures.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict


# Percentiles we materialize for every peer-group distribution. P50 is the
# median "norm"; P80 is the competitive target used throughout the dashboard.
STANDARD_PERCENTILES = (10, 25, 50, 75, 80, 90)


def percentile(values: list[float], p: float) -> float:
    """Linear-interpolated percentile (matches numpy's default 'linear' method).

    `p` is in [0, 100]. Raises ValueError on empty input so callers must decide
    how to handle empty peer groups rather than silently getting a 0.
    """
    if not values:
        raise ValueError("percentile() requires at least one value")
    if not 0 <= p <= 100:
        raise ValueError("percentile p must be between 0 and 100")

    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])

    # Rank position on a 0..n-1 scale, then interpolate between neighbours.
    rank = (p / 100.0) * (len(ordered) - 1)
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    frac = rank - low
    return float(ordered[low] + (ordered[high] - ordered[low]) * frac)


def percentile_rank(values: list[float], x: float) -> float:
    """Where `x` sits within `values`, as a 0..100 percentile.

    Uses the midpoint ("mean") convention: ties count as half, so a value equal
    to every other yields 50, not 0 or 100. Returns 50.0 for an empty set
    (no information => assume the median).
    """
    if not values:
        return 50.0
    below = sum(1 for v in values if v < x)
    equal = sum(1 for v in values if v == x)
    return 100.0 * (below + 0.5 * equal) / len(values)


@dataclass(frozen=True)
class Distribution:
    """Materialized summary of one metric across one peer group."""

    n: int
    mean: float
    p10: float
    p25: float
    p50: float
    p75: float
    p80: float
    p90: float

    def as_dict(self) -> dict:
        return asdict(self)


def summarize(values: list[float]) -> Distribution | None:
    """Compute a Distribution, or None when the peer group is empty."""
    if not values:
        return None
    pcts = {f"p{p}": round(percentile(values, p), 4) for p in STANDARD_PERCENTILES}
    return Distribution(
        n=len(values),
        mean=round(sum(values) / len(values), 4),
        **pcts,
    )


def cost_gap(value: float, reference: float) -> float | None:
    """Fractional gap of `value` above a reference norm (e.g. peer P50).

    +0.15 means 15% above the norm (worse, for a cost metric); negative means
    below it (better). Returns None when the reference is zero/undefined.
    """
    if not reference:
        return None
    return (value - reference) / reference


# --- FEL readiness ----------------------------------------------------------
#
# Front-End Loading (FEL) measures how well a project was defined before it was
# sanctioned. We score three sub-dimensions on a 1 (concept) .. 5 (fully
# defined) scale and roll them into a 0..100 readiness index. The weights
# reflect what most drives outcome predictability in sustaining capital work.

FEL_WEIGHTS = {
    "scope": 0.40,        # Is the work scope fixed and understood?
    "engineering": 0.35,  # Engineering / design maturity at sanction.
    "execution": 0.25,    # Execution & contracting plan readiness.
}

FEL_INPUT_MIN, FEL_INPUT_MAX = 1, 5


@dataclass(frozen=True)
class FelReadiness:
    score: int          # 0..100
    band: str           # human-readable readiness band
    components: dict     # per-dimension 0..100 contribution

    def as_dict(self) -> dict:
        return asdict(self)


def fel_band(score: float) -> str:
    """Map a 0..100 readiness score onto IPA-style definition bands."""
    if score >= 80:
        return "Best Practical"
    if score >= 60:
        return "Good"
    if score >= 40:
        return "Fair"
    return "Screening"


def fel_readiness(scope: int, engineering: int, execution: int) -> FelReadiness:
    """Roll three 1..5 sub-scores into a weighted 0..100 readiness index."""
    raw = {"scope": scope, "engineering": engineering, "execution": execution}
    for name, val in raw.items():
        if not FEL_INPUT_MIN <= val <= FEL_INPUT_MAX:
            raise ValueError(
                f"FEL '{name}' must be in [{FEL_INPUT_MIN}, {FEL_INPUT_MAX}], got {val}"
            )

    # Normalize each 1..5 input to 0..100 (1 -> 0, 5 -> 100).
    span = FEL_INPUT_MAX - FEL_INPUT_MIN
    components = {
        name: round(100.0 * (val - FEL_INPUT_MIN) / span, 1)
        for name, val in raw.items()
    }
    score = sum(components[name] * FEL_WEIGHTS[name] for name in raw)
    rounded = int(round(score))
    return FelReadiness(score=rounded, band=fel_band(rounded), components=components)
