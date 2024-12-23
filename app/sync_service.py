import os
import asyncio
import json
import logging
import signal
import aiofiles
from datetime import datetime
from filelock import FileLock
from typing import Dict, Any
from controllers.repo_sync import sync_repositories, GitError
from controllers.notifier import send_notification, send_notifications

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config', 'config.json')

class GracefulExit(SystemExit):
    pass

def signal_handler(signum, frame):
    raise GracefulExit()

def setup_logging(log_file: str) -> None:
    """Configureer logging met rotatie en file lock"""
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    lock = FileLock(log_file + '.lock')
    
    with lock:
        logging.basicConfig(
            handlers=[
                logging.handlers.RotatingFileHandler(
                    log_file, maxBytes=1024*1024, backupCount=5
                ),
                logging.StreamHandler()
            ],
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

def load_config() -> Dict[str, Any]:
    """Laad configuratie met error handling"""
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except FileNotFoundError:
        raise Exception(f"Configuration file not found: {CONFIG_FILE}")
    except json.JSONDecodeError as e:
        raise Exception(f"Invalid JSON in configuration file: {str(e)}")

async def update_sync_status(config: Dict[str, Any], repo_name: str, status: str, error: Exception = None) -> None:
    """Update sync status asynchroon"""
    try:
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

        async with aiofiles.open(CONFIG_FILE, 'w') as f:
            await f.write(json.dumps(config, indent=4))

    except Exception as e:
        logging.error(f"Error updating sync status: {str(e)}")

async def main():
    """Hoofdfunctie voor de sync service met graceful shutdown"""
    config = load_config()
    setup_logging(config['log_file'])
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        logging.info("Starting GitHub Auto Pull Service")
        await send_notification(
            config['discord_webhook'],
            f"Service gestart - Monitoring {len(config['repositories'])} repositories",
            "success"
        )

        while True:
            try:
                result = await sync_repositories(config['repositories'])
                
                if result['status'] == 'error':
                    await send_notification(
                        config['discord_webhook'],
                        f"Sync error: {result.get('error')}",
                        "error"
                    )
                elif result.get('updates'):
                    await send_notifications(config['discord_webhook'], result['updates'])
                
                await asyncio.sleep(config['sync_interval'])

            except GitError as e:
                logging.error(f"Git error: {str(e)}")
                await asyncio.sleep(30)
            except Exception as e:
                logging.error(f"Unexpected error: {str(e)}")
                await asyncio.sleep(30)

    except GracefulExit:
        shutdown_msg = "Service shutting down gracefully"
        logging.info(shutdown_msg)
        await send_notification(config['discord_webhook'], shutdown_msg, "warning")
    except Exception as e:
        fatal_error = f"Critical error in sync service: {str(e)}"
        logging.critical(fatal_error, exc_info=True)
        await send_notification(config['discord_webhook'], fatal_error, "error")
    finally:
        logging.info("Service stopped")
        logging.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
