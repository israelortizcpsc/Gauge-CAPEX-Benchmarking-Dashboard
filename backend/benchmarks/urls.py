from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"projects", views.ProjectViewSet, basename="project")

urlpatterns = [
    path("", include(router.urls)),
    path("benchmarks/", views.benchmark_view, name="benchmarks"),
    path("portfolio/", views.portfolio_view, name="portfolio"),
    path("meta/", views.meta_view, name="meta"),
]
