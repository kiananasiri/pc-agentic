from django.urls import path
from .views import *

urlpatterns = [
    path('conversations/', ConversationView.as_view()),
    path('conversations/<uuid:pk>/', ConversationDetailsView.as_view()),
    # path('conversations/<uuid:pk>/messages/', MessageView.as_view()),
    path('conversations/<uuid:conversation_id>/messages/<uuid:pk>', SingleMessageView.as_view()),
    path('conversations/<uuid:conversation_id>/archive-status', ArchiveStatusConversationView.as_view()),
    path('feedback-message', FeedbackMessageView.as_view()),
    path('feedback-message/report', FeedbackMessageReportView.as_view()),
    path('messages', MessageV2View.as_view()),

    path('problem-reports/', ProblemReportView.as_view()),
    path('problem-reports/<int:pk>', ProblemReportSingleView.as_view()),
    path('problem-reports/submit', SubmitProblemReportView.as_view()),
    path('problem-reports/change-status', ChangeProblemReportStatusView.as_view()),
]
