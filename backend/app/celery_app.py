from celery import Celery

from app.config import get_settings

celery_app = Celery("tacho", broker=get_settings().redis_url, backend=get_settings().redis_url)


@celery_app.task(name="tacho.ping")
def ping() -> str:
    return "pong"


from app import tasks  # noqa: E402,F401 — registers tasks on celery_app, imported last to dodge the circular import
