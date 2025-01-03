from celery import Celery
from flask import current_app as app
from flask import current_app as app
from celery.schedules import crontab 
import pytz

celery = Celery('web', broker='redis://192.168.29.118:6379/0')

celery.conf.update(
    result_backend='redis://192.168.29.118:6379/0',
    timezone='Asia/Kolkata',
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    imports=['web.tasks'],
    broker_connection_retry_on_startup = True
)

celery.conf.beat_schedule = {
    'send_daily_reminders': {
        'task': 'web.tasks.send_daily_reminders',  # path to the task function
        'schedule': crontab(hour=18, minute=00),  # Run daily at 6 PM
    },
    'send_monthly_activity_report': {
        'task': 'web.tasks.send_monthly_activity_report',  # path to the task function
        'schedule': crontab(hour=18, minute=0, day_of_month=1),  # Run on the 1st of every month at 6 PM
    },
}