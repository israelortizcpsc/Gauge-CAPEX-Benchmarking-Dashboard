"""API smoke tests: status codes, validation, and role-scoped reads."""

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from benchmarks.tests.test_services import make_project

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    return APIClient()


class TestProjectsEndpoint:
    def test_list_and_filter(self, client):
        make_project(sector="mining")
        make_project(sector="oil_gas")
        resp = client.get("/api/projects/?sector=mining")
        assert resp.status_code == 200
        assert resp.json()["count"] == 1

    def test_anonymous_cannot_see_confidential(self, client):
        make_project(name="public", is_confidential=False)
        make_project(name="secret", is_confidential=True)
        resp = client.get("/api/projects/")
        names = {row["name"] for row in resp.json()["results"]}
        assert "secret" not in names
        assert "public" in names

    def test_staff_sees_confidential(self, client):
        make_project(name="secret", is_confidential=True)
        staff = User.objects.create_user("admin", is_staff=True)
        client.force_authenticate(staff)
        resp = client.get("/api/projects/")
        names = {row["name"] for row in resp.json()["results"]}
        assert "secret" in names


class TestBenchmarkEndpoint:
    def test_rejects_invalid_filter_value(self, client):
        resp = client.get("/api/benchmarks/?sector=not_a_sector")
        assert resp.status_code == 400

    def test_returns_distribution(self, client):
        for _ in range(10):
            make_project(sector="chemicals")
        resp = client.get("/api/benchmarks/?sector=chemicals")
        assert resp.status_code == 200
        assert resp.json()["n"] == 10


class TestPortfolioEndpoint:
    def test_rollup_kpis(self, client):
        for _ in range(10):
            make_project(sector="power")
        resp = client.get("/api/portfolio/?sector=power")
        body = resp.json()
        assert body["count"] == 10
        assert "weighted_cost_growth" in body["kpis"]
        assert body["total_capex"] > 0

    def test_empty_portfolio(self, client):
        resp = client.get("/api/portfolio/?sector=power")
        assert resp.status_code == 200
        assert resp.json()["count"] == 0


class TestMetaAndHealth:
    def test_meta_lists_options(self, client):
        resp = client.get("/api/meta/")
        body = resp.json()
        assert len(body["sectors"]) == 5
        assert len(body["project_types"]) == 5

    def test_healthz(self, client):
        resp = client.get("/healthz")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
