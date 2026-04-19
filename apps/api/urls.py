from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.api.views import DomainListAPIView, DomainPagesAPIView, PageInsightAPIView

urlpatterns = [
    path("domains/", DomainListAPIView.as_view()),
    path("domains/<int:domain_id>/pages/", DomainPagesAPIView.as_view()),
    path("pages/<int:page_id>/insights/", PageInsightAPIView.as_view()),
]