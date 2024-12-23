import json
import logging
from dotenv import load_dotenv
import os
from database import DatabaseConnection

def migrate_existing_data():
    try:
        # Load environment variables
        load_dotenv()
        
        # Load existing config
        with open('app/config/config.json', 'r') as f:
            config = json.load(f)
        
        # Correct database initialization
        db = DatabaseConnection(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME', 'github_auto_pull')
        )
        
        # Rest van je code blijft hetzelfde
        for repo in config['repositories']:
            try:
                repo_id = db.add_repository(
                    repo['name'],
                    repo['url'],
                    repo['local_path']
                )
                
                # Migrate sync status
                if 'sync_status' in config:
                    status_data = config['sync_status']
                    
                    if repo['name'] in status_data.get('last_sync_times', {}):
                        db.update_sync_status(
                            repo_id,
                            'success',
                            None
                        )
                    
                    if repo['name'] in status_data.get('sync_errors', {}):
                        for error in status_data['sync_errors'][repo['name']]:
                            db.update_sync_status(
                                repo_id,
                                'error',
                                error['error']
                            )
                    
                logging.info(f"Migrated repository: {repo['name']}")
                
            except Exception as e:
                logging.error(f"Error migrating repository {repo['name']}: {e}")
                continue
                
        logging.info("Data migration completed")
        
    except Exception as e:
        logging.error(f"Migration failed: {e}")
        raise

if __name__ == "__main__":
    migrate_existing_data()
