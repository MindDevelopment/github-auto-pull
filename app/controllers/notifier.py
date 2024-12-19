import requests
import logging

def send_notification(webhook_url, message):
    try:
        payload = {"content": message if isinstance(message, str) else "\n".join(message)}
        requests.post(webhook_url, json=payload)
        logging.info("Notificatie verzonden.")
    except Exception as e:
        logging.error(f"Fout bij verzenden notificatie: {e}")
