from mysql.connector import connect, Error
import logging

def setup_database():
    try:
        # Vervang deze waardes met je eigen database credentials
        connection = connect(
            host="localhost",
            user="your_username",
            password="your_password"
        )
        
        cursor = connection.cursor()
        
        # Create database
        cursor.execute("CREATE DATABASE IF NOT EXISTS github_auto_pull")
        cursor.execute("USE github_auto_pull")
        
        # Create tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS repositories (
                id INT PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(255) NOT NULL UNIQUE,
                url VARCHAR(255) NOT NULL,
                local_path VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_status (
                id INT PRIMARY KEY AUTO_INCREMENT,
                repository_id INT,
                last_sync_time TIMESTAMP,
                status VARCHAR(50),
                FOREIGN KEY (repository_id) REFERENCES repositories(id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_errors (
                id INT PRIMARY KEY AUTO_INCREMENT,
                repository_id INT,
                error_message TEXT,
                error_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (repository_id) REFERENCES repositories(id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_statistics (
                id INT PRIMARY KEY AUTO_INCREMENT,
                repository_id INT,
                total_syncs INT DEFAULT 0,
                successful_syncs INT DEFAULT 0,
                failed_syncs INT DEFAULT 0,
                FOREIGN KEY (repository_id) REFERENCES repositories(id)
            )
        """)
        
        connection.commit()
        logging.info("Database and tables created successfully")
        
    except Error as e:
        logging.error(f"Error setting up database: {e}")
        raise
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

if __name__ == "__main__":
    setup_database()
