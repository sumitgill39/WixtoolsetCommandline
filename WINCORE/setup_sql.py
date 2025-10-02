"""
WINCORE SQL Database Setup Script
Creates and configures the SQL database for WINCORE JFrog polling system
"""

import pyodbc
import logging
from pathlib import Path
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database configuration
DB_CONFIG = {
    'driver': 'ODBC Driver 17 for SQL Server',
    'server': 'SUMEETGILL7E47\\MSSQLSERVER01',
    'database': 'WINCORE',
    'trusted_connection': 'yes'
}

def create_connection_string():
    """Create the connection string for SQL Server"""
    return (
        f"DRIVER={{{DB_CONFIG['driver']}}};"
        f"SERVER={DB_CONFIG['server']};"
        f"Trusted_Connection={DB_CONFIG['trusted_connection']};"
    )

def create_database():
    """Create the WINCORE database if it doesn't exist"""
    try:
        conn_str = create_connection_string()
        with pyodbc.connect(conn_str, autocommit=True) as conn:
            cursor = conn.cursor()
            
            # Check if database exists
            cursor.execute("""
                IF NOT EXISTS (SELECT name FROM master.sys.databases WHERE name = N'WINCORE')
                BEGIN
                    CREATE DATABASE WINCORE;
                END
            """)
            logger.info("Database check/creation completed successfully")
            
    except Exception as e:
        logger.error(f"Error creating database: {str(e)}")
        raise

def create_tables():
    """Create all required tables for WINCORE"""
    try:
        conn_str = create_connection_string() + f"DATABASE={DB_CONFIG['database']};"
        with pyodbc.connect(conn_str) as conn:
            cursor = conn.cursor()

            # Components table
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[components]') AND type in (N'U'))
                BEGIN
                    CREATE TABLE [dbo].[components] (
                        component_id INT IDENTITY(1,1) PRIMARY KEY,
                        component_name NVARCHAR(255) NOT NULL,
                        component_guid NVARCHAR(50) NOT NULL,
                        repository_url NVARCHAR(500) NOT NULL,
                        polling_enabled BIT DEFAULT 1,
                        polling_frequency_seconds INT DEFAULT 300,
                        last_poll_time DATETIME,
                        created_date DATETIME DEFAULT GETDATE(),
                        created_by NVARCHAR(100),
                        modified_date DATETIME,
                        modified_by NVARCHAR(100)
                    )
                END
            """)

            # Build History table
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[build_history]') AND type in (N'U'))
                BEGIN
                    CREATE TABLE [dbo].[build_history] (
                        build_id INT IDENTITY(1,1) PRIMARY KEY,
                        component_id INT FOREIGN KEY REFERENCES components(component_id),
                        build_number NVARCHAR(50),
                        build_date DATETIME,
                        artifact_path NVARCHAR(500),
                        download_status NVARCHAR(20),
                        download_path NVARCHAR(500),
                        extraction_status NVARCHAR(20),
                        extraction_path NVARCHAR(500),
                        created_date DATETIME DEFAULT GETDATE(),
                        modified_date DATETIME
                    )
                END
            """)

            # Polling Logs table
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[polling_logs]') AND type in (N'U'))
                BEGIN
                    CREATE TABLE [dbo].[polling_logs] (
                        log_id INT IDENTITY(1,1) PRIMARY KEY,
                        component_id INT FOREIGN KEY REFERENCES components(component_id),
                        log_level NVARCHAR(20),
                        message NVARCHAR(MAX),
                        created_date DATETIME DEFAULT GETDATE()
                    )
                END
            """)

            # System Configuration table
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[system_config]') AND type in (N'U'))
                BEGIN
                    CREATE TABLE [dbo].[system_config] (
                        config_id INT IDENTITY(1,1) PRIMARY KEY,
                        config_key NVARCHAR(100) NOT NULL,
                        config_value NVARCHAR(MAX),
                        description NVARCHAR(500),
                        modified_date DATETIME,
                        modified_by NVARCHAR(100)
                    )
                END
            """)

            # Component Threads table
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[component_threads]') AND type in (N'U'))
                BEGIN
                    CREATE TABLE [dbo].[component_threads] (
                        thread_id INT IDENTITY(1,1) PRIMARY KEY,
                        component_id INT FOREIGN KEY REFERENCES components(component_id),
                        thread_status NVARCHAR(20),
                        start_time DATETIME,
                        last_heartbeat DATETIME,
                        created_date DATETIME DEFAULT GETDATE()
                    )
                END
            """)

            conn.commit()
            logger.info("All tables created successfully")

    except Exception as e:
        logger.error(f"Error creating tables: {str(e)}")
        raise

def insert_default_config():
    """Insert default system configuration"""
    try:
        conn_str = create_connection_string() + f"DATABASE={DB_CONFIG['database']};"
        with pyodbc.connect(conn_str) as conn:
            cursor = conn.cursor()

            # Default configuration values
            default_configs = [
                ('JFrogBaseURL', '', 'Base URL for JFrog Artifactory'),
                ('MaxConcurrentThreads', '5', 'Maximum number of concurrent polling threads'),
                ('DefaultPollingFrequency', '300', 'Default polling frequency in seconds'),
                ('MaxBuildsToKeep', '5', 'Maximum number of builds to keep per component'),
                ('LogRetentionDays', '30', 'Number of days to retain polling logs'),
            ]

            for key, value, description in default_configs:
                cursor.execute("""
                    IF NOT EXISTS (SELECT 1 FROM system_config WHERE config_key = ?)
                    INSERT INTO system_config (config_key, config_value, description, modified_date)
                    VALUES (?, ?, ?, GETDATE())
                """, (key, key, value, description))

            conn.commit()
            logger.info("Default configuration inserted successfully")

    except Exception as e:
        logger.error(f"Error inserting default configuration: {str(e)}")
        raise

def main():
    """Main function to set up the database"""
    try:
        logger.info("Starting WINCORE database setup...")
        
        # Create database
        create_database()
        logger.info("Database created/verified successfully")

        # Create tables
        create_tables()
        logger.info("Tables created successfully")

        # Insert default configuration
        insert_default_config()
        logger.info("Default configuration inserted successfully")

        logger.info("WINCORE database setup completed successfully")

    except Exception as e:
        logger.error(f"Database setup failed: {str(e)}")
        raise

if __name__ == "__main__":
    main()