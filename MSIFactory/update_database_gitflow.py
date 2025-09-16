#!/usr/bin/env python3
"""
Update database schema for GitFlow branch tracking and artifact polling
"""

import pyodbc
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_database_schema():
    """Update database schema for GitFlow support"""
    try:
        conn_str = (
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=SUMEETGILL7E47\\MSSQLSERVER01;"
            "DATABASE=MSIFactory;"
            "Trusted_Connection=yes;"
        )
        
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        # Check and add columns to components table
        columns_to_add = [
            ('branch_name', 'VARCHAR(100)'),
            ('polling_enabled', 'BIT DEFAULT 1'),
            ('last_poll_time', 'DATETIME'),
            ('last_artifact_version', 'VARCHAR(100)'),
            ('last_download_path', 'VARCHAR(500)'),
            ('last_extract_path', 'VARCHAR(500)'),
            ('last_artifact_time', 'DATETIME')
        ]
        
        for column_name, column_type in columns_to_add:
            try:
                cursor.execute(f"""
                    IF NOT EXISTS (SELECT * FROM sys.columns 
                                  WHERE object_id = OBJECT_ID('components') 
                                  AND name = '{column_name}')
                    BEGIN
                        ALTER TABLE components ADD {column_name} {column_type}
                    END
                """)
                logger.info(f"Added/verified column: {column_name}")
            except Exception as e:
                logger.warning(f"Column {column_name} might already exist: {e}")
        
        # Check if component_guid exists, if not add it
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sys.columns 
                          WHERE object_id = OBJECT_ID('components') 
                          AND name = 'component_guid')
            BEGIN
                ALTER TABLE components ADD component_guid VARCHAR(50)
            END
        """)
        
        # Create artifact history table
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'artifact_history')
            BEGIN
                CREATE TABLE artifact_history (
                    history_id INT IDENTITY(1,1) PRIMARY KEY,
                    component_id INT,
                    artifact_version VARCHAR(100),
                    download_path VARCHAR(500),
                    extract_path VARCHAR(500),
                    download_time DATETIME,
                    branch_name VARCHAR(100),
                    artifact_size BIGINT,
                    artifact_hash VARCHAR(100),
                    FOREIGN KEY (component_id) REFERENCES components(component_id)
                )
                CREATE INDEX idx_artifact_history_component ON artifact_history(component_id)
                CREATE INDEX idx_artifact_history_time ON artifact_history(download_time)
            END
        """)
        logger.info("Created/verified artifact_history table")
        
        # Create MSI build queue table
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'msi_build_queue')
            BEGIN
                CREATE TABLE msi_build_queue (
                    queue_id INT IDENTITY(1,1) PRIMARY KEY,
                    component_id INT,
                    project_id INT,
                    source_path VARCHAR(500),
                    status VARCHAR(50),
                    queued_time DATETIME,
                    start_time DATETIME,
                    end_time DATETIME,
                    error_message TEXT,
                    msi_output_path VARCHAR(500),
                    build_log TEXT,
                    priority INT DEFAULT 5,
                    FOREIGN KEY (component_id) REFERENCES components(component_id),
                    FOREIGN KEY (project_id) REFERENCES projects(project_id)
                )
                CREATE INDEX idx_build_queue_status ON msi_build_queue(status)
                CREATE INDEX idx_build_queue_time ON msi_build_queue(queued_time)
            END
        """)
        logger.info("Created/verified msi_build_queue table")
        
        # Create polling configuration table
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'polling_config')
            BEGIN
                CREATE TABLE polling_config (
                    config_id INT IDENTITY(1,1) PRIMARY KEY,
                    component_id INT UNIQUE,
                    jfrog_repository VARCHAR(200),
                    artifact_path_pattern VARCHAR(500),
                    polling_interval_seconds INT DEFAULT 60,
                    enabled BIT DEFAULT 1,
                    last_successful_poll DATETIME,
                    consecutive_failures INT DEFAULT 0,
                    max_retries INT DEFAULT 3,
                    created_date DATETIME DEFAULT GETDATE(),
                    updated_date DATETIME DEFAULT GETDATE(),
                    FOREIGN KEY (component_id) REFERENCES components(component_id)
                )
            END
        """)
        logger.info("Created/verified polling_config table")
        
        # Create branch mapping table for GitFlow
        cursor.execute("""
            IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'branch_mappings')
            BEGIN
                CREATE TABLE branch_mappings (
                    mapping_id INT IDENTITY(1,1) PRIMARY KEY,
                    project_id INT,
                    branch_pattern VARCHAR(100),
                    repository_path VARCHAR(200),
                    environment_type VARCHAR(50), -- dev, qa, staging, prod
                    auto_deploy BIT DEFAULT 0,
                    created_date DATETIME DEFAULT GETDATE(),
                    FOREIGN KEY (project_id) REFERENCES projects(project_id)
                )
                
                -- Insert default GitFlow patterns
                INSERT INTO branch_mappings (project_id, branch_pattern, repository_path, environment_type, auto_deploy)
                VALUES 
                    (NULL, 'develop', '/snapshots/develop', 'dev', 1),
                    (NULL, 'master', '/releases/stable', 'prod', 0),
                    (NULL, 'main', '/releases/stable', 'prod', 0),
                    (NULL, 'feature/*', '/feature-builds', 'dev', 1),
                    (NULL, 'release/*', '/release-candidates', 'staging', 1),
                    (NULL, 'hotfix/*', '/hotfixes', 'prod', 0)
            END
        """)
        logger.info("Created/verified branch_mappings table with defaults")
        
        # Add sample data for testing
        cursor.execute("""
            -- Update a sample component with branch info for testing
            UPDATE TOP(1) components 
            SET branch_name = 'develop',
                polling_enabled = 1
            WHERE branch_name IS NULL
        """)
        
        conn.commit()
        conn.close()
        
        logger.info("Database schema updated successfully for GitFlow support!")
        
        # Print summary
        print("\n" + "="*60)
        print("DATABASE SCHEMA UPDATE COMPLETE")
        print("="*60)
        print("\nNew Tables Created:")
        print("  - artifact_history: Tracks all downloaded artifacts")
        print("  - msi_build_queue: Queue for MSI build tasks")
        print("  - polling_config: Component-specific polling settings")
        print("  - branch_mappings: GitFlow branch to repository mappings")
        print("\nUpdated Tables:")
        print("  - components: Added branch tracking and polling fields")
        print("\nGitFlow Branch Patterns Configured:")
        print("  - develop -> /snapshots/develop")
        print("  - master/main -> /releases/stable")
        print("  - feature/* -> /feature-builds")
        print("  - release/* -> /release-candidates")
        print("  - hotfix/* -> /hotfixes")
        print("="*60)
        
    except Exception as e:
        logger.error(f"Error updating database schema: {e}")
        raise

if __name__ == "__main__":
    update_database_schema()