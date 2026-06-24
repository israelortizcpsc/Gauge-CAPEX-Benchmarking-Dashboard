"""DRF serializers. Read serializers expose derived metrics; the query
serializer validates and normalizes incoming filter parameters so the rest of
the stack can trust its inputs (security: validate at the boundary)."""

from __future__ import annotations

from rest_framework import serializers

from .models import (
    ProjectType,
    Region,
    Sector,
    SIZE_BANDS,
    Project,
)

SIZE_BAND_KEYS = [band[0] for band in SIZE_BANDS]


class ProjectListSerializer(serializers.ModelSerializer):
    """Compact row for tables and filtering."""

    sector_label = serializers.CharField(source="get_sector_display", read_only=True)
    region_label = serializers.CharField(source="get_region_display", read_only=True)
    project_type_label = serializers.CharField(
        source="get_project_type_display", read_only=True
    )
    cost_growth = serializers.FloatField(read_only=True)
    schedule_slip = serializers.FloatField(read_only=True)
    fel_score = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "id",
            "name",
            "operator",
            "sector",
            "sector_label",
            "region",
            "region_label",
            "project_type",
            "project_type_label",
            "size_band",
            "sanction_year",
            "capex_estimate",
            "capex_actual",
            "cost_growth",
            "schedule_slip",
            "fel_score",
        ]

    def get_fel_score(self, obj: Project) -> int:
        return obj.fel.score


class ProjectDetailSerializer(ProjectListSerializer):
    """Full project record including raw FEL inputs and physical size."""

    capex_intensity = serializers.FloatField(read_only=True)
    fel = serializers.SerializerMethodField()

    class Meta(ProjectListSerializer.Meta):
        fields = ProjectListSerializer.Meta.fields + [
            "capacity",
            "capacity_unit",
            "capex_intensity",
            "schedule_months_planned",
            "schedule_months_actual",
            "fel_scope",
            "fel_engineering",
            "fel_execution",
            "fel",
        ]

    def get_fel(self, obj: Project) -> dict:
        return obj.fel.as_dict()


class BenchmarkQuerySerializer(serializers.Serializer):
    """Validates the peer-group filter query string for benchmark endpoints."""

    sector = serializers.ChoiceField(choices=Sector.choices, required=False)
    region = serializers.ChoiceField(choices=Region.choices, required=False)
    project_type = serializers.ChoiceField(
        choices=ProjectType.choices, required=False
    )
    size_band = serializers.ChoiceField(choices=SIZE_BAND_KEYS, required=False)

    def to_filters(self) -> dict:
        """Validated, non-empty filter dict ready for the service layer."""
        return {k: v for k, v in self.validated_data.items() if v}
