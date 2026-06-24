"""
Benchmark service layer.

This is the single place peer-group distributions are produced. Resolution
order for any filter combination:

    in-process cache  ->  materialized BenchmarkAggregate row  ->  compute

Computing means scanning the matching projects once and summarizing each
metric. The result is written back to the table and the cache, so the common
case (repeat reads of popular peer groups) never touches project rows.
"""

from __future__ import annotations

from django.core.cache import cache
from django.db.models import QuerySet

from . import stats
from .models import BENCHMARK_METRICS, BenchmarkAggregate, Project

# Filter dimensions that define a peer group, in canonical order.
PEER_DIMENSIONS = ("sector", "region", "project_type", "size_band")

CACHE_TTL = 60 * 30  # 30 minutes


def make_signature(filters: dict) -> str:
    """Order-independent, canonical key for a filter combination.

    Empty/None values are dropped, so {"sector": "mining"} and
    {"sector": "mining", "region": None} produce the same signature.
    """
    parts = [
        f"{dim}={filters[dim]}"
        for dim in PEER_DIMENSIONS
        if filters.get(dim)
    ]
    return "all" if not parts else "|".join(parts)


def filter_projects(queryset: QuerySet, filters: dict) -> QuerySet:
    """Apply the peer-group filters that are present to a Project queryset."""
    applied = {
        dim: filters[dim] for dim in PEER_DIMENSIONS if filters.get(dim)
    }
    return queryset.filter(**applied) if applied else queryset


def _compute(queryset: QuerySet, filters: dict) -> dict:
    """Scan the peer group once and summarize every benchmarked metric."""
    rows = list(queryset)
    distributions: dict[str, dict] = {}
    for metric in BENCHMARK_METRICS:
        values = [getattr(p, metric) for p in rows]
        summary = stats.summarize(values)
        if summary is not None:
            distributions[metric] = summary.as_dict()
    return {"n": len(rows), "distributions": distributions}


def get_benchmark(filters: dict, *, base_queryset: QuerySet | None = None) -> dict:
    """Return materialized distributions for a peer group.

    `base_queryset` lets callers pass a role-scoped queryset (e.g. excluding
    confidential projects); the signature is shared but the cache key is
    namespaced by the scope so scoped and unscoped reads don't collide.
    """
    base = base_queryset if base_queryset is not None else Project.objects.all()
    signature = make_signature(filters)
    scope = "all" if base_queryset is None else "scoped"
    cache_key = f"benchmark:{scope}:{signature}"

    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    # Scoped reads are computed on the fly (cheap, role-dependent) and cached,
    # but not persisted to the shared aggregate table.
    if base_queryset is not None:
        payload = _compute(filter_projects(base, filters), filters)
        payload["signature"] = signature
        cache.set(cache_key, payload, CACHE_TTL)
        return payload

    agg = BenchmarkAggregate.objects.filter(signature=signature).first()
    if agg is None:
        computed = _compute(filter_projects(base, filters), filters)
        agg = BenchmarkAggregate.objects.create(
            signature=signature,
            filters={d: filters[d] for d in PEER_DIMENSIONS if filters.get(d)},
            n=computed["n"],
            distributions=computed["distributions"],
        )

    payload = {
        "signature": agg.signature,
        "filters": agg.filters,
        "n": agg.n,
        "distributions": agg.distributions,
    }
    cache.set(cache_key, payload, CACHE_TTL)
    return payload


def rebuild_all() -> int:
    """Drop and rematerialize the 'all projects' aggregate plus every
    single-sector and single-type group. Returns the number of rows written.

    Called after seeding. We don't enumerate the full cross-product (it grows
    combinatorially and most cells are empty); single-dimension groups cover
    the dashboard's default views, and any other combination is computed and
    cached lazily on first request.
    """
    from .models import ProjectType, Sector

    cache.clear()
    BenchmarkAggregate.objects.all().delete()

    combos: list[dict] = [{}]
    combos += [{"sector": s.value} for s in Sector]
    combos += [{"project_type": t.value} for t in ProjectType]

    count = 0
    for filters in combos:
        get_benchmark(filters)
        count += 1
    return count


def project_benchmark(project: Project, *, base_queryset: QuerySet | None = None) -> dict:
    """Everything the dashboard needs for one project: its metrics, the peer
    group it's measured against, percentile ranks, and cost gaps vs P50/P80.
    """
    filters = {
        "sector": project.sector,
        "region": project.region,
        "project_type": project.project_type,
        "size_band": project.size_band,
    }

    base = base_queryset if base_queryset is not None else Project.objects.all()
    peer_qs = filter_projects(base, filters)

    # Fall back to a broader peer group when an exact match is too thin to
    # benchmark against (small-slice problem). Widen by dropping dimensions.
    fallbacks = [
        filters,
        {"sector": project.sector, "project_type": project.project_type},
        {"sector": project.sector},
        {},
    ]
    chosen = filters
    for candidate in fallbacks:
        if filter_projects(base, candidate).count() >= 12:
            chosen = candidate
            break
    else:
        chosen = {}

    bench = get_benchmark(chosen, base_queryset=base_queryset)
    peer_rows = list(filter_projects(base, chosen))

    metrics: dict[str, dict] = {}
    for metric in BENCHMARK_METRICS:
        value = getattr(project, metric)
        dist = bench["distributions"].get(metric)
        peer_values = [getattr(p, metric) for p in peer_rows]
        metrics[metric] = {
            "value": round(value, 4),
            "percentile_rank": round(stats.percentile_rank(peer_values, value), 1),
            "gap_vs_p50": _round_or_none(
                stats.cost_gap(value, dist["p50"]) if dist else None
            ),
            "gap_vs_p80": _round_or_none(
                stats.cost_gap(value, dist["p80"]) if dist else None
            ),
            "distribution": dist,
        }

    fel = project.fel
    return {
        "project_id": project.id,
        "peer_group": {
            "filters": chosen,
            "n": len(peer_rows),
            "is_exact": chosen == filters,
        },
        "metrics": metrics,
        "fel": fel.as_dict(),
    }


def _round_or_none(value):
    return None if value is None else round(value, 4)
