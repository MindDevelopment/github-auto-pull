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
            updates.append(f"{repo['name']}: Nieuwe repository gekloond")
        else:
            logging.info(f"Pullen voor {repo['name']}")
            # Haal eerst de huidige status op
            subprocess.run(['git', '-C', local_path, 'fetch'], check=True)
            result = subprocess.run(['git', '-C', local_path, 'diff', '--name-status', 'HEAD..origin/main'], 
                                 capture_output=True, text=True)
            
            if result.stdout.strip():
                # Voer de pull uit
                subprocess.run(['git', '-C', local_path, 'pull'], check=True)
                
                # Verwerk de veranderingen
                for line in result.stdout.splitlines():
                    status, file = line.split('\t', 1)
                    if status == 'A':
                        updates.append(f"{repo['name']}: New file {file}")
                    elif status == 'M':
                        updates.append(f"{repo['name']}: Modified {file}")
                    elif status == 'D':
                        updates.append(f"{repo['name']}: Deleted {file}")
    
    return updates

