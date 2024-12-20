import logging
import subprocess
from contextlib import contextmanager
import os
from typing import Dict, List, Union, Optional

@contextmanager
def temporary_logging_suspension():
    """Tijdelijk uitschakelen van logging handlers om file locks te voorkomen."""
    handlers = logging.root.handlers[:]
    for handler in handlers:
        if hasattr(handler, 'close'):
            handler.close()
        logging.root.removeHandler(handler)
    try:
        yield
    finally:
        for handler in handlers:
            logging.root.addHandler(handler)

def execute_git_command(command: List[str], local_path: str) -> str:
    """
    Voer git commando uit met error handling
    
    Returns:
        str: Command output
    Raises:
        subprocess.CalledProcessError: Bij git command fouten
    """
    try:
        result = subprocess.run(
            command,
            cwd=local_path,
            check=True,
            capture_output=True,
            text=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise Exception(f"Git command failed: {e.stderr}")

def get_repository_changes(local_path: str) -> Optional[List[str]]:
    """
    Controleer repository op wijzigingen
    
    Returns:
        Optional[List[str]]: Lijst van gewijzigde files of None bij geen wijzigingen
    """
    try:
        # Get latest commit hash before pull
        before_hash = execute_git_command(['git', 'rev-parse', 'HEAD'], local_path)
        
        # Pull changes
        execute_git_command(['git', 'pull'], local_path)
        
        # Get new commit hash
        after_hash = execute_git_command(['git', 'rev-parse', 'HEAD'], local_path)
        
        # Als er wijzigingen zijn, haal de details op
        if before_hash != after_hash:
            changes = execute_git_command(
                ['git', 'diff', '--name-status', before_hash, after_hash],
                local_path
            )
            return [f"{line.split()[0]}: {line.split()[1]}" for line in changes.splitlines()]
        return None
    except Exception as e:
        raise Exception(f"Failed to get repository changes: {str(e)}")

def sync_repositories(repositories: List[Dict]) -> Dict[str, Union[str, List[str]]]:
    """
    Synchroniseer repositories met verbeterde error handling en status tracking
    
    Returns:
        Dict met status en eventuele updates
    """
    results = {
        'status': 'success',
        'updates': []
    }

    for repo in repositories:
        repo_name = repo['name']
        local_path = repo['local_path']

        logging.info(f"Synchronizing repository: {repo_name}")
        
        try:
            # Controleer of directory bestaat
            if not os.path.exists(local_path):
                raise Exception(f"Repository path does not exist: {local_path}")

            # Reset lokale wijzigingen
            with temporary_logging_suspension():
                execute_git_command(['git', 'reset', '--hard', 'HEAD'], local_path)
                changes = get_repository_changes(local_path)

            if changes:
                results['updates'].extend([f"{repo_name}: {change}" for change in changes])
                logging.info(f"Repository {repo_name} updated successfully")
            else:
                logging.info(f"Repository {repo_name} is already up to date")

        except Exception as e:
            error_msg = f"Failed to sync {repo_name}: {str(e)}"
            logging.error(error_msg)
            results['status'] = 'error'
            results['error'] = error_msg
            break

    return results
