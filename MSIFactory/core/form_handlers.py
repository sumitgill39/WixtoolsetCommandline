"""
Form Handlers Module
Handles complex form processing - replaces JavaScript form manipulation
"""

from flask import request, session, flash
from sqlalchemy import text
from database.connection_manager import execute_with_retry
from logger import get_logger, log_info, log_error
from core.utilities import (
    generate_guid, generate_project_component_guid,
    generate_default_values, format_version_number,
    sanitize_filename, generate_install_path
)
from core.database_operations import get_db_connection

logger = get_logger()

class ProjectFormHandler:
    """Handles project creation and editing forms"""

    def __init__(self):
        self.component_counter = 0

    def process_project_form(self, form_data, is_edit=False, project_id=None):
        """
        Process project form data
        Replaces JavaScript addNewComponent() and form processing
        """
        try:
            # Extract basic project information
            project_data = self._extract_project_data(form_data)

            # Check for duplicate project key (unless editing the same project)
            if not is_edit or not project_id:
                if self._check_duplicate_project_key(project_data['project_key']):
                    return {
                        'success': False,
                        'error': f"Project key '{project_data['project_key']}' already exists. Please choose a different project key."
                    }

            # Extract components data
            components_data = self._extract_components_data(form_data, project_data['project_key'])

            # Extract environments data
            environments_data = self._extract_environments_data(form_data)

            # Pre-process and validate data
            project_data = self._preprocess_project_data(project_data)
            components_data = self._preprocess_components_data(components_data, project_data)

            log_info(f"Processed {'edit' if is_edit else 'create'} form for project: {project_data['project_name']}")
            log_info(f"Components: {len(components_data)}, Environments: {len(environments_data)}")

            return {
                'success': True,
                'project_data': project_data,
                'components_data': components_data,
                'environments_data': environments_data
            }

        except Exception as e:
            log_error(f"Error processing project form: {e}")
            return {
                'success': False,
                'error': f"Form processing error: {str(e)}"
            }

    def _extract_project_data(self, form_data):
        """Extract main project data from form"""
        return {
            'project_name': form_data.get('project_name', '').strip(),
            'project_key': form_data.get('project_key', '').upper().strip(),
            'project_guid': form_data.get('project_guid') or generate_guid(),
            'description': form_data.get('description', '').strip(),
            'project_type': form_data.get('project_type', ''),
            'owner_team': form_data.get('owner_team', '').strip(),
            'color_primary': form_data.get('color_primary', '#2c3e50'),
            'color_secondary': form_data.get('color_secondary', '#3498db'),
            'status': form_data.get('status', 'active'),
            'artifact_source_type': form_data.get('artifact_source_type', ''),
            'artifact_url': form_data.get('artifact_url', ''),
            'artifact_username': form_data.get('artifact_username', ''),
            'artifact_password': form_data.get('artifact_password', '')
        }

    def _extract_components_data(self, form_data, project_key):
        """
        Extract components data from form
        Replaces JavaScript component extraction logic
        """
        components_data = []
        component_counter = 1

        # Extract new components
        while True:
            component_name = form_data.get(f'component_name_{component_counter}')
            if not component_name:
                break

            # Generate component GUID if not provided
            component_guid = form_data.get(f'component_guid_{component_counter}')
            if not component_guid:
                component_guid = generate_project_component_guid(project_key, component_counter)

            component_data = {
                'component_guid': component_guid,
                'component_name': component_name.strip(),
                'component_type': form_data.get(f'component_type_{component_counter}', ''),
                'framework': form_data.get(f'component_framework_{component_counter}', ''),
                'artifact_source': form_data.get(f'component_artifact_{component_counter}', ''),
                'is_new': True,
                'counter': component_counter
            }

            # Add MSI configuration data if present
            self._extract_component_msi_data(form_data, component_data, component_counter)

            components_data.append(component_data)
            component_counter += 1

        # Extract existing components (for edit forms)
        existing_counter = 0
        while True:
            component_name = form_data.get(f'component_name_existing_{existing_counter}')
            if not component_name:
                break

            component_data = {
                'component_id': form_data.get(f'component_id_{existing_counter}'),
                'component_guid': form_data.get(f'component_guid_existing_{existing_counter}'),
                'component_name': component_name.strip(),
                'component_type': form_data.get(f'component_type_existing_{existing_counter}', ''),
                'framework': form_data.get(f'component_framework_existing_{existing_counter}', ''),
                'is_enabled': form_data.get(f'component_enabled_existing_{existing_counter}') == 'on',
                'is_new': False,
                'is_existing': True,
                'counter': existing_counter
            }

            # Add MSI configuration data
            self._extract_component_msi_data(form_data, component_data, existing_counter, is_existing=True)

            components_data.append(component_data)
            existing_counter += 1

        return components_data

    def _extract_component_msi_data(self, form_data, component_data, counter, is_existing=False):
        """Extract MSI configuration data for a component"""
        prefix = 'existing_' if is_existing else ''

        msi_data = {
            'app_name': form_data.get(f'component_app_name_{prefix}{counter}', ''),
            'app_version': form_data.get(f'component_version_{prefix}{counter}', '1.0.0.0'),
            'manufacturer': form_data.get(f'component_manufacturer_{prefix}{counter}', ''),
            'install_folder': form_data.get(f'component_install_folder_{prefix}{counter}', ''),
            'target_server': form_data.get(f'component_target_server_{prefix}{counter}', ''),
            'target_environment': form_data.get(f'component_target_environment_{prefix}{counter}', ''),
        }

        # IIS Configuration (for web apps)
        if component_data.get('component_type') in ['webapp', 'website', 'api']:
            msi_data.update({
                'iis_website_name': form_data.get(f'component_iis_website_{prefix}{counter}', ''),
                'iis_app_pool_name': form_data.get(f'component_app_pool_{prefix}{counter}', ''),
                'port': form_data.get(f'component_port_{prefix}{counter}', '80')
            })

        # Service Configuration
        if component_data.get('component_type') == 'service':
            msi_data.update({
                'service_name': form_data.get(f'component_service_name_{prefix}{counter}', ''),
                'service_display_name': form_data.get(f'component_service_display_{prefix}{counter}', '')
            })

        component_data['msi_config'] = msi_data

    def _extract_environments_data(self, form_data):
        """Extract environments data from form"""
        environments = form_data.getlist('environments')
        environments_data = []

        for env in environments:
            env_data = {
                'environment_name': env,
                'environment_description': f"{env} Environment",
                'servers': form_data.get(f'servers_{env}', ''),
                'region': form_data.get(f'region_{env}', '').upper()
            }
            environments_data.append(env_data)

        return environments_data

    def _preprocess_project_data(self, project_data):
        """Pre-process and enhance project data"""
        # Ensure GUID is generated
        if not project_data.get('project_guid'):
            project_data['project_guid'] = generate_guid()

        # Ensure project key is uppercase and valid
        project_data['project_key'] = project_data['project_key'].upper()

        # Sanitize text fields
        project_data['project_name'] = sanitize_filename(project_data['project_name'])
        project_data['description'] = project_data['description'][:500]  # Limit description

        return project_data

    def _preprocess_components_data(self, components_data, project_data):
        """Pre-process and enhance components data"""
        processed_components = []
        seen_names = set()

        for component in components_data:
            # Ensure unique component names
            original_name = component['component_name']
            counter = 1
            while component['component_name'].lower() in seen_names:
                component['component_name'] = f"{original_name}{counter}"
                counter += 1

            seen_names.add(component['component_name'].lower())

            # Generate defaults if missing
            if component.get('is_new', False):
                defaults = generate_default_values(
                    component['component_type'],
                    component['component_name'],
                    project_data['project_key']
                )

                # Merge defaults with existing data
                msi_config = component.get('msi_config', {})
                for key, default_value in defaults.items():
                    if not msi_config.get(key):
                        msi_config[key] = default_value

                component['msi_config'] = msi_config

            # Format version number
            if 'msi_config' in component and 'app_version' in component['msi_config']:
                component['msi_config']['app_version'] = format_version_number(
                    component['msi_config']['app_version']
                )

            # Generate install path if not provided
            if 'msi_config' in component and not component['msi_config'].get('install_folder'):
                component['msi_config']['install_folder'] = generate_install_path(
                    component['component_type'],
                    component['component_name']
                )

            processed_components.append(component)

        return processed_components

    def _check_duplicate_project_key(self, project_key):
        """Check if project key already exists in database"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM projects WHERE project_key = ?", (project_key,))
            count = cursor.fetchone()[0]

            conn.close()
            return count > 0

        except Exception as e:
            log_error(f"Error checking duplicate project key: {e}")
            return False


class ComponentFormHandler:
    """Handles individual component operations"""

    def process_add_component(self, form_data, project_id, project_key):
        """
        Process add component request
        Replaces JavaScript addNewComponent AJAX
        """
        try:
            component_data = {
                'project_id': project_id,
                'component_name': form_data.get('component_name', '').strip(),
                'component_type': form_data.get('component_type', ''),
                'framework': form_data.get('framework', ''),
                'artifact_source': form_data.get('artifact_source', ''),
                'component_guid': generate_project_component_guid(project_key, 1)  # Will be properly numbered in DB
            }

            # Generate defaults
            defaults = generate_default_values(
                component_data['component_type'],
                component_data['component_name'],
                project_key
            )

            component_data.update(defaults)

            log_info(f"Processed add component form: {component_data['component_name']}")
            return {
                'success': True,
                'component_data': component_data
            }

        except Exception as e:
            log_error(f"Error processing add component form: {e}")
            return {
                'success': False,
                'error': f"Component processing error: {str(e)}"
            }

    def process_component_config(self, form_data):
        """
        Process component configuration form
        Replaces JavaScript saveConfiguration
        """
        try:
            config_data = {
                'component_id': form_data.get('component_id'),
                'app_name': form_data.get('app_name', '').strip(),
                'app_version': format_version_number(form_data.get('app_version', '1.0.0.0')),
                'manufacturer': form_data.get('manufacturer', '').strip(),
                'upgrade_code': form_data.get('upgrade_code') or generate_guid(),
                'install_folder': form_data.get('install_folder', '').strip(),
                'target_server': form_data.get('target_server', '').strip(),
                'target_environment': form_data.get('target_environment', ''),
                'auto_increment_version': form_data.get('auto_increment_version') == 'on',
            }

            # IIS Configuration
            config_data.update({
                'iis_website_name': form_data.get('iis_website_name', ''),
                'iis_app_pool_name': form_data.get('iis_app_pool_name', ''),
                'app_pool_dotnet_version': form_data.get('app_pool_dotnet_version', ''),
                'app_pool_pipeline_mode': form_data.get('app_pool_pipeline_mode', ''),
                'app_pool_identity': form_data.get('app_pool_identity', ''),
                'app_pool_enable_32bit': form_data.get('app_pool_enable_32bit') == 'on',
            })

            # Service Configuration
            config_data.update({
                'service_name': form_data.get('service_name', ''),
                'service_display_name': form_data.get('service_display_name', ''),
                'service_description': form_data.get('service_description', ''),
                'service_start_type': form_data.get('service_start_type', ''),
                'service_account': form_data.get('service_account', ''),
            })

            log_info(f"Processed component config for ID: {config_data['component_id']}")
            return {
                'success': True,
                'config_data': config_data
            }

        except Exception as e:
            log_error(f"Error processing component config: {e}")
            return {
                'success': False,
                'error': f"Configuration processing error: {str(e)}"
            }

class UserFormHandler:
    """Handles user management forms"""

    def process_user_projects_update(self, form_data):
        """
        Process user projects assignment
        Replaces JavaScript user management
        """
        try:
            username = form_data.get('username', '').strip()
            project_keys = form_data.getlist('project_keys')
            all_projects_access = form_data.get('all_projects_access') == 'on'

            # If all projects access is selected, clear individual selections
            if all_projects_access:
                project_keys = ['*']

            log_info(f"Processed user projects update for {username}: {len(project_keys)} projects")
            return {
                'success': True,
                'username': username,
                'project_keys': project_keys,
                'all_projects_access': all_projects_access
            }

        except Exception as e:
            log_error(f"Error processing user projects form: {e}")
            return {
                'success': False,
                'error': f"User projects processing error: {str(e)}"
            }

class IntegrationsFormHandler:
    """Handles integration configuration forms"""

    def process_servicenow_config(self, form_data):
        """Process ServiceNow configuration"""
        try:
            config_data = {
                'instance': form_data.get('snow_instance_url', '').strip().rstrip('/'),
                'username': form_data.get('snow_username', '').strip(),
                'password': form_data.get('snow_password', ''),
                'table': form_data.get('snow_table', 'cmdb_ci_server'),
                'filter': form_data.get('snow_filter', '').strip(),
                'auto_sync': form_data.get('snow_auto_sync') == 'on',
                'sync_frequency': form_data.get('snow_sync_frequency', 'manual'),
                'enabled': True
            }

            # Validate required fields
            if not config_data['instance'] or not config_data['username'] or not config_data['password']:
                return {
                    'success': False,
                    'error': 'Instance URL, username, and password are required'
                }

            log_info(f"Processed ServiceNow config for instance: {config_data['instance']}")
            return {
                'success': True,
                'config_data': config_data
            }

        except Exception as e:
            log_error(f"Error processing ServiceNow config: {e}")
            return {
                'success': False,
                'error': f"ServiceNow configuration error: {str(e)}"
            }

    def process_vault_config(self, form_data):
        """Process Vault configuration"""
        try:
            config_data = {
                'url': form_data.get('vault_url', '').strip().rstrip('/'),
                'token': form_data.get('vault_token', '').strip(),
                'mount_path': form_data.get('vault_mount_path', 'secret').strip(),
                'timeout': int(form_data.get('vault_timeout', 30)),
                'verify_ssl': form_data.get('vault_verify_ssl') == 'on',
                'enabled': True
            }

            # Validate required fields
            if not config_data['url'] or not config_data['token']:
                return {
                    'success': False,
                    'error': 'Vault URL and token are required'
                }

            log_info(f"Processed Vault config for URL: {config_data['url']}")
            return {
                'success': True,
                'config_data': config_data
            }

        except Exception as e:
            log_error(f"Error processing Vault config: {e}")
            return {
                'success': False,
                'error': f"Vault configuration error: {str(e)}"
            }

def get_form_defaults(form_type, **kwargs):
    """
    Get default values for forms
    Replaces JavaScript default value generation
    """
    if form_type == 'project':
        return {
            'project_guid': generate_guid(),
            'color_primary': '#2c3e50',
            'color_secondary': '#3498db',
            'status': 'active',
            'project_type': 'WebApp'
        }

    elif form_type == 'component':
        project_key = kwargs.get('project_key', 'PROJ')
        component_type = kwargs.get('component_type', 'webapp')
        component_name = kwargs.get('component_name', 'NewComponent')

        defaults = generate_default_values(component_type, component_name, project_key)
        defaults['component_guid'] = generate_project_component_guid(project_key, 1)
        return defaults

    elif form_type == 'msi_config':
        return {
            'app_version': '1.0.0.0',
            'manufacturer': 'Your Company',
            'upgrade_code': generate_guid(),
            'auto_increment_version': True,
            'app_pool_dotnet_version': 'v4.0',
            'app_pool_pipeline_mode': 'Integrated',
            'service_start_type': 'Automatic'
        }

    return {}