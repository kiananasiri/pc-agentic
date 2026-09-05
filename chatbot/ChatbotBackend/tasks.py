import datetime
import json
import traceback

from django.db.models import Q

from ChatbotBackend.celery import app as celery_app
from chat_app.models import Message
from public_app.src.chat_bot import chat
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def send_to_webhook(data):
        dev_url = "https://dev-api-user-zp91.parsiancrypto.info/rest/chatbot/message/webhook"
        url = "https://api.parsiancrypto.com/chatbot/message/webhook"

        dev_token = '237d464556175aba22a14fd110b8cd9fece71948'
        headers = {
            "Authorization": f"Bearer {dev_token}"
        }

        # Configure retry strategy
        retry_strategy = Retry(
            total=5,
            backoff_factor=2,
            status_forcelist=list(range(500, 600)),
            allowed_methods=["PATCH"],
            raise_on_status=False
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)

        # Create a session with retry support
        with requests.Session() as session:
            session.mount("https://", adapter)

            response = session.patch(dev_url, json=data, headers=headers, timeout=10)
            print(response.text)
            return response

@celery_app.task(bind=True)
def run_ai_function(self,message_id,conversation_history_string):
    message = Message.objects.get(id=message_id)
    conversation_history = json.loads(conversation_history_string)
    analysis = message.analysis
    fundamental = message.analysis_fundamental
    exception = False
    exception_message = False
    answer_dic = None
    model = message.model if message.model else "gpt-4o"
    start_time_stamp = datetime.datetime.now().timestamp()
    if message.image_base64 != "":
        try:
            answer_dic = chat(message.question, conversation_history,
                              image_documents=message.image_base64,
                              analysis=analysis, code=message.code, fundamental=fundamental,
                              model=model,reasoning=message.reasoning)

        except Exception as ex:
            exception_message = traceback.format_exc()
            exception = True
    else:
        try:
            answer_dic = chat(message.question, conversation_history,
                              analysis=analysis, code=message.code, fundamental=fundamental,
                              model=model,reasoning=message.reasoning)
        except Exception as ex:
            exception = True
            exception_message = traceback.format_exc()
    end_time_stamp = datetime.datetime.now().timestamp()
    message.answer = answer_dic["answer"] if answer_dic else None
    message.price = answer_dic["price"] if answer_dic else None
    message.status = Message.StatusChoices.S if not exception else Message.StatusChoices.F
    message.exception_text = exception_message
    message.webhook_status = Message.SendToWebhookChoices.READY
    message.answer_generation_duration = int((end_time_stamp - start_time_stamp)) * 1000
    message.save()

    send_ready_message_to_webhook.delay()

@celery_app.task(bind=True)
def send_ready_message_to_webhook(self):
    messages = Message.objects.filter(Q(webhook_status=Message.SendToWebhookChoices.READY) | Q(webhook_status=Message.SendToWebhookChoices.ERROR))
    for message in messages:
        data = {
            "id": str(message.id),
            "question": message.question,
            "code": message.code,
            "image_base64": message.image_base64,
            "model": message.model,
            "reasoning": message.reasoning,
            "answer": message.answer,
            "price": message.price,
            "analysis_onchain": message.analysis_fundamental,
            "analysis_technical": message.analysis,
            "status": message.status,
            "answer_generation_duration": message.answer_generation_duration,
            "created_at": message.timestamp.isoformat(),
            "updated_at": message.updated_at.isoformat()
        }
        message.webhook_status = Message.SendToWebhookChoices.SENDING
        message.save()
        response = send_to_webhook(data)
        print(response,response.status_code not in range(500, 600))
        if response.status_code not in range(500, 600):
            message.webhook_status = Message.SendToWebhookChoices.SENT
        else:
            print("In else")
            message.webhook_error = f"{response.text} - Code:{response.status_code}" if response else f"No response from webhook - Code:{response.status_code}"
            message.webhook_status = Message.SendToWebhookChoices.ERROR

        message.save()
