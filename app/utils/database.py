import mysql.connector
from mysql.connector import Error
from contextlib import contextmanager
import logging
from datetime import datetime

class DatabaseConnection:
    def __init__(self, host, user, password, database):
        self.config = {
            'host': host,
            'user': user,
            'password': password,
            'database': database
        }

    @contextmanager
    def get_cursor(self):
        connection = None
        try:
            connection = mysql.connector.connect(**self.config)
            cursor = connection.cursor(dictionary=True)
            yield cursor
            connection.commit()
        except Error as e:
            if connection:
                connection.rollback()
            logging.error(f"Database error: {str(e)}")
            raise
        finally:
            if connection and connection.is_connected():
                cursor.close()
                connection.close()

    def add_repository(self, name, url, local_path):
        with self.get_cursor() as cursor:
            sql = """INSERT INTO repositories (name, url, local_path)
                    VALUES (%s, %s, %s)"""
            cursor.execute(sql, (name, url, local_path))
            return cursor.lastrowid

    def get_all_repositories(self):
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT r.*, 
                       ss.last_sync_time,
                       ss.status as sync_status,
                       st.total_syncs,
                       st.successful_syncs,
                       st.failed_syncs
                FROM repositories r
                LEFT JOIN sync_status ss ON r.id = ss.repository_id
                LEFT JOIN sync_statistics st ON r.id = st.repository_id
                ORDER BY r.created_at DESC
            """)
            return cursor.fetchall()

    def delete_repository(self, repo_id):
        with self.get_cursor() as cursor:
            # Delete related records first
            cursor.execute("DELETE FROM sync_errors WHERE repository_id = %s", (repo_id,))
            cursor.execute("DELETE FROM sync_status WHERE repository_id = %s", (repo_id,))
            cursor.execute("DELETE FROM sync_statistics WHERE repository_id = %s", (repo_id,))
            cursor.execute("DELETE FROM repositories WHERE id = %s", (repo_id,))

    def update_sync_status(self, repo_id, status, error=None):
        with self.get_cursor() as cursor:
            # Update sync_status
            cursor.execute("""
                INSERT INTO sync_status (repository_id, status, last_sync_time)
                VALUES (%s, %s, NOW())
            """, (repo_id, status))
            
            if error:
                cursor.execute("""
                    INSERT INTO sync_errors (repository_id, error_message)
                    VALUES (%s, %s)
                """, (repo_id, str(error)))

            # Update statistics
            cursor.execute("""
                INSERT INTO sync_statistics (repository_id, total_syncs, 
                    successful_syncs, failed_syncs)
                VALUES (%s, 1, %s, %s)
                ON DUPLICATE KEY UPDATE
                    total_syncs = total_syncs + 1,
                    successful_syncs = successful_syncs + %s,
                    failed_syncs = failed_syncs + %s
            """, (repo_id, 1 if not error else 0, 1 if error else 0,
                  1 if not error else 0, 1 if error else 0))
