"""Root URL configuration for the Gauge project."""

from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def healthz(_request):
    """Liveness probe for the hosting platform."""
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("benchmarks.urls")),
    path("healthz", healthz, name="healthz"),
]
