"""Service-layer tests: signatures, materialization, caching, role scoping."""

import pytest
from django.core.cache import cache

from benchmarks import services
from benchmarks.models import BenchmarkAggregate, Project

pytestmark = pytest.mark.django_db


def make_project(**overrides) -> Project:
    defaults = dict(
        name="Test",
        operator="Acme",
        sector="mining",
        region="north_america",
        project_type="reliability",
        sanction_year=2020,
        capacity=1000.0,
        capacity_unit="kt/yr",
        capex_estimate=50.0,
        capex_actual=55.0,
        schedule_months_planned=12.0,
        schedule_months_actual=14.0,
        fel_scope=3,
        fel_engineering=3,
        fel_execution=3,
    )
    defaults.update(overrides)
    return Project.objects.create(**defaults)


class TestSignature:
    def test_is_order_independent_and_drops_empty(self):
        a = services.make_signature({"sector": "mining", "region": "europe"})
        b = services.make_signature({"region": "europe", "sector": "mining", "size_band": None})
        assert a == b

    def test_empty_filters_is_all(self):
        assert services.make_signature({}) == "all"


class TestGetBenchmark:
    def test_materializes_and_caches(self):
        for _ in range(20):
            make_project()

        cache.clear()
        BenchmarkAggregate.objects.all().delete()

        result = services.get_benchmark({"sector": "mining"})
        assert result["n"] == 20
        assert "cost_growth" in result["distributions"]

        # An aggregate row was written, and the result is now cached.
        assert BenchmarkAggregate.objects.filter(signature="sector=mining").exists()
        assert cache.get("benchmark:all:sector=mining") is not None

    def test_empty_peer_group_has_no_distributions(self):
        result = services.get_benchmark({"sector": "power"})
        assert result["n"] == 0
        assert result["distributions"] == {}


class TestRoleScoping:
    def test_confidential_excluded_from_scoped_queryset(self):
        make_project(name="public", is_confidential=False)
        make_project(name="secret", is_confidential=True)

        scoped = Project.objects.filter(is_confidential=False)
        result = services.get_benchmark({"sector": "mining"}, base_queryset=scoped)
        assert result["n"] == 1

        unscoped = services.get_benchmark({"sector": "mining"})
        assert unscoped["n"] == 2


class TestProjectBenchmark:
    def test_widens_peer_group_when_exact_slice_is_thin(self):
        target = make_project(region="europe", project_type="compliance")
        # Only one project in the exact slice -> should widen the peer group.
        for _ in range(15):
            make_project(region="asia_pacific", project_type="reliability")

        payload = services.project_benchmark(target)
        assert payload["peer_group"]["is_exact"] is False
        assert payload["peer_group"]["n"] >= 12
        assert "fel" in payload
        assert payload["metrics"]["cost_growth"]["percentile_rank"] is not None
