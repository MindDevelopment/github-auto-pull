import os
import time
import json
import logging
import subprocess
import sys
from datetime import datetime
from filelock import FileLock
from controllers.repo_sync import sync_repositories
from controllers.notifier import send_notification, send_notifications

# Configuratie constanten
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config', 'config.json')

def setup_logging(log_file):
    """Configureer logging met file lock om conflicten te voorkomen"""
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    lock = FileLock(log_file + '.lock')
    
    with lock:
        for handler in logging.root.handlers[:]:
            if hasattr(handler, 'close'):
                handler.close()
            logging.root.removeHandler(handler)

        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        logging.getLogger().addHandler(console_handler)

def save_config(config, restart=False):
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        raise Exception(f"Fout bij opslaan configuratie: {str(e)}")

def update_sync_status(repo_name, status, error=None):
    """Update sync status voor een repository"""
    try:
        with open(CONFIG_FILE) as f:
            config = json.load(f)
    except FileNotFoundError:
        config = {}

    config.setdefault('sync_status', {
        'last_sync_times': {},
        'sync_errors': {},
        'sync_statistics': {}
    })

    current_time = datetime.now().isoformat()
    config['sync_status']['last_sync_times'][repo_name] = current_time

    # Update error log indien nodig
    if error:
        config['sync_status']['sync_errors'].setdefault(repo_name, []).append({
            'time': current_time,
            'error': str(error)
        })

    # Update statistieken
    stats = config['sync_status']['sync_statistics'].setdefault(repo_name, {
        'total_syncs': 0,
        'successful_syncs': 0,
        'failed_syncs': 0
    })

    stats['total_syncs'] += 1
    if error:
        stats['failed_syncs'] += 1
    else:
        stats['successful_syncs'] += 1

    save_config(config, restart=False)

def sync_repository(repo, config):
    """Synchroniseer een enkele repository"""
    try:
        result = sync_repositories([repo])
        
        # Als we een dictionary terugkrijgen met updates
        if isinstance(result, dict):
            if result.get('status') == 'error':
                # Bij een error in de sync
                error_msg = result.get('error', 'Unknown error during sync')
                logging.error(error_msg)
                update_sync_status(repo['name'], 'error', error_msg)
                send_notification(config['discord_webhook'], error_msg, "error")
            elif result.get('updates'):
                # Bij succesvolle updates
                update_sync_status(repo['name'], 'success')
                send_notifications(config['discord_webhook'], result['updates'])
            else:
                # Bij succes maar geen updates
                update_sync_status(repo['name'], 'success')
                logging.info(f"No updates for {repo['name']}")
        else:
            # Bij onverwacht resultaat formaat
            error_msg = f"Unexpected sync result format for {repo['name']}"
            logging.error(error_msg)
            update_sync_status(repo['name'], 'error', error_msg)
            send_notification(config['discord_webhook'], error_msg, "error")
            
    except Exception as e:
        error_msg = f"Error syncing {repo['name']}: {str(e)}"
        logging.error(error_msg)
        update_sync_status(repo['name'], 'error', e)
        send_notification(config['discord_webhook'], error_msg, "error")

def main():
    """Hoofdfunctie voor de sync service"""
    os.makedirs('logs', exist_ok=True)
    
    try:
        with open(CONFIG_FILE) as f:
            config = json.load(f)

        setup_logging(config['log_file'])
        
        logging.info("=" * 50)
        logging.info("Starting GitHub Auto Pull Service")
        logging.info(f"Configuration loaded: {len(config['repositories'])} repositories")
        
        send_notification(
            config['discord_webhook'],
            f"Service gestart - Monitoring {len(config['repositories'])} repositories",
            "success"
        )

        sync_count = 0
        last_sync_time = None

        while True:
            try:
                current_time = datetime.now()
                sync_count += 1
                
                logging.info(f"Starting sync #{sync_count}")
                if last_sync_time:
                    logging.info(f"Time since last sync: {current_time - last_sync_time}")

                # Synchroniseer alle repositories
                for repo in config['repositories']:
                    sync_repository(repo, config)

                last_sync_time = current_time
                logging.info(f"Waiting {config['sync_interval']} seconds until next sync")
                time.sleep(config['sync_interval'])

            except KeyboardInterrupt:
                raise
            except Exception as e:
                logging.error(f"Error during sync #{sync_count}: {str(e)}", exc_info=True)
                time.sleep(30)  # Wacht bij error voordat we opnieuw proberen

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
        logging.shutdown()

if __name__ == "__main__":
    main()
