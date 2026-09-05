import uuid
from datetime import datetime
from random import choices

import pytz
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

tehran_timezone = pytz.timezone("Asia/Tehran")


class Conversation(models.Model):
    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True)
    user_id = models.CharField(max_length=64)
    is_archive = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Message(models.Model):
    class StatusChoices(models.TextChoices):
        S = "s", "Success"
        F = "f", "Failed"
        P = "p", "Pending"

    class ReasoningChoices(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        MINIMAL = "minimal", "Minimal"

    class SendToWebhookChoices(models.TextChoices):
        READY = "ready", "Ready"
        SENDING = "sending", "Sending"
        SENT = "sent", "Sent"
        ERROR = "error", "Error"

    id = models.CharField(unique=True, primary_key=True,max_length=64)
    # conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE,related_name="messages")
    question = models.TextField()
    answer = models.TextField(null=True, blank=True)
    price = models.FloatField(null=True,blank=True)
    query_refinement = models.BooleanField(null=True)
    analysis = models.JSONField(null=True,blank=True)
    analysis_fundamental = models.JSONField(null=True,blank=True)
    code = models.BooleanField(default=False)
    time = models.DateTimeField(default=timezone.now)
    timestamp = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    image_base64 = models.TextField(null=True)
    model = models.TextField(null=True)
    status = models.CharField(max_length=1,choices=StatusChoices.choices,default=StatusChoices.P)
    exception_text = models.TextField(null=True,blank=True)
    reasoning = models.CharField(max_length=255, null=True, blank=True,choices=ReasoningChoices.choices)
    webhook_status = models.CharField(max_length=20,choices=SendToWebhookChoices.choices,null=True,blank=True)
    answer_generation_duration = models.IntegerField(null=True,blank=True)
    webhook_error = models.TextField(null=True, blank=True)


class Feedback(models.Model):
    class TypeChoices(models.IntegerChoices):
        LIKE = 0
        DISLIKE = 1

    message = models.ForeignKey(Message,on_delete=models.CASCADE)
    type = models.IntegerField(choices=TypeChoices.choices)
    user_id = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)



class ProblemReport(models.Model):
    class StatusChoices(models.TextChoices):
        OPEN = "open", "Open"
        CLOSE = "close", "Close"
    message = models.OneToOneField(Message, on_delete=models.CASCADE, related_name="problem_report")
    description = models.TextField()
    status = models.CharField(max_length=20, default=StatusChoices.OPEN,choices=StatusChoices.choices)

    close_message = models.TextField(null=True, blank=True)
    close_admin_id = models.CharField(max_length=64, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.description


# @receiver(post_save, sender=Message)
# def update_conversation_timestamp(sender, instance, **kwargs):
#     instance.conversation.updated_at = timezone.now()
#     instance.conversation.save()
