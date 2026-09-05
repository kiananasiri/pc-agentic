from django.contrib import admin
from .models import Conversation, Message, Feedback, ProblemReport


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ["id", "timestamp","status","webhook_status", "question"]


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ["id", "user_id", "created_at"]


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ["id", "message", "type", "user_id", "created_at"]



@admin.register(ProblemReport)
class ProblemReportAdmin(admin.ModelAdmin):
    list_display = ["id", "message", "status", "created_at", "close_admin_id"]
    list_filter = ["status"]
    search_fields = ["message__content", "description"]
    readonly_fields = ["created_at", "updated_at"]