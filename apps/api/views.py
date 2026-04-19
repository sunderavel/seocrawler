from http.client import BAD_REQUEST

from django.shortcuts import get_object_or_404, render

# Create your views here.
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from apps.seo.models import Domain, Insight, Page
from core.response_format import message_response
from core.response_message import INVALID_INPUT, SC_400
from apps.api.serializers import DomainSerializer, InsightSerializer, PageSerializer
from core.pagination import StandardPagination

class DomainListAPIView(APIView):

    def get(self, request):
        try:
            queryset = Domain.objects.all().order_by("-created_at")

            paginator = StandardPagination()
            page = paginator.paginate_queryset(queryset, request)
            print('page',page)
            serializer = DomainSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        except Exception as e:
            validation_error_code = SC_400
            return Response(message_response(INVALID_INPUT, validation_error_code), status=BAD_REQUEST)
    
class DomainPagesAPIView(APIView):

    def get(self, request, domain_id):
        try:
            get_object_or_404(Domain, id=domain_id)

            queryset = Page.objects.filter(domain_id=domain_id).order_by("-crawled_at")

            paginator = StandardPagination()
            page = paginator.paginate_queryset(queryset, request)
            serializer = PageSerializer(page, many=True, context={"request": request})
            
            return paginator.get_paginated_response(serializer.data)
        except Exception as e:
            validation_error_code = SC_400
            return Response(message_response(INVALID_INPUT, validation_error_code), status=BAD_REQUEST)
    
class PageInsightAPIView(APIView):

    def get(self, request, page_id):
        try:
            insight = get_object_or_404(Insight, page_id=page_id)

            serializer = InsightSerializer(insight)
            return Response(serializer.data)
        except Exception as e:
            validation_error_code = SC_400
            return Response(message_response(INVALID_INPUT, validation_error_code), status=BAD_REQUEST)
    
