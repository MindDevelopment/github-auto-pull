import time
import json
import logging
from controllers.repo_sync import sync_repositories
from controllers.notifier import send_notification
from utils.auto_restart import monitor_script

# Laad configuratie
with open('app/config/config.json') as f:
    config = json.load(f)

# Logging instellen
logging.basicConfig(filename=config['log_file'], level=logging.INFO)

def main():
    try:
        logging.info("Synchronisatie gestart.")
        while True:
            # Synchroniseer repositories
            updates = sync_repositories(config['repositories'])
            if updates:
                send_notification(config['discord_webhook'], updates)
            
            # Wacht voor de volgende synchronisatie
            time.sleep(config['sync_interval'])
    except Exception as e:
        logging.error(f"Fout in synchronisatie: {e}")
        send_notification(config['discord_webhook'], f"Fout: {e}")

if __name__ == "__main__":
    monitor_script(main)
