from celery_workers.notifications.tasks import celery_app

celery_app.worker_main(["worker", "--loglevel=info"])
