import smtplib
from email.message import EmailMessage
from typing import Any

import httpx

from .settings import get_settings


async def send_webhook_alert(title: str, payload: dict[str, Any]) -> bool:
    settings = get_settings()
    if not settings.alert_webhook_url:
        return False
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(settings.alert_webhook_url, json={'title': title, 'payload': payload})
        response.raise_for_status()
    return True


async def send_telegram_alert(text: str) -> bool:
    settings = get_settings()
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        return False
    url = f'https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage'
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(url, json={'chat_id': settings.telegram_chat_id, 'text': text})
        response.raise_for_status()
    return True


def send_email_alert(subject: str, body: str) -> bool:
    settings = get_settings()
    host = getattr(settings, 'smtp_host', None)
    user = getattr(settings, 'smtp_user', None)
    password = getattr(settings, 'smtp_password', None)
    to_addr = getattr(settings, 'smtp_to', None)
    from_addr = getattr(settings, 'smtp_from', None) or user
    if not host or not to_addr or not from_addr:
        return False
    message = EmailMessage()
    message['Subject'] = subject
    message['From'] = from_addr
    message['To'] = to_addr
    message.set_content(body)
    with smtplib.SMTP(host, int(getattr(settings, 'smtp_port', 587))) as smtp:
        smtp.starttls()
        if user and password:
            smtp.login(user, password)
        smtp.send_message(message)
    return True


async def notify_execution_event(title: str, payload: dict[str, Any]) -> dict[str, bool]:
    telegram = await send_telegram_alert(f'{title}\n{payload}')
    webhook = await send_webhook_alert(title, payload)
    email = send_email_alert(title, str(payload))
    return {'telegram': telegram, 'webhook': webhook, 'email': email}
