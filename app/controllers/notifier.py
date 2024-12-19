import requests
import logging
from datetime import datetime

def create_embed(updates, status="success"):
    colors = {
        "success": 3066993,  # Groen
        "warning": 16776960,  # Geel
        "error": 15158332    # Rood
    }
    
    embed = {
        "title": "GitHub Sync Update",
        "color": colors[status],
        "timestamp": datetime.utcnow().isoformat(),
        "fields": [],
        "footer": {
            "text": "GitHub Auto Pull Service"
        }
    }

    if isinstance(updates, str):
        embed["description"] = updates
    else:
        for update in updates:
            repo_name = update.split(":")[0].replace("Repository bijgewerkt", "").replace("Nieuwe repository gekloond", "").strip()
            embed["fields"].append({
                "name": "📦 Repository Update",
                "value": update,
                "inline": False
            })
    
    return embed

def send_notification(webhook_url, message, status="success"):
    try:
        embed = create_embed(message, status)
        payload = {"embeds": [embed]}
        response = requests.post(webhook_url, json=payload)
        if response.status_code == 204:
            logging.info("Discord notificatie succesvol verzonden")
        else:
            logging.warning(f"Discord notificatie verzenden gaf status code: {response.status_code}")
    except Exception as e:
        logging.error(f"Fout bij verzenden Discord notificatie: {e}")
