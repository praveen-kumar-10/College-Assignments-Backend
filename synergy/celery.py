from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

from celery import shared_task
from synergy import settings
from django.core.mail import send_mail
from django.core.mail import EmailMultiAlternatives


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'synergy.settings')

app = Celery('synergy',broker='amqps://xxfncfsf:hLqlc0FVdsXnyy9N9VbbKsDR-X3lcdPI@puffin.rmq2.cloudamqp.com/xxfncfsf')

app.config_from_object('django.conf:settings', namespace='CELERY')


@app.task()
def send_email(subject,text,html,email):
    try:
        email_from = settings.EMAIL_HOST_USER
        recipient_list = [email, ]
        msg = EmailMultiAlternatives(subject, text, email_from, recipient_list)
        msg.attach_alternative(html, "text/html")
        msg.send()

    except Exception as e:
        print(e)

