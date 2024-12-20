import requests
import logging
from datetime import datetime
from typing import List, Dict, Union

class DiscordNotificationError(Exception):
    """Base exception for Discord notification errors"""
    pass

class WebhookConnectionError(DiscordNotificationError):
    """Raised when connection to Discord webhook fails"""
    pass

class WebhookResponseError(DiscordNotificationError):
    """Raised when Discord webhook returns an error response"""
    pass

def create_embed(title: str, repository: str, action: str, files: Union[List[str], str], status: str = "success") -> Dict:
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
        "color": colors.get(status, colors["warning"]),
        "timestamp": datetime.utcnow().isoformat(),
        "fields": [
            {
                "name": "📦 Repository",
                "value": repository,
                "inline": False
            },
            {
                "name": "🔄 Actie",
                "value": action,
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
            "value": "\n".join([f.split(": ", 1)[1] for f in files]) if isinstance(files, list) else files,
            "inline": False
        })
    
    return embed

def extract_repo_name(update: str) -> str:
    """Extracts repository name from update message"""
    try:
        return update.split(":")[0].strip()
    except (IndexError, AttributeError) as e:
        logging.error(f"Fout bij extraheren repository naam: {e}")
        return "Onbekende Repository"

def send_notifications(webhook_url: str, updates: List[str]) -> None:
    try:
        if not updates:
            return

        # Extract repository name once
        repo_name = extract_repo_name(updates[0])
        
        # Categorize updates
        update_categories = {
            "added": [],
            "modified": [],
            "deleted": []
        }
        
        for update in updates:
            if "new file" in update.lower():
                update_categories["added"].append(update)
            elif "deleted" in update.lower():
                update_categories["deleted"].append(update)
            else:
                update_categories["modified"].append(update)

        embeds = []
        category_configs = {
            "added": ("✨ Nieuwe Bestanden Toegevoegd", "Toegevoegd", "added"),
            "modified": ("📝 Bestanden Gewijzigd", "Geüpdatet", "modified"),
            "deleted": ("🗑️ Bestanden Verwijderd", "Verwijderd", "deleted")
        }

        for category, files in update_categories.items():
            if files:
                title, action, status = category_configs[category]
                embeds.append(create_embed(title, repo_name, action, files, status))

        if embeds:
            try:
                response = requests.post(webhook_url, json={"embeds": embeds})
                if response.status_code == 204:
                    logging.info(f"Discord notificaties succesvol verzonden voor {repo_name}")
                else:
                    raise WebhookResponseError(f"Discord webhook gaf status code: {response.status_code}")
            except requests.ConnectionError as e:
                raise WebhookConnectionError(f"Kan geen verbinding maken met Discord webhook: {e}")
            except requests.RequestException as e:
                raise DiscordNotificationError(f"Algemene Discord notificatie fout: {e}")
                
    except Exception as e:
        logging.error(f"Kritieke fout bij verzenden Discord notificaties: {str(e)}")
        raise

def send_notification(webhook_url: str, message: str, status: str = "success") -> None:
    """Voor algemene status updates en foutmeldingen"""
    try:
        title = {
            "success": "GitHub Sync Status",
            "warning": "⚠️ GitHub Sync Waarschuwing",
            "error": "❌ GitHub Sync Fout"
        }.get(status, "GitHub Sync Status")

        embed = create_embed(title, "Systeem", status.capitalize(), message, status)
        
        try:
            response = requests.post(webhook_url, json={"embeds": [embed]})
            if response.status_code != 204:
                raise WebhookResponseError(f"Discord webhook gaf status code: {response.status_code}")
        except requests.ConnectionError as e:
            raise WebhookConnectionError(f"Kan geen verbinding maken met Discord webhook: {e}")
        except requests.RequestException as e:
            raise DiscordNotificationError(f"Algemene Discord notificatie fout: {e}")
            
    except Exception as e:
        logging.error(f"Kritieke fout bij verzenden Discord notificatie: {str(e)}")
        raise
