# Package Builder - Integration Manager
# Version: 1.0
# Description: Centralized integration configuration management for MSI Factory
# Author: MSI Factory Team

import json
import logging
import requests
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import hashlib
import base64

# Database imports
import pyodbc
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

class IntegrationManager:
    """
    Centralized Integration Manager for MSI Factory.
    Handles configuration, authentication, and communication with external systems.
    """

    def __init__(self):
        """Initialize the IntegrationManager with database configuration."""
        self.db_config = {
            'server': os.getenv('DB_SERVER', 'SUMEETGILL7E47\\MSSQLSERVER01'),
            'database': os.getenv('DB_NAME', 'MSIFactory'),
            'username': os.getenv('DB_USERNAME', ''),
            'password': os.getenv('DB_PASSWORD', ''),
            'driver': 'ODBC Driver 17 for SQL Server',
            'trusted_connection': os.getenv('DB_TRUST_CONNECTION', 'yes')
        }

    def _get_db_connection(self) -> pyodbc.Connection:
        """Establish and return a database connection."""
        try:
            if self.db_config['username'] and self.db_config['password']:
                conn_string = (
                    f"DRIVER={{{self.db_config['driver']}}};"
                    f"SERVER={self.db_config['server']};"
                    f"DATABASE={self.db_config['database']};"
                    f"UID={self.db_config['username']};"
                    f"PWD={self.db_config['password']};"
                    f"TrustServerCertificate=yes;"
                )
            else:
                conn_string = (
                    f"DRIVER={{{self.db_config['driver']}}};"
                    f"SERVER={self.db_config['server']};"
                    f"DATABASE={self.db_config['database']};"
                    f"Trusted_Connection={self.db_config['trusted_connection']};"
                    f"TrustServerCertificate=yes;"
                )

            connection = pyodbc.connect(conn_string)
            return connection
        except Exception as e:
            logger.error(f"Database connection failed: {str(e)}")
            raise Exception(f"Database connection error: {str(e)}")

    # Audit logging removed - using basic audit attributes in main table instead

    def get_integration_config(self, integration_type: str, integration_name: str = None) -> Dict[str, Any]:
        """
        Get integration configuration(s) by type and optionally by name.

        Args:
            integration_type (str): Type of integration (jfrog, servicenow, vault)
            integration_name (str, optional): Specific integration name

        Returns:
            Dict[str, Any]: Integration configuration data
        """
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                # Use direct SQL query instead of stored procedure to avoid api_key column issues
                if integration_name:
                    cursor.execute("""
                        SELECT config_id, integration_type, integration_name, base_url,
                               username, password, token, auth_type,
                               additional_config, is_enabled, is_validated,
                               last_test_date, last_test_result, last_test_message,
                               timeout_seconds, retry_count, ssl_verify,
                               created_date, updated_date, last_used_date, usage_count
                        FROM integrations_config
                        WHERE integration_type = ? AND integration_name = ?
                    """, (integration_type, integration_name))
                else:
                    cursor.execute("""
                        SELECT config_id, integration_type, integration_name, base_url,
                               username, auth_type, is_enabled, is_validated,
                               last_test_date, last_test_result, last_test_message,
                               timeout_seconds, retry_count, ssl_verify,
                               created_date, updated_date, last_used_date, usage_count
                        FROM integrations_config
                        WHERE integration_type = ?
                        ORDER BY integration_name
                    """, (integration_type,))

                if integration_name:
                    # Get single configuration
                    row = cursor.fetchone()
                    if row:
                        config = {
                            'config_id': row.config_id,
                            'integration_type': row.integration_type,
                            'integration_name': row.integration_name,
                            'base_url': row.base_url,
                            'username': row.username,
                            'password': row.password if hasattr(row, 'password') else None,
                            'token': row.token if hasattr(row, 'token') else None,
                            'auth_type': row.auth_type,
                            'additional_config': json.loads(row.additional_config) if row.additional_config else {},
                            'is_enabled': row.is_enabled,
                            'is_validated': row.is_validated,
                            'last_test_date': row.last_test_date.strftime('%Y-%m-%d %H:%M:%S') if row.last_test_date else None,
                            'last_test_result': row.last_test_result,
                            'last_test_message': row.last_test_message,
                            'timeout_seconds': row.timeout_seconds,
                            'retry_count': row.retry_count,
                            'ssl_verify': row.ssl_verify,
                            'created_date': row.created_date.strftime('%Y-%m-%d %H:%M:%S') if row.created_date else None,
                            'updated_date': row.updated_date.strftime('%Y-%m-%d %H:%M:%S') if row.updated_date else None,
                            'last_used_date': row.last_used_date.strftime('%Y-%m-%d %H:%M:%S') if row.last_used_date else None,
                            'usage_count': row.usage_count
                        }
                        return {'success': True, 'config': config}
                    else:
                        return {'success': False, 'error': 'Integration configuration not found'}
                else:
                    # Get all configurations for the type
                    rows = cursor.fetchall()
                    configs = []
                    for row in rows:
                        config = {
                            'config_id': row.config_id,
                            'integration_type': row.integration_type,
                            'integration_name': row.integration_name,
                            'base_url': row.base_url,
                            'username': row.username,
                            'auth_type': row.auth_type,
                            'is_enabled': row.is_enabled,
                            'is_validated': row.is_validated,
                            'last_test_date': row.last_test_date.strftime('%Y-%m-%d %H:%M:%S') if row.last_test_date else None,
                            'last_test_result': row.last_test_result,
                            'timeout_seconds': row.timeout_seconds,
                            'created_date': row.created_date.strftime('%Y-%m-%d %H:%M:%S') if row.created_date else None,
                            'usage_count': row.usage_count
                        }
                        configs.append(config)
                    return {'success': True, 'configs': configs}

        except Exception as e:
            logger.error(f"Error retrieving integration config: {str(e)}")
            return {'success': False, 'error': f"Failed to retrieve configuration: {str(e)}"}

    def get_jfrog_base_url(self, integration_name: str = 'Primary JFrog') -> str:
        """
        Get JFrog base URL for use in branch display formatting.

        Args:
            integration_name (str): Name of the JFrog integration

        Returns:
            str: JFrog base URL or placeholder if not found
        """
        try:
            config_result = self.get_integration_config('jfrog', integration_name)
            if config_result['success'] and config_result.get('config'):
                config = config_result['config']
                if config['is_enabled']:
                    # Update usage tracking
                    self._update_integration_usage(config['config_id'])
                    return config['base_url']

            # Try to get any enabled JFrog configuration
            all_configs = self.get_integration_config('jfrog')
            if all_configs['success'] and all_configs.get('configs'):
                for config in all_configs['configs']:
                    if config['is_enabled']:
                        self._update_integration_usage(config['config_id'])
                        return config['base_url']

            # Return placeholder if no configuration found
            return '{baseURL}'

        except Exception as e:
            logger.error(f"Error getting JFrog base URL: {str(e)}")
            return '{baseURL}'

    def get_jfrog_credentials(self, integration_name: str = 'Primary JFrog') -> Dict[str, str]:
        """
        Get JFrog credentials for authentication.

        Args:
            integration_name (str): Name of the JFrog integration

        Returns:
            Dict[str, str]: Dictionary containing username and password
        """
        try:
            config_result = self.get_integration_config('jfrog', integration_name)
            if config_result['success'] and config_result.get('config'):
                config = config_result['config']
                if config['is_enabled']:
                    self._update_integration_usage(config['config_id'])
                    return {
                        'username': config.get('username', ''),
                        'password': config.get('password', ''),
                        'base_url': config.get('base_url', '')
                    }

            return {'username': '', 'password': '', 'base_url': ''}

        except Exception as e:
            logger.error(f"Error getting JFrog credentials: {str(e)}")
            return {'username': '', 'password': '', 'base_url': ''}

    def build_jfrog_artifact_url(self, project_name: str, component_name: str, branch: str, build_date: str, build_number: str, integration_name: str = 'Primary JFrog') -> str:
        """
        Build complete JFrog artifact URL using the specific pattern.

        Args:
            project_name (str): Name of the project
            component_name (str): Name of the component
            branch (str): Branch name
            build_date (str): Build date
            build_number (str): Build number
            integration_name (str): Name of the JFrog integration

        Returns:
            str: Complete JFrog artifact URL
        """
        try:
            base_url = self.get_jfrog_base_url(integration_name)
            if base_url == '{baseURL}':
                return '{baseURL}'

            # Build the specific URL pattern:
            # https://mgti-dal-so-art-mrshmc.com/artifactory/raw/Mercer/{ProjectName}/{ComponentName}/{branch}/Build{date}.{buildNumber}/{componentName}.zip

            # Ensure base_url ends with /artifactory
            if not base_url.endswith('/artifactory'):
                if base_url.endswith('/'):
                    base_url = base_url + 'artifactory'
                else:
                    base_url = base_url + '/artifactory'

            artifact_url = f"{base_url}/raw/Mercer/{project_name}/{component_name}/{branch}/Build{build_date}.{build_number}/{component_name}.zip"

            logger.info(f"Built JFrog artifact URL: {artifact_url}")
            return artifact_url

        except Exception as e:
            logger.error(f"Error building JFrog artifact URL: {str(e)}")
            return '{baseURL}'

    def _find_curl_exe(self) -> str:
        """
        Find the path to curl.exe on Windows.

        Returns:
            str: Path to curl.exe or None if not found
        """
        import os
        import shutil

        # Try common curl locations on Windows
        curl_paths = [
            # Windows 10/11 built-in curl
            r"C:\Windows\System32\curl.exe",
            # Git for Windows curl
            r"C:\Program Files\Git\mingw64\bin\curl.exe",
            r"C:\Program Files (x86)\Git\mingw64\bin\curl.exe",
            # Chocolatey curl
            r"C:\ProgramData\chocolatey\bin\curl.exe",
            # Custom installation paths
            r"C:\Tools\curl\bin\curl.exe",
            r"C:\curl\bin\curl.exe"
        ]

        # First, check if curl is in PATH
        curl_in_path = shutil.which("curl.exe")
        if curl_in_path:
            logger.info(f"Found curl.exe in PATH: {curl_in_path}")
            return curl_in_path

        # Check common locations
        for curl_path in curl_paths:
            if os.path.exists(curl_path):
                logger.info(f"Found curl.exe at: {curl_path}")
                return curl_path

        # If not found, log available options
        logger.warning("curl.exe not found in common locations. Please install curl or specify path.")
        return None

    def get_configured_curl_path(self, integration_name: str = 'Primary JFrog') -> str:
        """
        Get the configured curl path from JFrog integration settings.

        Args:
            integration_name (str): Name of the JFrog integration

        Returns:
            str: Configured curl path or None
        """
        try:
            config_result = self.get_integration_config('jfrog', integration_name)
            if config_result['success'] and config_result.get('config'):
                config = config_result['config']
                additional_config = config.get('additional_config', {})
                return additional_config.get('curl_path')
            return None
        except Exception as e:
            logger.error(f"Error getting configured curl path: {str(e)}")
            return None

    def download_jfrog_artifact(self, project_name: str, component_name: str, branch: str, build_date: str, build_number: str, download_path: str, integration_name: str = 'Primary JFrog', curl_path: str = None) -> Dict[str, Any]:
        """
        Download artifact from JFrog using curl command.

        Args:
            project_name (str): Name of the project
            component_name (str): Name of the component
            branch (str): Branch name
            build_date (str): Build date
            build_number (str): Build number
            download_path (str): Local path to download the file
            integration_name (str): Name of the JFrog integration
            curl_path (str, optional): Path to curl.exe. If not provided, will search for it.

        Returns:
            Dict[str, Any]: Result containing success status and details
        """
        try:
            import subprocess
            import os

            # Find curl.exe path - check configuration first, then auto-detect, then use provided
            if not curl_path:
                # First try to get from configuration
                curl_path = self.get_configured_curl_path(integration_name)

                if curl_path:
                    logger.info(f"Using configured curl path from JFrog settings: {curl_path}")
                else:
                    # If not configured, try auto-detection
                    curl_path = self._find_curl_exe()
                    if curl_path:
                        logger.info(f"Using auto-detected curl path: {curl_path}")

            if not curl_path:
                return {
                    'success': False,
                    'error': 'curl.exe not found. Please install curl or provide path.',
                    'downloaded_file': None,
                    'suggestion': 'Install curl from https://curl.se/windows/ or use Windows 10/11 built-in curl'
                }

            # Verify curl.exe exists at the specified path
            if not os.path.exists(curl_path):
                return {
                    'success': False,
                    'error': f'curl.exe not found at specified path: {curl_path}',
                    'downloaded_file': None
                }

            # Get JFrog credentials
            credentials = self.get_jfrog_credentials(integration_name)
            if not credentials['username'] or not credentials['password']:
                return {
                    'success': False,
                    'error': 'JFrog credentials not configured',
                    'downloaded_file': None
                }

            # Build artifact URL
            artifact_url = self.build_jfrog_artifact_url(
                project_name, component_name, branch, build_date, build_number, integration_name
            )

            if artifact_url == '{baseURL}':
                return {
                    'success': False,
                    'error': 'JFrog base URL not configured',
                    'downloaded_file': None
                }

            # Ensure download directory exists
            download_dir = os.path.dirname(download_path)
            if download_dir and not os.path.exists(download_dir):
                os.makedirs(download_dir, exist_ok=True)

            # Build curl command: Curl.exe -u "{UserName}":"{Password}" -O {JfrogURL}
            curl_command = [
                curl_path,  # Use the full path to curl.exe
                '-u', f"{credentials['username']}:{credentials['password']}",
                '-o', download_path,  # Use -o instead of -O to specify exact output path
                '-L',  # Follow redirects
                '--ssl-no-revoke',  # Windows-specific: don't check certificate revocation
                artifact_url
            ]

            logger.info(f"Executing curl command to download from JFrog: {curl_path} -u [CREDENTIALS_HIDDEN] -o {download_path} -L --ssl-no-revoke {artifact_url}")

            # Execute curl command
            result = subprocess.run(
                curl_command,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                shell=False  # Don't use shell for security
            )

            if result.returncode == 0:
                # Verify file was downloaded
                if os.path.exists(download_path) and os.path.getsize(download_path) > 0:
                    file_size = os.path.getsize(download_path)
                    logger.info(f"Successfully downloaded JFrog artifact: {download_path} ({file_size} bytes)")

                    return {
                        'success': True,
                        'message': f'Artifact downloaded successfully ({file_size} bytes)',
                        'downloaded_file': download_path,
                        'file_size': file_size,
                        'artifact_url': artifact_url
                    }
                else:
                    return {
                        'success': False,
                        'error': 'Download completed but file not found or empty',
                        'downloaded_file': None,
                        'curl_output': result.stdout,
                        'curl_error': result.stderr
                    }
            else:
                error_msg = f"Curl command failed with exit code {result.returncode}"
                logger.error(f"{error_msg}: {result.stderr}")

                return {
                    'success': False,
                    'error': error_msg,
                    'downloaded_file': None,
                    'curl_output': result.stdout,
                    'curl_error': result.stderr,
                    'exit_code': result.returncode
                }

        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': 'Download timed out after 5 minutes',
                'downloaded_file': None
            }
        except Exception as e:
            logger.error(f"Error downloading JFrog artifact: {str(e)}")
            return {
                'success': False,
                'error': f"Download failed: {str(e)}",
                'downloaded_file': None
            }

    def list_jfrog_artifacts(self, project_name: str, component_name: str, branch: str = None, integration_name: str = 'Primary JFrog') -> Dict[str, Any]:
        """
        List available artifacts from JFrog for a specific component.

        Args:
            project_name (str): Name of the project
            component_name (str): Name of the component
            branch (str, optional): Branch name to filter by
            integration_name (str): Name of the JFrog integration

        Returns:
            Dict[str, Any]: Result containing artifact list
        """
        try:
            import requests

            # Get JFrog credentials
            credentials = self.get_jfrog_credentials(integration_name)
            if not credentials['username'] or not credentials['password']:
                return {
                    'success': False,
                    'error': 'JFrog credentials not configured',
                    'artifacts': []
                }

            base_url = credentials['base_url'].rstrip('/')

            # Use AQL (Artifactory Query Language) to search for artifacts
            aql_url = f"{base_url}/api/search/aql"

            # Build AQL query to find artifacts for the component
            if branch:
                aql_query = f'''
                    items.find({{
                        "repo":"raw",
                        "path":"Mercer/{project_name}/{component_name}/{branch}/*",
                        "name":"{component_name}.zip"
                    }}).include("name","path","size","created","modified")
                    .sort({{"$desc":["created"]}})
                    .limit(50)
                '''
            else:
                aql_query = f'''
                    items.find({{
                        "repo":"raw",
                        "path":"Mercer/{project_name}/{component_name}/*/*",
                        "name":"{component_name}.zip"
                    }}).include("name","path","size","created","modified")
                    .sort({{"$desc":["created"]}})
                    .limit(50)
                '''

            response = requests.post(
                aql_url,
                data=aql_query,
                auth=(credentials['username'], credentials['password']),
                headers={'Content-Type': 'text/plain'},
                timeout=30
            )

            if response.status_code == 200:
                result_data = response.json()
                artifacts = []

                for item in result_data.get('results', []):
                    # Parse path to extract branch and build info
                    # Path format: Mercer/{ProjectName}/{ComponentName}/{branch}/Build{date}.{buildNumber}
                    path_parts = item['path'].split('/')
                    if len(path_parts) >= 5:
                        item_branch = path_parts[3]
                        build_folder = path_parts[4]

                        artifacts.append({
                            'component_name': component_name,
                            'branch': item_branch,
                            'build_folder': build_folder,
                            'file_name': item['name'],
                            'size': item.get('size', 0),
                            'created': item.get('created', ''),
                            'modified': item.get('modified', ''),
                            'download_url': self.build_jfrog_artifact_url(
                                project_name, component_name, item_branch,
                                build_folder.replace('Build', '').split('.')[0],
                                build_folder.replace('Build', '').split('.')[1] if '.' in build_folder else '1',
                                integration_name
                            )
                        })

                return {
                    'success': True,
                    'artifacts': artifacts,
                    'count': len(artifacts)
                }
            else:
                return {
                    'success': False,
                    'error': f'JFrog API request failed: {response.status_code}',
                    'artifacts': []
                }

        except Exception as e:
            logger.error(f"Error listing JFrog artifacts: {str(e)}")
            return {
                'success': False,
                'error': f"Failed to list artifacts: {str(e)}",
                'artifacts': []
            }

    def _update_integration_usage(self, config_id: int):
        """Update integration usage statistics."""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                # Simple UPDATE query instead of stored procedure
                cursor.execute("""
                    UPDATE integrations_config
                    SET last_used_date = GETDATE(), usage_count = usage_count + 1
                    WHERE config_id = ?
                """, (config_id,))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to update integration usage: {str(e)}")

    def save_integration_config(self, integration_data: Dict[str, Any], performed_by: str) -> Dict[str, Any]:
        """
        Save or update integration configuration.

        Args:
            integration_data (Dict[str, Any]): Integration configuration data
            performed_by (str): Username of the user saving the configuration

        Returns:
            Dict[str, Any]: Result of the save operation
        """
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()

                config_id = integration_data.get('config_id')
                integration_type = integration_data.get('integration_type')
                integration_name = integration_data.get('integration_name')

                if config_id:
                    # Update existing configuration
                    update_query = """
                    UPDATE integrations_config
                    SET integration_name = ?, base_url = ?, username = ?, password = ?,
                        token = ?, auth_type = ?, additional_config = ?,
                        is_enabled = ?, timeout_seconds = ?, retry_count = ?, ssl_verify = ?,
                        updated_date = GETDATE(), updated_by = ?, version_number = version_number + 1
                    WHERE config_id = ?
                    """
                    cursor.execute(update_query, (
                        integration_name, integration_data.get('base_url'),
                        integration_data.get('username'), integration_data.get('password'),
                        integration_data.get('token'),
                        integration_data.get('auth_type', 'username_password'),
                        json.dumps(integration_data.get('additional_config', {})),
                        integration_data.get('is_enabled', True),
                        integration_data.get('timeout_seconds', 30),
                        integration_data.get('retry_count', 3),
                        integration_data.get('ssl_verify', True),
                        performed_by, config_id
                    ))

                    action_type = 'updated'
                    message = f"Integration configuration '{integration_name}' updated successfully"

                else:
                    # Insert new configuration
                    insert_query = """
                    INSERT INTO integrations_config (
                        integration_type, integration_name, base_url, username, password,
                        token, auth_type, additional_config, is_enabled,
                        timeout_seconds, retry_count, ssl_verify, created_by, updated_by
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """
                    cursor.execute(insert_query, (
                        integration_type, integration_name,
                        integration_data.get('base_url'), integration_data.get('username'),
                        integration_data.get('password'), integration_data.get('token'),
                        integration_data.get('auth_type', 'username_password'),
                        json.dumps(integration_data.get('additional_config', {})),
                        integration_data.get('is_enabled', True),
                        integration_data.get('timeout_seconds', 30),
                        integration_data.get('retry_count', 3),
                        integration_data.get('ssl_verify', True),
                        performed_by, performed_by
                    ))

                    # Get the new config_id
                    cursor.execute("SELECT @@IDENTITY")
                    config_id = cursor.fetchone()[0]
                    action_type = 'created'
                    message = f"Integration configuration '{integration_name}' created successfully"

                conn.commit()
                logger.info(message)
                return {'success': True, 'message': message, 'config_id': config_id}

        except Exception as e:
            logger.error(f"Error saving integration config: {str(e)}")
            return {'success': False, 'error': f"Failed to save configuration: {str(e)}"}

    def test_integration_connection(self, integration_type: str, integration_name: str, performed_by: str) -> Dict[str, Any]:
        """
        Test connection to an integration service.

        Args:
            integration_type (str): Type of integration
            integration_name (str): Name of the integration
            performed_by (str): Username performing the test

        Returns:
            Dict[str, Any]: Test result
        """
        try:
            config_result = self.get_integration_config(integration_type, integration_name)
            if not config_result['success']:
                return config_result

            config = config_result['config']
            config_id = config['config_id']

            # Test based on integration type
            if integration_type == 'jfrog':
                result = self._test_jfrog_connection(config)
            elif integration_type == 'servicenow':
                result = self._test_servicenow_connection(config)
            elif integration_type == 'vault':
                result = self._test_vault_connection(config)
            else:
                result = {'success': False, 'message': f'Unknown integration type: {integration_type}'}

            # Update test results in database
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE integrations_config
                    SET last_test_date = GETDATE(),
                        last_test_result = ?,
                        last_test_message = ?,
                        is_validated = ?
                    WHERE config_id = ?
                """, (
                    'success' if result['success'] else 'failed',
                    result['message'],
                    1 if result['success'] else 0,
                    config_id
                ))
                conn.commit()

            return result

        except Exception as e:
            logger.error(f"Error testing integration connection: {str(e)}")
            return {'success': False, 'message': f"Test failed: {str(e)}"}

    def _test_jfrog_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Test JFrog Artifactory connection."""
        try:
            base_url = config['base_url'].rstrip('/')
            test_url = f"{base_url}/api/system/ping"

            auth = None
            if config['auth_type'] == 'username_password' and config['username'] and config['password']:
                auth = (config['username'], config['password'])
            # api_key auth type removed - not supported anymore
            else:
                return {'success': False, 'message': 'Invalid authentication configuration for JFrog'}

            response = requests.get(
                test_url,
                auth=auth,
                headers=headers if 'headers' in locals() else None,
                timeout=config.get('timeout_seconds', 30),
                verify=config.get('ssl_verify', True)
            )

            if response.status_code == 200:
                return {'success': True, 'message': 'JFrog connection successful'}
            else:
                return {'success': False, 'message': f'JFrog connection failed with status {response.status_code}'}

        except Exception as e:
            return {'success': False, 'message': f'JFrog connection error: {str(e)}'}

    def _test_servicenow_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Test ServiceNow connection."""
        try:
            base_url = config['base_url'].rstrip('/')
            test_url = f"{base_url}/api/now/table/sys_user?sysparm_limit=1"

            if config['auth_type'] == 'username_password' and config['username'] and config['password']:
                auth = (config['username'], config['password'])
            else:
                return {'success': False, 'message': 'ServiceNow requires username/password authentication'}

            response = requests.get(
                test_url,
                auth=auth,
                timeout=config.get('timeout_seconds', 30),
                verify=config.get('ssl_verify', True),
                headers={'Accept': 'application/json'}
            )

            if response.status_code == 200:
                return {'success': True, 'message': 'ServiceNow connection successful'}
            else:
                return {'success': False, 'message': f'ServiceNow connection failed with status {response.status_code}'}

        except Exception as e:
            return {'success': False, 'message': f'ServiceNow connection error: {str(e)}'}

    def _test_vault_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Test HashiCorp Vault connection."""
        try:
            base_url = config['base_url'].rstrip('/')
            test_url = f"{base_url}/v1/sys/health"

            headers = {}
            if config['auth_type'] == 'token' and config['token']:
                headers['X-Vault-Token'] = config['token']
            else:
                return {'success': False, 'message': 'Vault requires token authentication'}

            response = requests.get(
                test_url,
                headers=headers,
                timeout=config.get('timeout_seconds', 30),
                verify=config.get('ssl_verify', True)
            )

            if response.status_code in [200, 429, 472, 473]:  # Various healthy states
                return {'success': True, 'message': 'Vault connection successful'}
            else:
                return {'success': False, 'message': f'Vault connection failed with status {response.status_code}'}

        except Exception as e:
            return {'success': False, 'message': f'Vault connection error: {str(e)}'}

    def get_all_integrations_status(self) -> Dict[str, Any]:
        """Get status of all configured integrations."""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT integration_type, integration_name, is_enabled,
                           is_validated, last_test_result, last_test_date,
                           usage_count, last_used_date
                    FROM integrations_config
                    ORDER BY integration_type, integration_name
                """)

                integrations = []
                for row in cursor.fetchall():
                    integration = {
                        'integration_type': row.integration_type,
                        'integration_name': row.integration_name,
                        'is_enabled': row.is_enabled,
                        'is_validated': row.is_validated,
                        'last_test_result': row.last_test_result,
                        'last_test_date': row.last_test_date.strftime('%Y-%m-%d %H:%M:%S') if row.last_test_date else None,
                        'usage_count': row.usage_count,
                        'last_used_date': row.last_used_date.strftime('%Y-%m-%d %H:%M:%S') if row.last_used_date else None
                    }
                    integrations.append(integration)

                return {'success': True, 'integrations': integrations}

        except Exception as e:
            logger.error(f"Error getting integrations status: {str(e)}")
            return {'success': False, 'error': f"Failed to get status: {str(e)}"}

# Initialize the integration manager instance
integration_manager = IntegrationManager()