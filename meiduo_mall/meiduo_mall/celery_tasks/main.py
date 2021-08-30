# Entry of Celery
from celery import Celery
# create Celery instance
celery_app = Celery("meiduo")

celery_app.config_from_object("celery_tasks.config")

# 注册任务
celery_app.autodiscover_tasks(["celery_tasks.sms"])


