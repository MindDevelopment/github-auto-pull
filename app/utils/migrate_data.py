import json
from database import DatabaseConnection
import logging

def migrate_existing_data():
    try:
        # Load existing config
        with open('app/config/config.json', 'r') as f:
            config = json.load(f)
        
        db = DatabaseConnection()
        
        # Migrate repositories
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
                    
                    # Last sync time
                    if repo['name'] in status_data.get('last_sync_times', {}):
                        db.update_sync_status(
                            repo_id,
                            'success',
                            None
                        )
                    
                    # Sync errors
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
