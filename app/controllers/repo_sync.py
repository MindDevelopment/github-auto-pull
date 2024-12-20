import logging
import subprocess
from contextlib import contextmanager
import os

@contextmanager
def temporary_logging_suspension():
    """Schakel logging tijdelijk uit en sluit handlers om file locks te voorkomen."""
    handlers = logging.root.handlers[:]
    for handler in handlers:
        if hasattr(handler, 'close'):
            handler.close()  # Expliciet sluiten van handlers
        logging.root.removeHandler(handler)
    try:
        yield
    finally:
        for handler in handlers:
            logging.root.addHandler(handler)

def sync_repositories(repositories):
    for repo in repositories:
        repo_name = repo['name']
        local_path = repo['local_path']

        logging.info(f"Pullen voor {repo_name}")
        try:
            # Zorg dat alle logging handlers gesloten zijn
            with temporary_logging_suspension():
                # Wacht kort om er zeker van te zijn dat bestanden zijn vrijgegeven
                import time
                time.sleep(1)
                
                # Voer git commando's uit
                subprocess.run(['git', '-C', local_path, 'reset', '--hard'], 
                             check=True, 
                             stderr=subprocess.PIPE)
                subprocess.run(['git', '-C', local_path, 'pull'], 
                             check=True,
                             stderr=subprocess.PIPE)
            
            logging.info(f"Repository {repo_name} succesvol gesynchroniseerd.")
            return {"repo_name": repo_name, "status": "success"}
        except subprocess.CalledProcessError as e:
            error_message = f"Git error in {repo_name}: {str(e)}"
            logging.error(error_message)
            raise Exception(error_message)
