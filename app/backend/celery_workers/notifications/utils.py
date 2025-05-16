import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from celery_workers.notifications.config import settings
import requests


def send_email(email: str, subject: str, body: str):
    # Создаём сообщение
    msg = MIMEMultipart()
    msg["From"] = f"{settings.SMTP_MAIL_FROM_NAME} <{settings.SMTP_MAIL_USER}>"
    msg["To"] = email
    msg["Subject"] = subject

    # Добавляем текст письма
    msg.attach(MIMEText(body, "plain"))

    # Подключаемся к серверу и отправляем письмо
    try:
        with smtplib.SMTP(settings.SMTP_MAIL_SERVER, settings.SMTP_MAIL_PORT) as server:
            server.starttls()  # Если SMTP_MAIL_STARTTLS=1
            server.login(settings.SMTP_MAIL_USER, settings.SMTP_MAIL_PASSWORD)
            server.send_message(msg)
        print(f"Email успешно отправлен на {email}")
    except Exception as e:
        print(f"Ошибка при отправке email: {e}")


def send_sms(phone: str, text: str):
    response = requests.post(
        url=settings.SMS_API_URL,
        headers={"Authorization": f"Bearer {settings.SMS_API_KEY}"},
        json={"to": phone, "message": text},
        timeout=10,
    )

    if response.status_code != 200:
        raise Exception(f"Не удалось отправить SMS: {response.text}")

    return
