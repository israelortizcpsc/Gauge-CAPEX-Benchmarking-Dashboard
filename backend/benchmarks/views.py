"""
API views.

Read-only by design - this dashboard never mutates benchmark data over the
wire. Reads are role-scoped: anonymous/non-staff callers never see projects
flagged confidential. Filter inputs are validated by serializers before they
reach the service layer.
"""

from __future__ import annotations

from rest_framework import viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from . import services, stats
from .models import (
    ProjectType,
    Region,
    Sector,
    SIZE_BANDS,
    Project,
)
from .serializers import (
    BenchmarkQuerySerializer,
    ProjectDetailSerializer,
    ProjectListSerializer,
)


def scoped_projects(request):
    """Role-scoped base queryset: confidential projects only for staff."""
    qs = Project.objects.all()
    if not (request.user and request.user.is_staff):
        qs = qs.filter(is_confidential=False)
    return qs


def _scope_for(request):
    """The base_queryset to hand the service layer, or None for the full set
    (None lets the service use the persisted aggregate table)."""
    if request.user and request.user.is_staff:
        return None
    return scoped_projects(request)


class ProjectViewSet(viewsets.ReadOnlyModelViewSet):
    """`/api/projects/` list + detail, with filtering, search and ordering."""

    filterset_fields = ["sector", "region", "project_type", "size_band", "sanction_year"]
    search_fields = ["name", "operator"]
    ordering_fields = ["name", "capex_actual", "capex_estimate", "sanction_year"]

    def get_queryset(self):
        return scoped_projects(self.request)

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ProjectDetailSerializer
        return ProjectListSerializer

    @action(detail=True, methods=["get"])
    def benchmark(self, request, pk=None):
        """Per-project benchmark payload: metrics, peer group, gaps, FEL."""
        project = self.get_object()
        data = services.project_benchmark(
            project, base_queryset=_scope_for(request)
        )
        return Response(data)


@api_view(["GET"])
@permission_classes([AllowAny])
def benchmark_view(request):
    """`/api/benchmarks/?sector=&region=&...` -> peer-group distributions."""
    query = BenchmarkQuerySerializer(data=request.query_params)
    query.is_valid(raise_exception=True)
    data = services.get_benchmark(
        query.to_filters(), base_queryset=_scope_for(request)
    )
    return Response(data)


@api_view(["GET"])
@permission_classes([AllowAny])
def portfolio_view(request):
    """`/api/portfolio/?sector=&...` -> roll-up KPIs for the filtered set."""
    query = BenchmarkQuerySerializer(data=request.query_params)
    query.is_valid(raise_exception=True)
    filters = query.to_filters()

    qs = services.filter_projects(scoped_projects(request), filters)
    rows = list(qs)

    if not rows:
        return Response(
            {"filters": filters, "count": 0, "total_capex": 0, "kpis": {}}
        )

    total_capex_actual = sum(p.capex_actual for p in rows)
    total_capex_estimate = sum(p.capex_estimate for p in rows)

    # Capex-weighted cost growth: big projects move the portfolio number more.
    weighted_cost_growth = (
        (total_capex_actual - total_capex_estimate) / total_capex_estimate
        if total_capex_estimate
        else 0.0
    )

    cost_growths = [p.cost_growth for p in rows]
    schedule_slips = [p.schedule_slip for p in rows]
    fel_scores = [p.fel.score for p in rows]

    # Share of portfolio capex sitting above the peer median cost growth.
    bench = services.get_benchmark(filters, base_queryset=_scope_for(request))
    cg_p50 = bench["distributions"].get("cost_growth", {}).get("p50")
    capex_over_norm = sum(
        p.capex_actual
        for p in rows
        if cg_p50 is not None and p.cost_growth > cg_p50
    )

    kpis = {
        "weighted_cost_growth": round(weighted_cost_growth, 4),
        "median_cost_growth": round(stats.percentile(cost_growths, 50), 4),
        "median_schedule_slip": round(stats.percentile(schedule_slips, 50), 4),
        "avg_fel_score": round(sum(fel_scores) / len(fel_scores), 1),
        "pct_over_budget": round(
            100.0 * sum(1 for cg in cost_growths if cg > 0) / len(rows), 1
        ),
        "pct_capex_over_peer_norm": round(
            100.0 * capex_over_norm / total_capex_actual, 1
        )
        if total_capex_actual
        else 0.0,
    }

    return Response(
        {
            "filters": filters,
            "count": len(rows),
            "total_capex": round(total_capex_actual, 1),
            "peer_n": bench["n"],
            "kpis": kpis,
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def meta_view(request):
    """`/api/meta/` -> filter option lists + metric metadata for the UI."""
    return Response(
        {
            "sectors": [{"value": v, "label": l} for v, l in Sector.choices],
            "regions": [{"value": v, "label": l} for v, l in Region.choices],
            "project_types": [
                {"value": v, "label": l} for v, l in ProjectType.choices
            ],
            "size_bands": [
                {"value": key, "label": label} for key, label, *_ in SIZE_BANDS
            ],
            "metrics": [
                {
                    "key": "capex_intensity",
                    "label": "Capex Intensity",
                    "unit": "$M / unit",
                    "higher_is_worse": True,
                },
                {
                    "key": "cost_growth",
                    "label": "Cost Growth",
                    "unit": "%",
                    "higher_is_worse": True,
                },
                {
                    "key": "schedule_slip",
                    "label": "Schedule Slip",
                    "unit": "%",
                    "higher_is_worse": True,
                },
            ],
            "fel_bands": [
                {"min": 80, "label": "Best Practical"},
                {"min": 60, "label": "Good"},
                {"min": 40, "label": "Fair"},
                {"min": 0, "label": "Screening"},
            ],
        }
    )
