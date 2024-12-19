import os
import subprocess
import logging

def sync_repositories(repositories):
    updates = []
    for repo in repositories:
        local_path = repo['local_path']
        url = repo['url']
        if not os.path.exists(local_path):
            logging.info(f"Cloning {repo['name']} naar {local_path}")
            subprocess.run(['git', 'clone', url, local_path], check=True)
            updates.append(f"Nieuwe repository gekloond: {repo['name']}")
        else:
            logging.info(f"Pullen voor {repo['name']}")
            result = subprocess.run(['git', '-C', local_path, 'pull'], capture_output=True, text=True)
            if "Already up to date." not in result.stdout:
                updates.append(f"Repository bijgewerkt: {repo['name']}")
    
    return updates
