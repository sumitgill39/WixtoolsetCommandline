"""
Database Helper Module for JFrog Polling System
Handles all database operations with MS SQL Server
"""

import pyodbc
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import logging
from config import DB_CONFIG

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseHelper:
    """Database helper class for JFrog polling system operations"""

    def __init__(self):
        """Initialize database connection parameters"""
        # Use the working connection string format
        self.connection_string = r'DRIVER={ODBC Driver 17 for SQL Server};SERVER=SUMEETGILL7E47\MSSQLSERVER01;DATABASE=MSIFactory;Trusted_Connection=yes'
        self.connection = None

    def get_connection_string(self) -> str:
        """Return the connection string for SQL Server"""
        return self.connection_string

    def execute_query(self, query: str, params: tuple = None) -> Optional[List[Dict]]:
        """Execute a query and return results as list of dictionaries"""
        try:
            cursor = self.connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            # If the query returns results
            if cursor.description:
                columns = [column[0] for column in cursor.description]
                results = []
                for row in cursor.fetchall():
                    results.append(dict(zip(columns, row)))
                return results
            
            return None

        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}")
            raise

    def get_ssp_config(self) -> Tuple[Optional[str], Optional[str]]:
        """Get SSP API configuration"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT TOP 1 [api_url], [api_token]
                FROM [ssp_config]
                ORDER BY [config_id] DESC
            """)
            row = cursor.fetchone()
            if row:
                return row.api_url, row.api_token
            return None, None
        except Exception as e:
            logger.error(f"Error getting SSP config: {str(e)}")
            return None, None

    def update_ssp_config(self, api_url: str, api_token: Optional[str] = None) -> bool:
        """Update SSP API configuration"""
        try:
            cursor = self.connection.cursor()
            
            # If token is not provided, only update URL
            if api_token:
                cursor.execute("""
                    INSERT INTO [ssp_config] ([api_url], [api_token])
                    VALUES (?, ?)
                """, (api_url, api_token))
            else:
                # Get existing token
                _, existing_token = self.get_ssp_config()
                if existing_token:
                    cursor.execute("""
                        INSERT INTO [ssp_config] ([api_url], [api_token])
                        VALUES (?, ?)
                    """, (api_url, existing_token))
                else:
                    return False

            self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating SSP config: {str(e)}")
            return False

    def get_component_info(self, component_id: int) -> Optional[Dict]:
        """Get component and project information"""
        try:
            cursor = self.connection.cursor()
            query = """
                SELECT 
                    c.component_id,
                    c.component_name,
                    c.polling_enabled,
                    p.project_key,
                    p.project_name,
                    (SELECT TOP 1 branch_name 
                     FROM component_branches 
                     WHERE component_id = c.component_id) as default_branch
                FROM components c
                INNER JOIN projects p ON c.project_id = p.project_id
                WHERE c.component_id = ? AND c.is_enabled = 1
            """
            cursor.execute(query, (component_id,))
            
            row = cursor.fetchone()
            if row:
                return {
                    'component_id': row.component_id,
                    'component_name': row.component_name,
                    'project_key': row.project_key,
                    'project_name': row.project_name,
                    'default_branch': row.default_branch or 'main',
                    'polling_enabled': row.polling_enabled
                }
            return None
        except Exception as e:
            logger.error(f"Error getting component info: {str(e)}")
            return None

    def get_branch_pattern(self, component_id: int, branch: str = None) -> Optional[str]:
        """Get URL pattern for component/branch"""
        try:
            cursor = self.connection.cursor()
            if branch:
                query = """
                    SELECT path_pattern_override
                    FROM component_branches
                    WHERE component_id = ? AND branch_name = ?
                """
                cursor.execute(query, (component_id, branch))
            else:
                query = """
                    SELECT TOP 1 path_pattern_override
                    FROM component_branches
                    WHERE component_id = ?
                """
                cursor.execute(query, (component_id,))
            
            row = cursor.fetchone()
            return row.path_pattern_override if row else None
        except Exception as e:
            logger.error(f"Error getting branch pattern: {str(e)}")
            return None

    def get_latest_build_number(self, component_id: int) -> Optional[int]:
        """Get latest build number for component"""
        try:
            cursor = self.connection.cursor()
            query = """
                SELECT TOP 1 build_number
                FROM jfrog_build_tracking
                WHERE component_id = ?
                ORDER BY build_number DESC
            """
            cursor.execute(query, (component_id,))
            
            row = cursor.fetchone()
            return int(row.build_number) if row else None
        except Exception as e:
            logger.error(f"Error getting latest build number: {str(e)}")
            return None

    def get_system_config(self, key: str) -> Optional[str]:
        """Get system configuration value by key"""
        try:
            cursor = self.connection.cursor()
            query = """
                SELECT config_value
                FROM jfrog_system_config
                WHERE config_key = ? AND is_enabled = 1
            """
            cursor.execute(query, (key,))
            
            row = cursor.fetchone()
            return row.config_value if row else None
        except Exception as e:
            logger.error(f"Error getting system config: {str(e)}")
            return None
        """Update SSP API configuration"""
        try:
            cursor = self.connection.cursor()
            
            # If token is not provided, only update URL
            if api_token:
                cursor.execute("""
                    INSERT INTO [ssp_config] ([api_url], [api_token])
                    VALUES (?, ?)
                """, (api_url, api_token))
            else:
                # Get existing token
                _, existing_token = self.get_ssp_config()
                if existing_token:
                    cursor.execute("""
                        INSERT INTO [ssp_config] ([api_url], [api_token])
                        VALUES (?, ?)
                    """, (api_url, existing_token))
                else:
                    return False

            self.connection.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating SSP config: {str(e)}")
            return False

    def connect(self) -> bool:
        """Establish database connection"""
        try:
            self.connection = pyodbc.connect(self.get_connection_string())
            logger.info("Database connection established successfully")
            return True
        except Exception as e:
            logger.error(f"Database connection failed: {str(e)}")
            return False

    def disconnect(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")

    def execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        """Execute SELECT query and return results as list of dictionaries"""
        try:
            cursor = self.connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            # Get column names
            columns = [column[0] for column in cursor.description]

            # Fetch all rows and convert to list of dictionaries
            results = []
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))

            cursor.close()
            return results

        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}")
            return []

    def execute_non_query(self, query: str, params: tuple = None) -> bool:
        """Execute INSERT, UPDATE, DELETE query"""
        try:
            cursor = self.connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            self.connection.commit()
            cursor.close()
            return True

        except Exception as e:
            logger.error(f"Non-query execution failed: {str(e)}")
            self.connection.rollback()
            return False

    def get_active_polling_config(self) -> List[Dict]:
        """Get all active polling configurations"""
        query = "EXEC sp_GetActivePollingConfig"
        return self.execute_query(query)

    def get_system_config(self, config_key: str) -> Optional[str]:
        """Get system configuration value by key"""
        query = """
            SELECT config_value
            FROM jfrog_system_config
            WHERE config_key = ? AND is_enabled = 1
        """
        results = self.execute_query(query, (config_key,))
        if results:
            return results[0]['config_value']
        return None

    def update_system_config(self, config_key: str, config_value: str, updated_by: str = 'system') -> bool:
        """Update system configuration"""
        query = """
            UPDATE jfrog_system_config
            SET config_value = ?, updated_date = GETDATE(), updated_by = ?
            WHERE config_key = ?
        """
        return self.execute_non_query(query, (config_value, updated_by, config_key))

    def get_build_tracking(self, component_id: int, branch_id: int) -> Optional[Dict]:
        """Get build tracking information for a component/branch"""
        query = """
            SELECT * FROM jfrog_build_tracking
            WHERE component_id = ? AND branch_id = ?
        """
        results = self.execute_query(query, (component_id, branch_id))
        if results:
            return results[0]
        return None

    def update_build_tracking(self, component_id: int, branch_id: int, build_date: str,
                             build_number: int, build_url: str, download_status: str = 'pending',
                             extraction_status: str = 'pending') -> bool:
        """Update or insert build tracking record"""
        query = """
            EXEC sp_UpdateBuildTracking
                @component_id = ?,
                @branch_id = ?,
                @build_date = ?,
                @build_number = ?,
                @build_url = ?,
                @download_status = ?,
                @extraction_status = ?
        """
        params = (component_id, branch_id, build_date, build_number, build_url,
                 download_status, extraction_status)
        return self.execute_non_query(query, params)

    def update_download_status(self, component_id: int, branch_id: int,
                               download_path: str, file_size: int,
                               checksum: str = None) -> bool:
        """Update download status after successful download"""
        query = """
            UPDATE jfrog_build_tracking
            SET download_status = 'completed',
                last_downloaded_time = GETDATE(),
                download_path = ?,
                file_size = ?,
                checksum = ?,
                updated_date = GETDATE()
            WHERE component_id = ? AND branch_id = ?
        """
        return self.execute_non_query(query, (download_path, file_size, checksum,
                                              component_id, branch_id))

    def update_extraction_status(self, component_id: int, branch_id: int,
                                 extraction_path: str) -> bool:
        """Update extraction status after successful extraction"""
        query = """
            UPDATE jfrog_build_tracking
            SET extraction_status = 'completed',
                extraction_path = ?,
                updated_date = GETDATE()
            WHERE component_id = ? AND branch_id = ?
        """
        return self.execute_non_query(query, (extraction_path, component_id, branch_id))

    def insert_build_history(self, component_id: int, branch_id: int, build_date: str,
                            build_number: int, build_url: str, download_path: str = None,
                            extraction_path: str = None, file_size: int = None,
                            checksum: str = None) -> bool:
        """Insert new build into history"""
        query = """
            INSERT INTO jfrog_build_history
            (component_id, branch_id, build_date, build_number, build_url,
             download_path, extraction_path, file_size, checksum,
             downloaded_time, extracted_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE(), GETDATE())
        """
        params = (component_id, branch_id, build_date, build_number, build_url,
                 download_path, extraction_path, file_size, checksum)
        return self.execute_non_query(query, params)

    def cleanup_old_builds(self, component_id: int, branch_id: int,
                          max_builds: int = 5) -> List[Dict]:
        """Cleanup old builds and return paths to delete"""
        query = "EXEC sp_CleanupOldBuilds @component_id = ?, @branch_id = ?, @max_builds_to_keep = ?"
        return self.execute_query(query, (component_id, branch_id, max_builds))

    def log_polling_activity(self, log_level: str, log_message: str,
                            thread_id: int = None, component_id: int = None,
                            branch_id: int = None, build_date: str = None,
                            build_number: int = None, operation_type: str = None,
                            duration_ms: int = None) -> bool:
        """Log polling activity"""
        query = """
            EXEC sp_LogPollingActivity
                @thread_id = ?,
                @component_id = ?,
                @branch_id = ?,
                @log_level = ?,
                @log_message = ?,
                @build_date = ?,
                @build_number = ?,
                @operation_type = ?,
                @duration_ms = ?
        """
        params = (thread_id, component_id, branch_id, log_level, log_message,
                 build_date, build_number, operation_type, duration_ms)
        return self.execute_non_query(query, params)

    def get_jfrog_credentials(self) -> Tuple[str, str, str]:
        """Get JFrog base URL and credentials"""
        base_url = self.get_system_config('JFrogBaseURL') or ''
        username = self.get_system_config('SVCJFROGUSR') or ''
        password = self.get_system_config('SVCJFROGPAS') or ''
        return base_url, username, password

    def get_base_drive(self) -> str:
        """Get base drive path for artifact storage"""
        return self.get_system_config('BaseDrive') or r'C:\WINCORE'

    def get_max_threads(self) -> int:
        """Get maximum concurrent threads"""
        max_threads = self.get_system_config('MaxConcurrentThreads') or '100'
        return int(max_threads)

    def get_max_builds_to_keep(self) -> int:
        """Get maximum builds to keep"""
        max_builds = self.get_system_config('MaxBuildsToKeep') or '5'
        return int(max_builds)
