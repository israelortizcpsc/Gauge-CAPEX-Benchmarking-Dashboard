from django.contrib import admin

from .models import BenchmarkAggregate, Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "sector",
        "region",
        "project_type",
        "size_band",
        "capex_actual",
        "sanction_year",
        "is_confidential",
    )
    list_filter = ("sector", "region", "project_type", "size_band", "is_confidential")
    search_fields = ("name", "operator")


@admin.register(BenchmarkAggregate)
class BenchmarkAggregateAdmin(admin.ModelAdmin):
    list_display = ("signature", "n", "updated_at")
    readonly_fields = ("signature", "filters", "n", "distributions", "updated_at")
