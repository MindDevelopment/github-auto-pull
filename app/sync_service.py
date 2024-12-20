import os
import time
import json
import logging
import subprocess
import sys
from datetime import datetime
from controllers.repo_sync import sync_repositories
from controllers.notifier import send_notification, send_notifications

# Configureer logging met meer details
def setup_logging(log_file):
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    # Voeg ook console logging toe
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    logging.getLogger().addHandler(console_handler)

def check_process_running(process_name):
    """Check of een proces al draait"""
    try:
        output = subprocess.check_output(['tasklist', '/FI', f'WINDOWTITLE eq {process_name}'])
        return process_name.encode() in output
    except subprocess.CalledProcessError:
        return False

def restart_sync_service():
    """Herstart de sync service op een veilige manier"""
    service_name = "sync_service"
    try:
        # Stop bestaande service
        if check_process_running(service_name):
            logging.info("Stopping existing sync service...")
            subprocess.run(['taskkill', '/F', '/IM', 'python.exe', '/FI', f'WINDOWTITLE eq {service_name}'], 
                         check=True)
            time.sleep(2)  # Wacht tot proces volledig gestopt is

        # Start nieuwe service
        logging.info("Starting new sync service instance...")
        subprocess.Popen(['start', 'cmd', '/k', f'python app/sync_service.py'], 
                        shell=True, 
                        creationflags=subprocess.CREATE_NEW_CONSOLE)
        
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Error during service restart: {e}")
        return False

def main():
    try:
        # Laad configuratie
        with open('app/config/config.json') as f:
            config = json.load(f)

        # Setup logging
        setup_logging(config['log_file'])
        
        # Log startup informatie
        logging.info("="*50)
        logging.info("Starting GitHub Auto Pull Service")
        logging.info(f"Configuration loaded: {len(config['repositories'])} repositories configured")
        logging.info(f"Sync interval: {config['sync_interval']} seconds")
        
        # Stuur startup notificatie
        send_notification(config['discord_webhook'], 
                        "Synchronisatie service gestart\n" + 
                        f"Monitoring {len(config['repositories'])} repositories", 
                        "success")
        
        last_sync_time = None
        sync_count = 0
        
        while True:
            try:
                current_time = datetime.now()
                sync_count += 1
                
                # Log sync start
                logging.info(f"Starting sync #{sync_count}")
                if last_sync_time:
                    logging.info(f"Time since last sync: {current_time - last_sync_time}")
                
                # Synchroniseer repositories
                updates = sync_repositories(config['repositories'])
                if updates:
                    logging.info(f"Found {len(updates)} updates")
                    send_notifications(config['discord_webhook'], updates)
                else:
                    logging.info("No updates found")
                
                # Update laatste sync tijd
                last_sync_time = current_time
                
                # Wacht voor volgende synchronisatie
                logging.info(f"Waiting {config['sync_interval']} seconds until next sync")
                time.sleep(config['sync_interval'])
                
            except KeyboardInterrupt:
                logging.info("Received shutdown signal")
                raise
            except Exception as e:
                error_msg = f"Error during sync #{sync_count}: {str(e)}"
                logging.error(error_msg, exc_info=True)  # Include stack trace
                send_notification(config['discord_webhook'], error_msg, "error")
                time.sleep(30)  # Wacht voor nieuwe poging
                
    except KeyboardInterrupt:
        shutdown_msg = "Service shutting down gracefully"
        logging.info(shutdown_msg)
        send_notification(config['discord_webhook'], shutdown_msg, "warning")
    except Exception as e:
        fatal_error = f"Critical error in sync service: {str(e)}"
        logging.critical(fatal_error, exc_info=True)
        send_notification(config['discord_webhook'], fatal_error, "error")
        
    finally:
        logging.info("Service stopped")

if __name__ == "__main__":
    main()
