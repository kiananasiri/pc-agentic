import json

from celery import Celery
import os
from django.conf import settings
import time
import requests
from django.core.files.base import ContentFile
from celery.utils.log import get_task_logger
from requests.adapters import HTTPAdapter, Retry

logger = get_task_logger(__name__)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ChatbotBackend.settings')

app = Celery('ChatbotBackend')
app.config_from_object('django.conf:settings', namespace="CELERY")
app.autodiscover_tasks(['chat_app'])