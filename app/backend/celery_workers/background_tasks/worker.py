from celery_workers.background_tasks.tasks import celery_app

celery_app.worker_main(["worker", "--loglevel=info"])
