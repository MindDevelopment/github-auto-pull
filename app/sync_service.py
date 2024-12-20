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

# Aan het begin van sync_service.py toevoegen
os.makedirs('logs', exist_ok=True)

# Absoluut pad naar de configuratie
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config', 'config.json')

# Configureer logging met meer details
def setup_logging(log_file):
    log_dir = os.path.dirname(log_file)
    os.makedirs(log_dir, exist_ok=True)

    lock_file = log_file + '.lock'
    lock = FileLock(lock_file)

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

def save_config(config):
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
        restart_sync_service()
    except Exception as e:
        raise Exception(f"Fout bij opslaan configuratie: {str(e)}")

def check_process_running(process_name):
    try:
        output = subprocess.check_output(['tasklist', '/FI', f'IMAGENAME eq {process_name}'])
        return process_name.encode() in output
    except subprocess.CalledProcessError:
        return False

def restart_sync_service():
    service_name = "python.exe"
    try:
        if check_process_running(service_name):
            logging.info("Stopping existing sync service...")
            subprocess.run(['taskkill', '/F', '/IM', service_name], check=True)
            time.sleep(2)

        logging.info("Starting new sync service instance...")
        subprocess.Popen(
            ['cmd.exe', '/c', 'start', 'python', 'app/sync_service.py'],
            shell=True,
            stdout=subprocess.DEVNULL,  # Schakel logging uit voor subprocess
            stderr=subprocess.DEVNULL
        )
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Error during service restart: {e}")
        return False

def update_sync_status(repo_name, status, error=None):
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

    if error:
        config['sync_status']['sync_errors'].setdefault(repo_name, []).append({
            'time': current_time,
            'error': str(error)
        })

    repo_stats = config['sync_status']['sync_statistics'].setdefault(repo_name, {
        'total_syncs': 0,
        'successful_syncs': 0,
        'failed_syncs': 0
    })

    repo_stats['total_syncs'] += 1
    if error:
        repo_stats['failed_syncs'] += 1
    else:
        repo_stats['successful_syncs'] += 1

    save_config(config)

def main():
    try:
        with open(CONFIG_FILE) as f:
            config = json.load(f)

        setup_logging(config['log_file'])

        logging.info("=" * 50)
        logging.info("Starting GitHub Auto Pull Service")
        logging.info(f"Configuration loaded: {len(config['repositories'])} repositories configured")
        logging.info(f"Sync interval: {config['sync_interval']} seconds")

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

                logging.info(f"Starting sync #{sync_count}")
                if last_sync_time:
                    logging.info(f"Time since last sync: {current_time - last_sync_time}")

                for repo in config['repositories']:
                    try:
                        updates = sync_repositories([repo])
                        if updates:
                            update_sync_status(repo['name'], 'success')
                            send_notifications(config['discord_webhook'], updates)
                        else:
                            update_sync_status(repo['name'], 'success')
                            logging.info(f"No updates for {repo['name']}")
                    except Exception as repo_error:
                        error_msg = f"Error syncing {repo['name']}: {str(repo_error)}"
                        logging.error(error_msg)
                        update_sync_status(repo['name'], 'error', repo_error)
                        send_notification(config['discord_webhook'], error_msg, "error")
                last_sync_time = current_time

                logging.info(f"Waiting {config['sync_interval']} seconds until next sync")
                time.sleep(config['sync_interval'])

            except KeyboardInterrupt:
                logging.info("Received shutdown signal")
                raise
            except Exception as e:
                logging.error(f"Error during sync #{sync_count}: {str(e)}", exc_info=True)
                time.sleep(30)

    except KeyboardInterrupt:
        shutdown_msg = "Service shutting down gracefully"
        logging.info(shutdown_msg)
        send_notification(config['discord_webhook'], shutdown_msg, "warning")
    except Exception as e:
        fatal_error = f"Critical error in sync service: {str(e)}"
        logging.critical(fatal_error, exc_info=True)
        send_notification(config['discord_webhook'], fatal_error, "error")

    finally:
        logging.shutdown()  # Zorg ervoor dat logging correct wordt afgesloten
        logging.info("Service stopped")

if __name__ == "__main__":
    main()