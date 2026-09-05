from http.client import HTTPResponse

from django.http import JsonResponse
from django.shortcuts import render
from rest_framework import generics, mixins
from rest_framework.exceptions import NotFound
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticated
from django_filters import rest_framework as rfilters
from public_app.utils import StandardResultsSetPagination
from .serializer import *
from django_filters import rest_framework as filters
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


class ConversationView(generics.GenericAPIView, mixins.ListModelMixin,
                       mixins.CreateModelMixin):
    queryset = Conversation.objects.filter()
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = (rfilters.DjangoFilterBackend, OrderingFilter)
    pagination_class = StandardResultsSetPagination
    filterset_fields = ["is_archive"]
    ordering_fields = ['created_at', 'updated_at']

    def get_queryset(self):
        user_id = self.request.GET.get("user_id")
        if not user_id:
            return self.queryset
        return self.queryset.filter(user_id=user_id)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)


class ConversationDetailsView(generics.GenericAPIView, mixins.RetrieveModelMixin):
    queryset = Conversation.objects.filter().order_by("-created_at")
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)


class MessageV2View(generics.GenericAPIView,
                  mixins.CreateModelMixin):
    queryset = Message.objects.filter().order_by("-timestamp")
    serializer_class = MessageV2Serializer
    permission_classes = [IsAuthenticated]
    filter_backends = (rfilters.DjangoFilterBackend, OrderingFilter)
    pagination_class = StandardResultsSetPagination
    ordering_fields = ['timestamp']
    handler500 = 'rest_framework.exceptions.server_error'

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)


class SingleMessageView(generics.GenericAPIView, mixins.RetrieveModelMixin,
                        mixins.CreateModelMixin):
    queryset = Message.objects.filter().order_by("-timestamp")
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]
    handler500 = 'rest_framework.exceptions.server_error'

    def get_queryset(self):
        conversation_id = self.kwargs.get('conversation_id')
        pk = self.kwargs.get('pk')
        return Message.objects.filter(conversation__id=conversation_id, id=pk)

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)


class ArchiveStatusConversationView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, conversation_id):
        conversation = Conversation.objects.filter(id=conversation_id).first()
        if not conversation:
            raise NotFound(code=404)
        is_archive = request.data.get('is_archive', True)

        conversation.is_archive = is_archive
        conversation.save()
        return JsonResponse(ConversationSerializer(conversation).data)


class FeedbackMessageView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FeedbackSerializer

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)


class FeedbackMessageReportView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="feedback message report",
        manual_parameters=[
            openapi.Parameter(
                'from_date',
                openapi.IN_QUERY,
                description="Start date (YYYY-MM-DD)",
                type=openapi.TYPE_STRING,
                format='date',
                required=True
            ),
            openapi.Parameter(
                'to_date',
                openapi.IN_QUERY,
                description="End date (YYYY-MM-DD)",
                type=openapi.TYPE_STRING,
                format='date',
                required=True
            ),
        ],
        responses={
            200: openapi.Response(
                description="Feedback report counts by type and analysis",
                examples={
                    "application/json": {
                        "normal": {"like_count": 0, "dislike_count": 0},
                        "technical_analysis": {"like_count": 0, "dislike_count": 0},
                        "fundamental_analysis": {"like_count": 0, "dislike_count": 0}
                    }
                }
            ),
            400: openapi.Response(
                description="Missing required parameters",
                examples={"application/json": {"error": "from_date and to_date are required"}}
            )
        }
    )
    def get(self, request):
        from_date = request.GET.get('from_date')
        to_date = request.GET.get('to_date')
        if not from_date or not to_date:
            return JsonResponse({"error": "from_date and to_date are required"}, status=400)

        feedbacks = Feedback.objects.filter(created_at__gte=from_date, created_at__lte=to_date)
        data = {
            "normal":{
                "like_count": feedbacks.filter(type=0,message__analysis__isnull=True,message__analysis_fundamental__isnull=True).count(),
                "dislike_count": feedbacks.filter(type=1,message__analysis__isnull=True,message__analysis_fundamental__isnull=True).count(),
            },
            "technical_analysis": {
                "like_count": feedbacks.filter(type=0, message__analysis__isnull=False,message__analysis_fundamental__isnull=True).count(),
                "dislike_count": feedbacks.filter(type=1, message__analysis__isnull=False,message__analysis_fundamental__isnull=True).count(),
            },
            "fundamental_analysis": {
                "like_count": feedbacks.filter(type=0, message__analysis__isnull=True, message__analysis_fundamental__isnull=False).count(),
                "dislike_count": feedbacks.filter(type=1, message__analysis__isnull=True, message__analysis_fundamental__isnull=False).count(),
            }

        }
        return JsonResponse(data)


class ProblemReportView(generics.ListAPIView):
    class ProblemReportFilter(filters.FilterSet):
        created_at__gte = filters.DateTimeFilter(field_name="created_at", lookup_expr="gte")
        created_at__lte = filters.DateTimeFilter(field_name="created_at", lookup_expr="lte")

        class Meta:
            model = ProblemReport
            fields = ['status', 'created_at__gte', 'created_at__lte']

    queryset = ProblemReport.objects.all()
    serializer_class = ProblemReportSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = (rfilters.DjangoFilterBackend, OrderingFilter)
    filterset_class = ProblemReportFilter
    pagination_class = StandardResultsSetPagination

class ProblemReportSingleView(generics.RetrieveAPIView):
    queryset = ProblemReport.objects.all()
    serializer_class = ProblemReportSerializer
    permission_classes = [IsAuthenticated]


class SubmitProblemReportView(generics.CreateAPIView):
    serializer_class = SubmitProblemReportSerializer
    permission_classes = [IsAuthenticated]


class ChangeProblemReportStatusView(generics.UpdateAPIView):
    serializer_class = ChangeProblemReportStatusSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        report_id = self.request.data.get("report_id")
        record = ProblemReport.objects.filter(id=report_id)
        if not record.exists():
            raise NotFound(code=404)
        return record.first()
