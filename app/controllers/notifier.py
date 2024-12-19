import requests
import logging
from datetime import datetime

def create_embed(title, repository, files, status="success"):
    colors = {
        "success": 3066993,  # Groen
        "warning": 16776960,  # Geel
        "error": 15158332,   # Rood
        "added": 3066993,    # Groen
        "modified": 16776960,# Geel
        "deleted": 15158332  # Rood
    }
    
    embed = {
        "title": title,
        "color": colors[status],
        "timestamp": datetime.utcnow().isoformat(),
        "fields": [
            {
                "name": "📦 Repository",
                "value": repository,
                "inline": False
            }
        ],
        "footer": {
            "text": "GitHub Auto Pull Service"
        }
    }

    if files:
        embed["fields"].append({
            "name": "📄 Bestanden",
            "value": "\n".join(files) if isinstance(files, list) else files,
            "inline": False
        })
    
    return embed

def send_notifications(webhook_url, updates):
    try:
        embeds = []
        
        # Sorteer updates per type
        added_files = []
        modified_files = []
        deleted_files = []
        
        for update in updates:
            if "new file" in update.lower():
                added_files.append(update)
            elif "deleted" in update.lower():
                deleted_files.append(update)
            else:
                modified_files.append(update)
        
        # Maak embeds voor elk type update
        if added_files:
            embeds.append(create_embed(
                "✨ Nieuwe Bestanden Toegevoegd",
                added_files[0].split(":")[0],  # Repository naam
                added_files,
                "added"
            ))
            
        if modified_files:
            embeds.append(create_embed(
                "📝 Bestanden Gewijzigd",
                modified_files[0].split(":")[0],  # Repository naam
                modified_files,
                "modified"
            ))
            
        if deleted_files:
            embeds.append(create_embed(
                "🗑️ Bestanden Verwijderd",
                deleted_files[0].split(":")[0],  # Repository naam
                deleted_files,
                "deleted"
            ))
        
        if embeds:
            payload = {"embeds": embeds}
            response = requests.post(webhook_url, json=payload)
            if response.status_code == 204:
                logging.info("Discord notificatie succesvol verzonden")
            else:
                logging.warning(f"Discord notificatie verzenden gaf status code: {response.status_code}")
    except Exception as e:
        logging.error(f"Fout bij verzenden Discord notificatie: {e}")

def send_notification(webhook_url, message, status="success"):
    """Voor algemene status updates en foutmeldingen"""
    try:
        embed = create_embed(
            "GitHub Sync Status" if status == "success" else "⚠️ GitHub Sync Waarschuwing" if status == "warning" else "❌ GitHub Sync Fout",
            "Systeem",
            message,
            status
        )
        payload = {"embeds": [embed]}
        response = requests.post(webhook_url, json=payload)
        if response.status_code == 204:
            logging.info("Discord notificatie succesvol verzonden")
        else:
            logging.warning(f"Discord notificatie verzenden gaf status code: {response.status_code}")
    except Exception as e:
        logging.error(f"Fout bij verzenden Discord notificatie: {e}")
