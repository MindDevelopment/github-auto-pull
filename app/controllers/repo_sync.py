import logging
import subprocess
from contextlib import contextmanager

@contextmanager
def temporary_logging_suspension():
    """Schakel logging tijdelijk uit om file lock issues te voorkomen."""
    handlers = logging.root.handlers[:]
    for handler in handlers:
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
            # Schakel logging tijdelijk uit
            with temporary_logging_suspension():
                subprocess.run(['git', '-C', local_path, 'reset', '--hard'], check=True)
                subprocess.run(['git', '-C', local_path, 'pull'], check=True)
            
            logging.info(f"Repository {repo_name} succesvol gesynchroniseerd.")
            return {"repo_name": repo_name, "status": "success"}
        except subprocess.CalledProcessError as e:
            error_message = f"Git error in {repo_name}: {str(e)}"
            logging.error(error_message)
            raise Exception(error_message)
