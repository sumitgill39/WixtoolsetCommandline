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