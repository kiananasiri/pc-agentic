import json

from pydantic.v1 import UUID4
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
import copy

from ChatbotBackend.tasks import run_ai_function
from public_app.src.chat_bot import chat
from .models import *
import traceback


class ConversationSerializer(serializers.ModelSerializer):
    first_message = serializers.SerializerMethodField(read_only=True)

    def get_first_message(self, obj):
        first_message = obj.messages.filter().order_by("timestamp").first()
        if first_message:
            return MessageSerializer(obj.messages.filter().order_by("timestamp").first()).data
        return None
        # return MessageSerializer(obj.messages.filter().order_by("timestamp").first()).data

    class Meta:
        model = Conversation
        fields = ["id", "user_id", "first_message", "is_archive", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]


class MessageSerializer(serializers.ModelSerializer):
    MODEL_CHOICES = [
        ("gpt-4o-mini", "gpt-4o-mini (1x)"),
        ("gpt-4.1-nano", "gpt-4.1-nano (0.67x)"),
        ("gpt-4.1-mini", "gpt-4.1-mini (2.67x)"),
        ("gpt-4.1", "gpt-4.1 (13.33x)"),
        ("gpt-4o", "gpt-4o (16.67x)"),
    ]

    model = serializers.ChoiceField(choices=MODEL_CHOICES)
    has_report = serializers.SerializerMethodField(read_only=True)
    report_id = serializers.SerializerMethodField(read_only=True)
    feedback = serializers.SerializerMethodField(read_only=True)
    conversationHistory = serializers.ListSerializer(child=serializers.JSONField(), write_only=True)

    def get_has_report(self, obj):
        return ProblemReport.objects.filter(message=obj).exists()

    def get_report_id(self, obj):
        record = ProblemReport.objects.filter(message=obj).first()
        if not record:
            return None
        return record.pk

    def get_feedback(self, obj):
        feedback = Feedback.objects.filter(message=obj).first()
        if not feedback:
            return None
        return FeedbackSerializer(feedback).data

    class Meta:
        model = Message
        fields = ["id", "question", "answer", "price", "image_base64", "analysis", "analysis_fundamental", "code",
                  "report_id","conversationHistory","reasoning",
                  "query_refinement", "time", "model", "has_report", "feedback", "status", "timestamp", "updated_at"]
        read_only_fields = ["answer", "price", "has_report", "image_base64", "query_refinement", "time", "timestamp",
                            "status",
                            "updated_at"]

    def create(self, validated_data):

        request = self.context.get("request")
        conversation = Conversation.objects.filter(id=request.resolver_match.kwargs.get("pk")).first()
        if not conversation:
            raise ValidationError("Conversation not found")
        # conversation_history = [
        #     {
        #         "id": message.id,
        #         "user_id": str(message.conversation.user_id),
        #         "convo_id": str(message.conversation.id),
        #         "message_id": str(message.id),
        #         "question": message.question,
        #         "answer": message.answer,
        #         "price": message.price,
        #         "query_refinement": message.query_refinement,
        #         "time": message.time,
        #         "timestamp": message.timestamp,
        #         "image_base64": message.image_base64,
        #         "code": message.code,
        #     }
        #     for message in conversation.messages.filter(status=Message.StatusChoices.S, answer__isnull=False)
        # ]

        validated_data["conversation"] = conversation
        validated_data["image_base64"] = request.data.get("image_base64")
        validated_data["code"] = request.data.get("code")
        conversation_history = validated_data.pop("conversationHistory")
        m = Message.objects.create(**validated_data)
        run_ai_function.delay(message_id=m.id, conversation_history_string=json.dumps(conversation_history))
        return m


class MessageV2Serializer(serializers.ModelSerializer):
    MODEL_CHOICES = [
        ("gpt-4o-mini", "gpt-4o-mini (1x)"),
        ("gpt-4.1-nano", "gpt-4.1-nano (0.67x)"),
        ("gpt-4.1-mini", "gpt-4.1-mini (2.67x)"),
        ("gpt-4.1", "gpt-4.1 (13.33x)"),
        ("gpt-4o", "gpt-4o (16.67x)"),
        ("gpt-5", "gpt-5"),
        ("gpt-5-mini", "gpt-5-mini"),
        ("gpt-5-nano", "gpt-5-nano"),
    ]

    model = serializers.ChoiceField(choices=MODEL_CHOICES)
    conversationHistory = serializers.ListSerializer(child=serializers.JSONField(), write_only=True)

    class Meta:
        model = Message
        fields = ["id", "question", "answer", "price", "image_base64", "analysis", "analysis_fundamental", "code","conversationHistory","reasoning",
                  "query_refinement", "time", "model", "timestamp", "updated_at"]
        read_only_fields = ["answer", "price", "image_base64", "query_refinement", "time", "timestamp",
                            "status",
                            "updated_at"]

    def create(self, validated_data):

        request = self.context.get("request")
        print(validated_data,request.data)


        validated_data["image_base64"] = request.data.get("image_base64")
        validated_data["code"] = request.data.get("code")
        conversation_history = validated_data.pop("conversationHistory")
        validated_data["analysis_fundamental"] = request.data.get("analysis_onchain",None)
        validated_data["analysis"] = request.data.get("analysis_technical",None)
        m = Message.objects.create(**validated_data)
        run_ai_function.delay(message_id=m.id, conversation_history_string=json.dumps(conversation_history))
        return m


class FeedbackSerializer(serializers.ModelSerializer):
    message = serializers.PrimaryKeyRelatedField(queryset=Message.objects.only("id"), write_only=True)

    class Meta:
        model = Feedback
        fields = "__all__"

    def create(self, validated_data):
        reaction_type = validated_data["type"]
        message = validated_data["message"]
        user_id = validated_data["user_id"]
        record, created = Feedback.objects.update_or_create(message=message,
                                                            user_id=user_id,
                                                            defaults={
                                                                "type": reaction_type
                                                            }
                                                            )

        return record


class ProblemReportSerializer(serializers.ModelSerializer):
    message = MessageSerializer(read_only=True)
    conversation = serializers.SerializerMethodField(read_only=True)

    def get_conversation(self, obj) -> UUID4 | None:
        if obj.message and obj.message.conversation:
            return obj.message.conversation.id
        return None

    class Meta:
        model = ProblemReport
        fields = "__all__"


class SubmitProblemReportSerializer(serializers.ModelSerializer):
    message = serializers.PrimaryKeyRelatedField(queryset=Message.objects.only("id"), write_only=True)

    class Meta:
        model = ProblemReport
        fields = ["message", "description", "status", "close_message", "close_admin_id"]
        read_only_fields = ["status", "close_message", "close_admin_id"]

    def to_representation(self, instance):
        return ProblemReportSerializer(instance).data

    def create(self, validated_data):
        message = validated_data["message"]
        description = validated_data["description"]
        report, created = ProblemReport.objects.update_or_create(message=message,
                                                                 defaults={
                                                                     "description": description
                                                                 }
                                                                 )
        return report


class ChangeProblemReportStatusSerializer(serializers.ModelSerializer):
    report_id = serializers.PrimaryKeyRelatedField(queryset=ProblemReport.objects.only("id"), write_only=True)
    close_admin_id = serializers.CharField(write_only=True, required=True)
    status = serializers.ChoiceField(choices=ProblemReport.StatusChoices.choices, required=True)

    def to_representation(self, instance):
        return ProblemReportSerializer(instance).data

    class Meta:
        model = ProblemReport
        fields = ["report_id", "status", "close_message", "close_admin_id"]

    def update(self, instance, validated_data):
        instance.status = validated_data.get("status", instance.status)
        instance.close_message = validated_data.get("close_message", instance.close_message)
        instance.close_admin_id = validated_data.get("close_admin_id", instance.close_admin_id)
        instance.save()
        return instance
