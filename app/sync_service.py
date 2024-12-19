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
        send_notification(config['discord_webhook'], "Synchronisatie service gestart", "success")
        
        while True:
            try:
                # Synchroniseer repositories
                updates = sync_repositories(config['repositories'])
                if updates:
                    # Succesvolle updates
                    send_notification(config['discord_webhook'], updates, "success")
                
                # Check repository bereikbaarheid
                for repo in config['repositories']:
                    if not os.path.exists(repo['local_path']):
                        warning_msg = f"Waarschuwing: Repository {repo['name']} niet bereikbaar"
                        logging.warning(warning_msg)
                        send_notification(config['discord_webhook'], warning_msg, "warning")
                
                # Wacht voor de volgende synchronisatie
                time.sleep(config['sync_interval'])
                
            except Exception as e:
                error_msg = f"Fout tijdens synchronisatie: {str(e)}"
                logging.error(error_msg)
                send_notification(config['discord_webhook'], error_msg, "error")
                time.sleep(30)  # Wacht kort voor nieuwe poging
                
    except Exception as e:
        fatal_error = f"Kritieke fout in synchronisatie service: {str(e)}"
        logging.critical(fatal_error)
        send_notification(config['discord_webhook'], fatal_error, "error")

if __name__ == "__main__":
    monitor_script(main)
