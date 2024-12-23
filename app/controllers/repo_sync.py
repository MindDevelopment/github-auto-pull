import asyncio
import logging
import subprocess
from contextlib import contextmanager
import os
from typing import Dict, List, Union, Optional
from concurrent.futures import ThreadPoolExecutor

class GitError(Exception):
    """Custom exception voor git-gerelateerde fouten"""
    pass

@contextmanager
def temporary_logging_suspension():
    """Tijdelijk uitschakelen van logging handlers om file locks te voorkomen."""
    handlers = logging.root.handlers[:]
    for handler in handlers:
        logging.root.removeHandler(handler)
    try:
        yield
    finally:
        for handler in handlers:
            logging.root.addHandler(handler)

async def execute_git_command(command: List[str], local_path: str) -> str:
    """
    Voer git commando asynchroon uit met verbeterde error handling
    """
    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=local_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise GitError(f"Git command failed: {stderr.decode()}")
            
        return stdout.decode().strip()
    except Exception as e:
        raise GitError(f"Error executing git command: {str(e)}")

async def get_repository_changes(local_path: str) -> Optional[List[str]]:
    """
    Controleer repository op wijzigingen asynchroon
    """
    try:
        # Get latest commit hash before pull
        before_hash = await execute_git_command(['git', 'rev-parse', 'HEAD'], local_path)
        
        # Pull changes
        await execute_git_command(['git', 'pull'], local_path)
        
        # Get new commit hash
        after_hash = await execute_git_command(['git', 'rev-parse', 'HEAD'], local_path)
        
        if before_hash != after_hash:
            changes = await execute_git_command(
                ['git', 'diff', '--name-status', before_hash, after_hash],
                local_path
            )
            return [f"{line.split()[0]}: {line.split()[1]}" for line in changes.splitlines()]
        return None
    except GitError as e:
        logging.error(f"Git error in repository {local_path}: {str(e)}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error in repository {local_path}: {str(e)}")
        raise

async def sync_repositories(repositories: List[Dict]) -> Dict[str, Union[str, List[str]]]:
    """
    Synchroniseer repositories asynchroon met rate limiting
    """
    results = {
        'status': 'success',
        'updates': []
    }
    
    # Rate limiting semaphore
    semaphore = asyncio.Semaphore(3)  # Max 3 concurrent syncs
    
    async def sync_single_repo(repo):
        async with semaphore:
            try:
                repo_name = repo['name']
                local_path = repo['local_path']
                
                if not os.path.exists(local_path):
                    raise GitError(f"Repository path does not exist: {local_path}")

                with temporary_logging_suspension():
                    await execute_git_command(['git', 'reset', '--hard', 'HEAD'], local_path)
                    changes = await get_repository_changes(local_path)

                if changes:
                    return [f"{repo_name}: {change}" for change in changes]
                return []

            except Exception as e:
                logging.error(f"Failed to sync {repo['name']}: {str(e)}")
                raise

    try:
        # Gebruik asyncio.gather voor parallelle uitvoering
        tasks = [sync_single_repo(repo) for repo in repositories]
        repo_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in repo_results:
            if isinstance(result, Exception):
                results['status'] = 'error'
                results['error'] = str(result)
                break
            elif result:
                results['updates'].extend(result)
                
        return results

    except Exception as e:
        results['status'] = 'error'
        results['error'] = str(e)
        return results
