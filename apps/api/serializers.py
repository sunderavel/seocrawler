# serializers.py
from rest_framework import serializers
from apps.seo.models import Domain, Page, Insight


class DomainSerializer(serializers.ModelSerializer):
    class Meta:
        model = Domain
        fields = ["id", "domain_name", "created_at"]


class PageSerializer(serializers.ModelSerializer):
    insight_page = serializers.SerializerMethodField()

    class Meta:
        model = Page
        fields = ["id", "url", "status_code", "crawled_at", "insight_page"]

    def get_insight_page(self, obj):
        request = self.context.get("request")
        return request.build_absolute_uri(
            f"/pages/{obj.id}/insights/"
        )

class InsightSerializer(serializers.ModelSerializer):
    class Meta:
        model = Insight
        fields = "__all__"