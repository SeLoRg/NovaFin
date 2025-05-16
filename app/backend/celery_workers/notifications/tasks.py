from celery_workers.notifications import utils
from celery_workers.notifications.app import celery_app


@celery_app.task(
    name="send_email_verification",
    ignore_result=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 10},
)
def send_verification_email(email: str, verification_code: str):
    subject = "Email Verification"
    body = f"Перейдите по указанной сслыке для подтверждения почты: {verification_code}"

    utils.send_email(email, subject, body)

    return f"Verification email sent to {email}"


@celery_app.task(
    name="send_email_opt_code",
    ignore_result=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 10},
)
def send_sms_verify_code(email: str, opt_code: str):
    subject = "2FA Verification"
    body = f"Ваш код подтверждения: {opt_code}"

    utils.send_email(email=email, subject=subject, body=body)

    return f"Verification code send to {email}"
