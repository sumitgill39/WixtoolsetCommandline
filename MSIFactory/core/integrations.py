"""
Integrations Module
Handles all third-party integrations (ServiceNow, Vault, etc.)
"""

import json
import requests
from sqlalchemy import text
from database.connection_manager import execute_with_retry
from logger import get_logger, log_info, log_error
from core.database_operations import get_db_connection

def get_integration_config(integration_type):
    """Get configuration for a specific integration"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT config_data, is_enabled
            FROM integrations_config
            WHERE integration_type = ?
        """, (integration_type,))

        row = cursor.fetchone()
        if row:
            config = json.loads(row[0]) if row[0] else {}
            config['is_enabled'] = row[1]
            conn.close()
            return config
        else:
            conn.close()
            return {'is_enabled': False}

    except Exception as e:
        log_error(f"Error fetching {integration_type} config: {e}")
        return {'is_enabled': False}

def save_integration_config(integration_type, config_data, username):
    """Save configuration for an integration"""
    try:
        def save_config_in_db(db_session):
            # Check if config exists
            check_query = text("""
                SELECT COUNT(*) FROM integrations_config
                WHERE integration_type = :integration_type
            """)
            exists = db_session.execute(check_query, {
                'integration_type': integration_type
            }).fetchone()[0]

            if exists:
                # Update existing config
                update_query = text("""
                    UPDATE integrations_config
                    SET config_data = :config_data,
                        is_enabled = :is_enabled,
                        updated_by = :updated_by,
                        updated_date = GETDATE()
                    WHERE integration_type = :integration_type
                """)
                db_session.execute(update_query, {
                    'integration_type': integration_type,
                    'config_data': json.dumps(config_data),
                    'is_enabled': config_data.get('enabled', False),
                    'updated_by': username
                })
            else:
                # Insert new config
                insert_query = text("""
                    INSERT INTO integrations_config (
                        integration_type, config_data, is_enabled,
                        created_by, updated_by
                    )
                    VALUES (
                        :integration_type, :config_data, :is_enabled,
                        :created_by, :updated_by
                    )
                """)
                db_session.execute(insert_query, {
                    'integration_type': integration_type,
                    'config_data': json.dumps(config_data),
                    'is_enabled': config_data.get('enabled', False),
                    'created_by': username,
                    'updated_by': username
                })

        execute_with_retry(save_config_in_db)
        log_info(f"{integration_type} configuration saved successfully")
        return True, f"{integration_type} configuration saved successfully"

    except Exception as e:
        log_error(f"Error saving {integration_type} config: {e}")
        return False, f"Error saving configuration: {str(e)}"

def test_servicenow_connection(config):
    """Test ServiceNow connection"""
    try:
        # Build ServiceNow API URL
        instance = config.get('instance')
        if not instance:
            return False, "ServiceNow instance URL is required"

        url = f"https://{instance}/api/now/table/sys_user?sysparm_limit=1"

        # Setup authentication
        auth = (config.get('username'), config.get('password'))

        # Make test request
        response = requests.get(url, auth=auth, timeout=10)

        if response.status_code == 200:
            log_info("ServiceNow connection test successful")
            return True, "Connection successful"
        else:
            error_msg = f"Connection failed with status {response.status_code}"
            log_error(f"ServiceNow connection test failed: {error_msg}")
            return False, error_msg

    except requests.exceptions.Timeout:
        return False, "Connection timeout - check instance URL"
    except requests.exceptions.RequestException as e:
        log_error(f"ServiceNow connection test error: {e}")
        return False, f"Connection error: {str(e)}"
    except Exception as e:
        log_error(f"Unexpected error testing ServiceNow connection: {e}")
        return False, f"Unexpected error: {str(e)}"

def sync_servicenow_servers(config):
    """Sync servers from ServiceNow to CMDB"""
    try:
        instance = config.get('instance')
        if not instance:
            return False, 0, "ServiceNow instance URL is required"

        # Query ServiceNow for servers
        url = f"https://{instance}/api/now/table/cmdb_ci_server"
        auth = (config.get('username'), config.get('password'))

        params = {
            'sysparm_limit': 100,
            'sysparm_fields': 'name,host_name,ip_address,os,environment,location'
        }

        response = requests.get(url, auth=auth, params=params, timeout=30)

        if response.status_code != 200:
            return False, 0, f"Failed to fetch servers: Status {response.status_code}"

        servers = response.json().get('result', [])
        synced_count = 0

        def sync_servers_in_db(db_session):
            nonlocal synced_count
            for server in servers:
                # Check if server already exists
                check_query = text("""
                    SELECT server_id FROM cmdb_servers
                    WHERE hostname = :hostname
                """)
                existing = db_session.execute(check_query, {
                    'hostname': server.get('host_name')
                }).fetchone()

                if not existing:
                    # Insert new server
                    insert_query = text("""
                        INSERT INTO cmdb_servers (
                            server_name, hostname, ip_address,
                            os, environment, region, status,
                            infra_type, created_by, source_system
                        )
                        VALUES (
                            :server_name, :hostname, :ip_address,
                            :os, :environment, :region, 'active',
                            'Virtual', 'ServiceNow Sync', 'ServiceNow'
                        )
                    """)
                    db_session.execute(insert_query, {
                        'server_name': server.get('name'),
                        'hostname': server.get('host_name'),
                        'ip_address': server.get('ip_address', ''),
                        'os': server.get('os', 'Unknown'),
                        'environment': server.get('environment', 'Production'),
                        'region': server.get('location', 'Unknown')
                    })
                    synced_count += 1

        execute_with_retry(sync_servers_in_db)

        log_info(f"ServiceNow sync completed: {synced_count} new servers added")
        return True, synced_count, f"Sync completed: {synced_count} new servers added"

    except Exception as e:
        log_error(f"ServiceNow sync error: {e}")
        return False, 0, f"Sync error: {str(e)}"

def test_vault_connection(config):
    """Test HashiCorp Vault connection"""
    try:
        vault_url = config.get('url')
        if not vault_url:
            return False, "Vault URL is required"

        token = config.get('token')
        if not token:
            return False, "Vault token is required"

        # Test Vault health endpoint
        health_url = f"{vault_url}/v1/sys/health"
        headers = {'X-Vault-Token': token}

        response = requests.get(health_url, headers=headers, timeout=10)

        if response.status_code in [200, 429, 473, 501, 503]:
            # These status codes indicate Vault is responding
            log_info("Vault connection test successful")
            return True, "Connection successful"
        else:
            error_msg = f"Connection failed with status {response.status_code}"
            log_error(f"Vault connection test failed: {error_msg}")
            return False, error_msg

    except requests.exceptions.Timeout:
        return False, "Connection timeout - check Vault URL"
    except requests.exceptions.RequestException as e:
        log_error(f"Vault connection test error: {e}")
        return False, f"Connection error: {str(e)}"
    except Exception as e:
        log_error(f"Unexpected error testing Vault connection: {e}")
        return False, f"Unexpected error: {str(e)}"

def get_vault_secrets(config, path):
    """Retrieve secrets from Vault"""
    try:
        vault_url = config.get('url')
        token = config.get('token')

        if not vault_url or not token:
            return None, "Vault configuration incomplete"

        # Build secret URL
        secret_url = f"{vault_url}/v1/{path}"
        headers = {'X-Vault-Token': token}

        response = requests.get(secret_url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            secrets = data.get('data', {})
            log_info(f"Successfully retrieved secrets from path: {path}")
            return secrets, None
        else:
            error_msg = f"Failed to retrieve secrets: Status {response.status_code}"
            log_error(error_msg)
            return None, error_msg

    except Exception as e:
        log_error(f"Error retrieving Vault secrets: {e}")
        return None, f"Error: {str(e)}"

def list_vault_secrets(config):
    """List available secrets in Vault"""
    try:
        vault_url = config.get('url')
        token = config.get('token')
        mount_path = config.get('mount_path', 'secret')

        if not vault_url or not token:
            return []

        # List secrets endpoint
        list_url = f"{vault_url}/v1/{mount_path}/metadata?list=true"
        headers = {'X-Vault-Token': token}

        response = requests.get(list_url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            keys = data.get('data', {}).get('keys', [])
            log_info(f"Retrieved {len(keys)} secret paths from Vault")
            return keys
        else:
            log_error(f"Failed to list Vault secrets: Status {response.status_code}")
            return []

    except Exception as e:
        log_error(f"Error listing Vault secrets: {e}")
        return []

def get_all_integrations_status():
    """Get status of all integrations"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                integration_type,
                is_enabled,
                updated_date,
                updated_by
            FROM integrations_config
            ORDER BY integration_type
        """)

        integrations = []
        for row in cursor.fetchall():
            integrations.append({
                'type': row[0],
                'is_enabled': row[1],
                'updated_date': row[2],
                'updated_by': row[3]
            })

        conn.close()
        return integrations

    except Exception as e:
        log_error(f"Error fetching integrations status: {e}")
        return []

def test_jfrog_connection(config):
    """Test JFrog Artifactory connection"""
    try:
        if not config or not config.get('base_url'):
            return False, "JFrog configuration not found or base URL missing"

        base_url = config.get('base_url')
        username = config.get('username')
        password = config.get('password')
        ssl_verify = config.get('ssl_verify', True)

        if not username or not password:
            return False, "JFrog username or password missing"

        # Test connection by getting system ping
        ping_url = f"{base_url}/api/system/ping"

        response = requests.get(
            ping_url,
            auth=(username, password),
            timeout=10,
            verify=ssl_verify
        )

        if response.status_code == 200:
            log_info("JFrog connection test successful")
            return True, "Connection successful"
        else:
            error_msg = f"JFrog connection failed with status {response.status_code}"
            log_error(error_msg)
            return False, error_msg

    except requests.exceptions.RequestException as e:
        error_msg = f"JFrog connection error: {str(e)}"
        log_error(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"Unexpected error testing JFrog connection: {str(e)}"
        log_error(error_msg)
        return False, error_msg

def get_jfrog_artifacts(config, component_name=None, branch=None):
    """Get artifacts from JFrog Artifactory"""
    try:
        if not config or not config.get('base_url'):
            return False, [], "JFrog configuration not found or base URL missing"

        base_url = config.get('base_url')
        repository = config.get('repository')
        username = config.get('username')
        password = config.get('password')
        ssl_verify = config.get('ssl_verify', True)

        if not all([username, password, repository]):
            return False, [], "JFrog credentials or repository missing"

        # Build search URL for the repository
        search_url = f"{base_url}/api/search/aql"

        # Build AQL query based on filters
        aql_query = f'items.find({{"repo":"{repository}"}}'

        if component_name:
            aql_query += f'.include("name").include("path").include("size").include("created")'
        else:
            aql_query += f').include("name").include("path").include("size").include("created")'

        aql_query += '.sort({"$desc":["created"]}).limit(50)'

        headers = {
            'Content-Type': 'text/plain'
        }

        response = requests.post(
            search_url,
            data=aql_query,
            auth=(username, password),
            headers=headers,
            timeout=30,
            verify=ssl_verify
        )

        if response.status_code == 200:
            result = response.json()
            artifacts = []

            for item in result.get('results', []):
                # Parse the path to extract branch and build info
                path_parts = item.get('path', '').split('/')
                artifact_name = item.get('name', '')

                if len(path_parts) >= 2 and artifact_name.endswith('.zip'):
                    branch_name = path_parts[0] if path_parts[0] else 'unknown'
                    build_folder = path_parts[1] if len(path_parts) > 1 else 'unknown'

                    # Extract component name from filename (remove .zip)
                    component = artifact_name.replace('.zip', '')

                    artifacts.append({
                        'branch': branch_name,
                        'build': build_folder,
                        'component': component,
                        'path': f"{item.get('path', '')}/{artifact_name}",
                        'size': format_bytes(item.get('size', 0)),
                        'date': item.get('created', '').split('T')[0] if item.get('created') else 'Unknown',
                        'download_url': f"{base_url}/{repository}/{item.get('path', '')}/{artifact_name}"
                    })

            log_info(f"Retrieved {len(artifacts)} JFrog artifacts")
            return True, artifacts, f"Found {len(artifacts)} artifacts"
        else:
            error_msg = f"JFrog search failed with status {response.status_code}"
            log_error(error_msg)
            return False, [], error_msg

    except requests.exceptions.RequestException as e:
        error_msg = f"JFrog API error: {str(e)}"
        log_error(error_msg)
        return False, [], error_msg
    except Exception as e:
        error_msg = f"Unexpected error getting JFrog artifacts: {str(e)}"
        log_error(error_msg)
        return False, [], error_msg

def format_bytes(bytes_value):
    """Format bytes to human readable string"""
    try:
        bytes_value = int(bytes_value)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.1f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.1f} TB"
    except:
        return "Unknown"

def get_component_artifacts_from_jfrog(config, component_name, branch=None):
    """Get artifacts for a specific component from JFrog"""
    try:
        if not config or not config.get('base_url'):
            return False, [], "JFrog configuration not found"

        base_url = config.get('base_url')
        repository = config.get('repository')
        username = config.get('username')
        password = config.get('password')
        artifact_path_pattern = config.get('artifact_path_pattern', '{branch}/Build{date}.{buildNumber}/{componentName}.zip')
        ssl_verify = config.get('ssl_verify', True)

        # Build search for specific component
        search_pattern = artifact_path_pattern.replace('{componentName}', component_name)
        if branch:
            search_pattern = search_pattern.replace('{branch}', branch)
        else:
            search_pattern = search_pattern.replace('{branch}', '*')

        # Replace other placeholders with wildcards for searching
        search_pattern = search_pattern.replace('{date}', '*').replace('{buildNumber}', '*')

        # Use AQL to search for specific patterns
        aql_query = f'items.find({{"repo":"{repository}","name":"{component_name}.zip"}}).include("name").include("path").include("size").include("created").sort({{"$desc":["created"]}}).limit(20)'

        search_url = f"{base_url}/api/search/aql"

        response = requests.post(
            search_url,
            data=aql_query,
            auth=(username, password),
            headers={'Content-Type': 'text/plain'},
            timeout=30,
            verify=ssl_verify
        )

        if response.status_code == 200:
            result = response.json()
            builds = []

            for item in result.get('results', []):
                path_parts = item.get('path', '').split('/')
                if len(path_parts) >= 2:
                    branch_name = path_parts[0]
                    build_folder = path_parts[1]

                    builds.append({
                        'branch': branch_name,
                        'build': build_folder,
                        'path': f"{item.get('path', '')}/{item.get('name', '')}",
                        'size': format_bytes(item.get('size', 0)),
                        'created': item.get('created', ''),
                        'download_url': f"{base_url}/{repository}/{item.get('path', '')}/{item.get('name', '')}"
                    })

            return True, builds, f"Found {len(builds)} builds for {component_name}"
        else:
            return False, [], f"Search failed with status {response.status_code}"

    except Exception as e:
        error_msg = f"Error getting component artifacts: {str(e)}"
        log_error(error_msg)
        return False, [], error_msg