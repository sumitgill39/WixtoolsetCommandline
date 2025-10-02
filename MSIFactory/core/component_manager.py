#!/usr/bin/env python3
"""
Component Manager - Complete Component Operations Handler
Handles ALL component operations for MSI Factory (replaces JavaScript functionality)
"""

import pyodbc
import logging
import re
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from core.utilities import generate_guid, generate_project_component_guid


class ComponentManager:
    """Complete component management system - handles all component operations"""

    def __init__(self):
        self.conn_str = (
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=SUMEETGILL7E47\\MSSQLSERVER01;"
            "DATABASE=MSIFactory;"
            "Trusted_Connection=yes;"
            "Connection Timeout=10;"
        )

        # Component type field mappings - defines which fields are relevant for each type
        self.COMPONENT_TYPE_FIELDS = {
            'webapp': {
                'core_fields': ['component_name', 'component_type', 'framework', 'description', 'app_name', 'app_version', 'manufacturer', 'target_server', 'install_folder', 'artifact_url'],
                'specific_fields': ['iis_website_name', 'iis_app_pool_name', 'port'],
                'excluded_fields': ['service_name', 'service_display_name']
            },
            'website': {
                'core_fields': ['component_name', 'component_type', 'framework', 'description', 'app_name', 'app_version', 'manufacturer', 'target_server', 'install_folder', 'artifact_url'],
                'specific_fields': ['iis_website_name', 'iis_app_pool_name', 'port'],
                'excluded_fields': ['service_name', 'service_display_name']
            },
            'api': {
                'core_fields': ['component_name', 'component_type', 'framework', 'description', 'app_name', 'app_version', 'manufacturer', 'target_server', 'install_folder', 'artifact_url'],
                'specific_fields': ['iis_website_name', 'iis_app_pool_name', 'port'],
                'excluded_fields': ['service_name', 'service_display_name']
            },
            'service': {
                'core_fields': ['component_name', 'component_type', 'framework', 'description', 'app_name', 'app_version', 'manufacturer', 'target_server', 'install_folder', 'artifact_url'],
                'specific_fields': ['service_name', 'service_display_name'],
                'excluded_fields': ['iis_website_name', 'iis_app_pool_name', 'port']
            },
            'scheduler': {
                'core_fields': ['component_name', 'component_type', 'framework', 'description', 'app_name', 'app_version', 'manufacturer', 'target_server', 'install_folder', 'artifact_url'],
                'specific_fields': ['service_name', 'service_display_name'],
                'excluded_fields': ['iis_website_name', 'iis_app_pool_name', 'port']
            },
            'desktop': {
                'core_fields': ['component_name', 'component_type', 'framework', 'description', 'app_name', 'app_version', 'manufacturer', 'target_server', 'install_folder', 'artifact_url'],
                'specific_fields': [],
                'excluded_fields': ['iis_website_name', 'iis_app_pool_name', 'port', 'service_name', 'service_display_name']
            },
            'library': {
                'core_fields': ['component_name', 'component_type', 'framework', 'description', 'app_name', 'app_version', 'manufacturer', 'target_server', 'install_folder', 'artifact_url'],
                'specific_fields': [],
                'excluded_fields': ['iis_website_name', 'iis_app_pool_name', 'port', 'service_name', 'service_display_name']
            }
        }

    # =================== COMPONENT TYPE HELPERS ===================

    def get_relevant_fields_for_type(self, component_type: str) -> List[str]:
        """Get all relevant fields for a component type"""
        if component_type not in self.COMPONENT_TYPE_FIELDS:
            return []

        config = self.COMPONENT_TYPE_FIELDS[component_type]
        return config['core_fields'] + config['specific_fields']

    def get_excluded_fields_for_type(self, component_type: str) -> List[str]:
        """Get fields that should be excluded/ignored for a component type"""
        if component_type not in self.COMPONENT_TYPE_FIELDS:
            return []

        return self.COMPONENT_TYPE_FIELDS[component_type]['excluded_fields']

    def clean_component_data_for_type(self, component_data: Dict, component_type: str) -> Dict:
        """Clean component data by setting excluded fields to None for the given type"""
        cleaned_data = component_data.copy()
        excluded_fields = self.get_excluded_fields_for_type(component_type)

        for field in excluded_fields:
            if field in cleaned_data:
                cleaned_data[field] = None

        return cleaned_data

    def validate_required_fields_for_type(self, component_data: Dict, component_type: str) -> Tuple[bool, List[str]]:
        """Validate that required fields are present for the component type"""
        errors = []

        if component_type not in self.COMPONENT_TYPE_FIELDS:
            errors.append(f"Unsupported component type: {component_type}")
            return False, errors

        config = self.COMPONENT_TYPE_FIELDS[component_type]
        required_core_fields = ['component_name', 'component_type', 'framework']

        for field in required_core_fields:
            if not component_data.get(field):
                errors.append(f"{field.replace('_', ' ').title()} is required")

        # Type-specific validation
        if component_type in ['webapp', 'website', 'api']:
            if component_data.get('port'):
                try:
                    port = int(component_data['port'])
                    if port < 1 or port > 65535:
                        errors.append("Port must be between 1 and 65535")
                except (ValueError, TypeError):
                    errors.append("Port must be a valid number")

        return len(errors) == 0, errors

    # =================== COMPONENT CRUD OPERATIONS ===================

    def create_component(self, project_id: int, component_data: Dict, username: str = 'system') -> Tuple[bool, str, Optional[int]]:
        """Create a new component with all validation"""
        try:
            # Validate component type and required fields
            component_type = component_data.get('component_type')
            is_valid, validation_errors = self.validate_required_fields_for_type(component_data, component_type)

            if not is_valid:
                return False, "Validation errors: " + "; ".join(validation_errors), None

            # Clean component data for the specific type (set excluded fields to None)
            cleaned_data = self.clean_component_data_for_type(component_data, component_type)

            # Use provided GUID or generate new one
            component_guid = component_data.get('component_guid', '').strip()
            if not component_guid:
                component_guid = self.generate_component_guid(project_id, component_data.get('component_name'))
            else:
                # Ensure provided GUID is unique
                component_guid = self.ensure_unique_guid(component_guid)

            with pyodbc.connect(self.conn_str) as conn:
                with conn.cursor() as cursor:
                    # Insert new component
                    cursor.execute("""
                        INSERT INTO components (
                            project_id, component_name, component_type, framework,
                            component_guid, app_name, app_version, manufacturer,
                            install_folder, iis_website_name, iis_app_pool_name, port,
                            service_name, service_display_name, description,
                            is_enabled, created_by, created_date
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE())
                    """, (
                        project_id,
                        cleaned_data.get('component_name'),
                        cleaned_data.get('component_type'),
                        cleaned_data.get('framework'),
                        component_guid,
                        cleaned_data.get('app_name', cleaned_data.get('component_name')),
                        cleaned_data.get('app_version', '1.0.0.0'),
                        cleaned_data.get('manufacturer', 'Your Company'),
                        cleaned_data.get('install_folder', ''),
                        cleaned_data.get('iis_website_name', None),
                        cleaned_data.get('iis_app_pool_name', None),
                        cleaned_data.get('port', None),
                        cleaned_data.get('service_name', None),
                        cleaned_data.get('service_display_name', None),
                        cleaned_data.get('description', ''),
                        cleaned_data.get('is_enabled', False),  # Default to disabled for safety
                        username
                    ))

                    # Get the new component ID
                    cursor.execute("SELECT @@IDENTITY")
                    component_id = cursor.fetchone()[0]
                    conn.commit()

                    logging.info(f"Component '{component_data.get('component_name')}' created by {username}")
                    return True, f"Component '{component_data.get('component_name')}' created successfully", component_id

        except Exception as e:
            error_msg = f"Error creating component: {str(e)}"
            logging.error(error_msg)
            return False, error_msg, None

    def update_component(self, component_id: int, project_id: int, component_data: Dict, username: str = 'system') -> Tuple[bool, str]:
        """Update existing component with validation"""
        try:
            # Validate component exists
            existing_component = self.get_component_by_id(component_id, project_id)
            if not existing_component:
                return False, "Component not found"

            with pyodbc.connect(self.conn_str) as conn:
                with conn.cursor() as cursor:
                    # Component GUID is immutable - use existing GUID
                    component_guid = existing_component.get('component_guid')

                    cursor.execute("""
                        UPDATE components SET
                            component_name = ?, component_type = ?, framework = ?, component_guid = ?,
                            app_name = ?, app_version = ?, manufacturer = ?,
                            install_folder = ?, iis_website_name = ?, iis_app_pool_name = ?,
                            port = ?, service_name = ?, service_display_name = ?,
                            description = ?, is_enabled = ?,
                            updated_date = GETDATE(), updated_by = ?
                        WHERE component_id = ? AND project_id = ?
                    """, (
                        component_data.get('component_name', existing_component['component_name']),
                        component_data.get('component_type', existing_component['component_type']),
                        component_data.get('framework', existing_component['framework']),
                        component_guid,
                        component_data.get('app_name', existing_component['app_name']),
                        component_data.get('app_version', existing_component['app_version']),
                        component_data.get('manufacturer', existing_component['manufacturer']),
                        component_data.get('install_folder', existing_component['install_folder']),
                        component_data.get('iis_website_name', existing_component['iis_website_name']),
                        component_data.get('iis_app_pool_name', existing_component['iis_app_pool_name']),
                        component_data.get('port', existing_component['port']),
                        component_data.get('service_name', existing_component['service_name']),
                        component_data.get('service_display_name', existing_component['service_display_name']),
                        component_data.get('description', existing_component['description']),
                        component_data.get('is_enabled', existing_component['is_enabled']),
                        username,
                        component_id,
                        project_id
                    ))

                    if cursor.rowcount > 0:
                        conn.commit()
                        logging.info(f"Component {component_id} updated by {username}")
                        return True, "Component updated successfully"
                    else:
                        return False, "No changes made"

        except Exception as e:
            error_msg = f"Error updating component: {str(e)}"
            logging.error(error_msg)
            return False, error_msg

    def toggle_component_status(self, component_id: int, is_enabled: bool, username: str = 'system') -> Tuple[bool, str]:
        """Toggle component status between Active (is_enabled=True) and Inactive (is_enabled=False)"""
        try:
            with pyodbc.connect(self.conn_str) as conn:
                with conn.cursor() as cursor:
                    # Update component status
                    cursor.execute("""
                        UPDATE components
                        SET is_enabled = ?, updated_date = GETDATE(), updated_by = ?
                        WHERE component_id = ?
                    """, (is_enabled, username, component_id))

                    if cursor.rowcount > 0:
                        conn.commit()
                        status_text = "activated" if is_enabled else "deactivated"
                        logging.info(f"Component {component_id} {status_text} by {username}")
                        return True, f"Component {status_text} successfully"
                    else:
                        return False, "Component not found"

        except Exception as e:
            error_msg = f"Error updating component status: {str(e)}"
            logging.error(error_msg)
            return False, error_msg

    # =================== COMPONENT RETRIEVAL ===================

    def get_component_by_id(self, component_id: int, project_id: Optional[int] = None) -> Optional[Dict]:
        """Get component by ID with optional project validation"""
        try:
            with pyodbc.connect(self.conn_str) as conn:
                with conn.cursor() as cursor:
                    if project_id:
                        cursor.execute("""
                            SELECT component_id, component_name, component_type, framework,
                                   component_guid, app_name, app_version, manufacturer,
                                   install_folder, iis_website_name, iis_app_pool_name, port,
                                   service_name, service_display_name, description, is_enabled,
                                   created_date, created_by, updated_date, updated_by, project_id
                            FROM components
                            WHERE component_id = ? AND project_id = ?
                        """, (component_id, project_id))
                    else:
                        cursor.execute("""
                            SELECT component_id, component_name, component_type, framework,
                                   component_guid, app_name, app_version, manufacturer,
                                   install_folder, iis_website_name, iis_app_pool_name, port,
                                   service_name, service_display_name, description, is_enabled,
                                   created_date, created_by, updated_date, updated_by, project_id
                            FROM components
                            WHERE component_id = ?
                        """, (component_id,))

                    row = cursor.fetchone()
                    if row:
                        return {
                            'component_id': row[0],
                            'component_name': row[1],
                            'component_type': row[2],
                            'framework': row[3],
                            'component_guid': row[4],
                            'app_name': row[5],
                            'app_version': row[6],
                            'manufacturer': row[7],
                            'install_folder': row[8],
                            'iis_website_name': row[9],
                            'iis_app_pool_name': row[10],
                            'port': row[11],
                            'service_name': row[12],
                            'service_display_name': row[13],
                            'description': row[14],
                            'is_enabled': row[15],
                            'created_date': row[16],
                            'created_by': row[17],
                            'updated_date': row[18],
                            'updated_by': row[19],
                            'project_id': row[20]
                        }
                    return None

        except Exception as e:
            logging.error(f"Error getting component by ID: {str(e)}")
            return None

    def get_project_components(self, project_id: int, include_disabled: bool = True) -> List[Dict]:
        """Get all components for a project"""
        try:
            with pyodbc.connect(self.conn_str) as conn:
                with conn.cursor() as cursor:
                    query = """
                        SELECT component_id, component_name, component_type, framework,
                               component_guid, app_name, app_version, manufacturer,
                               install_folder, iis_website_name, iis_app_pool_name, port,
                               service_name, service_display_name, description, is_enabled,
                               created_date, created_by
                        FROM components
                        WHERE project_id = ?
                    """

                    if not include_disabled:
                        query += " AND is_enabled = 1"

                    query += " ORDER BY component_name"

                    cursor.execute(query, (project_id,))

                    components = []
                    for row in cursor.fetchall():
                        components.append({
                            'component_id': row[0],
                            'component_name': row[1],
                            'component_type': row[2],
                            'framework': row[3],
                            'component_guid': row[4],
                            'app_name': row[5],
                            'app_version': row[6],
                            'manufacturer': row[7],
                            'install_folder': row[8],
                            'iis_website_name': row[9],
                            'iis_app_pool_name': row[10],
                            'port': row[11],
                            'service_name': row[12],
                            'service_display_name': row[13],
                            'description': row[14],
                            'is_enabled': row[15],
                            'created_date': row[16],
                            'created_by': row[17]
                        })

                    return components

        except Exception as e:
            logging.error(f"Error getting project components: {str(e)}")
            return []

    # =================== COMPONENT STATUS OPERATIONS ===================

    def toggle_component_status(self, component_id: int, project_id: int, username: str = 'system') -> Tuple[bool, str]:
        """Toggle the enabled/disabled status of a component"""
        try:
            current_component = self.get_component_by_id(component_id, project_id)
            if not current_component:
                return False, "Component not found"

            new_status = not current_component['is_enabled']
            return self.set_component_status(component_id, project_id, new_status, username)

        except Exception as e:
            error_msg = f"Error toggling component status: {str(e)}"
            logging.error(error_msg)
            return False, error_msg

    def set_component_status(self, component_id: int, project_id: int, enabled_status: bool, username: str = 'system') -> Tuple[bool, str]:
        """Set the enabled/disabled status of a component"""
        try:
            with pyodbc.connect(self.conn_str) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE components
                        SET is_enabled = ?, updated_date = GETDATE(), updated_by = ?
                        WHERE component_id = ? AND project_id = ?
                    """, (enabled_status, username, component_id, project_id))

                    if cursor.rowcount > 0:
                        conn.commit()
                        status_text = "enabled" if enabled_status else "disabled"
                        logging.info(f"Component {component_id} set to {status_text} by {username}")
                        return True, f"Component {status_text} successfully"
                    else:
                        return False, "Component not found or no changes made"

        except Exception as e:
            error_msg = f"Error setting component status: {str(e)}"
            logging.error(error_msg)
            return False, error_msg

    def bulk_enable_components(self, component_ids: List[int], project_id: int, username: str = 'system') -> Tuple[bool, str]:
        """Enable multiple components at once"""
        try:
            with pyodbc.connect(self.conn_str) as conn:
                with conn.cursor() as cursor:
                    placeholders = ','.join(['?' for _ in component_ids])
                    query = f"""
                        UPDATE components
                        SET is_enabled = 1, updated_date = GETDATE(), updated_by = ?
                        WHERE component_id IN ({placeholders}) AND project_id = ?
                    """

                    params = [username] + component_ids + [project_id]
                    cursor.execute(query, params)

                    count = cursor.rowcount
                    if count > 0:
                        conn.commit()
                        logging.info(f"{count} components enabled by {username}")
                        return True, f"{count} components enabled successfully"
                    else:
                        return False, "No components were updated"

        except Exception as e:
            error_msg = f"Error bulk enabling components: {str(e)}"
            logging.error(error_msg)
            return False, error_msg

    def bulk_disable_components(self, component_ids: List[int], project_id: int, username: str = 'system') -> Tuple[bool, str]:
        """Disable multiple components at once"""
        try:
            with pyodbc.connect(self.conn_str) as conn:
                with conn.cursor() as cursor:
                    placeholders = ','.join(['?' for _ in component_ids])
                    query = f"""
                        UPDATE components
                        SET is_enabled = 0, updated_date = GETDATE(), updated_by = ?
                        WHERE component_id IN ({placeholders}) AND project_id = ?
                    """

                    params = [username] + component_ids + [project_id]
                    cursor.execute(query, params)

                    count = cursor.rowcount
                    if count > 0:
                        conn.commit()
                        logging.info(f"{count} components disabled by {username}")
                        return True, f"{count} components disabled successfully"
                    else:
                        return False, "No components were updated"

        except Exception as e:
            error_msg = f"Error bulk disabling components: {str(e)}"
            logging.error(error_msg)
            return False, error_msg

    # =================== GUID GENERATION AND VALIDATION ===================

    def generate_component_guid(self, project_id: int, component_name: str = None) -> str:
        """Generate a unique GUID for a component"""
        try:
            # Get project key for GUID generation
            project_key = self.get_project_key(project_id)

            # Get component counter
            component_counter = self.get_next_component_counter(project_id)

            # Use the new utility function for consistent GUID generation
            if project_key:
                component_guid = generate_project_component_guid(project_key, component_counter)
            else:
                component_guid = generate_guid()

            # Ensure uniqueness
            return self.ensure_unique_guid(component_guid)

        except Exception as e:
            logging.error(f"Error generating component GUID: {str(e)}")
            return generate_guid()

    def get_project_key(self, project_id: int) -> Optional[str]:
        """Get project key for GUID generation"""
        try:
            with pyodbc.connect(self.conn_str) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT project_key FROM projects WHERE project_id = ?", (project_id,))
                    row = cursor.fetchone()
                    return row[0] if row else None
        except:
            return None

    def get_next_component_counter(self, project_id: int) -> int:
        """Get the next component counter for a project"""
        try:
            with pyodbc.connect(self.conn_str) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT COUNT(*) FROM components WHERE project_id = ?", (project_id,))
                    count = cursor.fetchone()[0]
                    return count + 1
        except:
            return 1

    def ensure_unique_guid(self, proposed_guid: str) -> str:
        """Ensure the GUID is unique in the database"""
        try:
            with pyodbc.connect(self.conn_str) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT COUNT(*) FROM components WHERE component_guid = ?", (proposed_guid,))
                    count = cursor.fetchone()[0]

                    if count == 0:
                        return proposed_guid
                    else:
                        # Generate a new GUID if collision
                        return generate_guid()
        except:
            return generate_guid()

    def regenerate_component_guid(self, component_id: int, project_id: int, username: str = 'system') -> Tuple[bool, str, Optional[str]]:
        """Regenerate GUID for an existing component"""
        try:
            component = self.get_component_by_id(component_id, project_id)
            if not component:
                return False, "Component not found", None

            new_guid = self.generate_component_guid(project_id, component['component_name'])

            with pyodbc.connect(self.conn_str) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE components
                        SET component_guid = ?, updated_date = GETDATE(), updated_by = ?
                        WHERE component_id = ? AND project_id = ?
                    """, (new_guid, username, component_id, project_id))

                    if cursor.rowcount > 0:
                        conn.commit()
                        logging.info(f"Component {component_id} GUID regenerated by {username}")
                        return True, "GUID regenerated successfully", new_guid
                    else:
                        return False, "Failed to update GUID", None

        except Exception as e:
            error_msg = f"Error regenerating component GUID: {str(e)}"
            logging.error(error_msg)
            return False, error_msg, None

    # =================== COMPONENT VALIDATION ===================

    def validate_component_data(self, component_data: Dict) -> Tuple[bool, List[str]]:
        """Validate component data and return errors if any"""
        errors = []

        # Required fields validation
        if not component_data.get('component_name', '').strip():
            errors.append("Component name is required")

        if not component_data.get('component_type'):
            errors.append("Component type is required")

        if not component_data.get('framework'):
            errors.append("Framework is required")

        # Component name validation
        component_name = component_data.get('component_name', '').strip()
        if component_name:
            if len(component_name) < 2:
                errors.append("Component name must be at least 2 characters")
            if len(component_name) > 100:
                errors.append("Component name must be less than 100 characters")
            if not re.match(r'^[a-zA-Z0-9_\-\s]+$', component_name):
                errors.append("Component name can only contain letters, numbers, spaces, hyphens, and underscores")

        # Version validation
        app_version = component_data.get('app_version', '')
        if app_version and not re.match(r'^\d+\.\d+\.\d+\.\d+$', app_version):
            errors.append("Version must be in format X.Y.Z.W (e.g., 1.0.0.0)")

        # Port validation
        port = component_data.get('port')
        if port:
            try:
                port_num = int(port)
                if port_num < 1 or port_num > 65535:
                    errors.append("Port must be between 1 and 65535")
            except ValueError:
                errors.append("Port must be a valid number")

        # Component type specific validations
        component_type = component_data.get('component_type')
        if component_type in ['webapp', 'website', 'api']:
            if not component_data.get('iis_website_name'):
                errors.append("IIS Website name is required for web components")

        if component_type == 'service':
            if not component_data.get('service_name'):
                errors.append("Service name is required for Windows services")

        return len(errors) == 0, errors

    def validate_component_name_unique(self, component_name: str, project_id: int, exclude_component_id: Optional[int] = None) -> bool:
        """Check if component name is unique within project"""
        try:
            with pyodbc.connect(self.conn_str) as conn:
                with conn.cursor() as cursor:
                    if exclude_component_id:
                        cursor.execute("""
                            SELECT COUNT(*) FROM components
                            WHERE project_id = ? AND component_name = ? AND component_id != ?
                        """, (project_id, component_name, exclude_component_id))
                    else:
                        cursor.execute("""
                            SELECT COUNT(*) FROM components
                            WHERE project_id = ? AND component_name = ?
                        """, (project_id, component_name))

                    count = cursor.fetchone()[0]
                    return count == 0

        except Exception as e:
            logging.error(f"Error validating component name uniqueness: {str(e)}")
            return False

    # =================== COMPONENT TYPE OPERATIONS ===================

    def get_supported_component_types(self) -> List[Dict[str, str]]:
        """Get list of supported component types"""
        return [
            {'value': 'webapp', 'label': 'Web Application', 'icon': 'fa-globe'},
            {'value': 'website', 'label': 'Website', 'icon': 'fa-window-restore'},
            {'value': 'service', 'label': 'Windows Service', 'icon': 'fa-cogs'},
            {'value': 'api', 'label': 'API Service', 'icon': 'fa-plug'},
            {'value': 'scheduler', 'label': 'Scheduler', 'icon': 'fa-clock'},
            {'value': 'desktop', 'label': 'Desktop Application', 'icon': 'fa-desktop'},
            {'value': 'library', 'label': 'Library/DLL', 'icon': 'fa-book'}
        ]

    def get_supported_frameworks(self) -> List[Dict[str, str]]:
        """Get list of supported frameworks"""
        return [
            {'value': 'netframework', 'label': '.NET Framework'},
            {'value': 'netcore', 'label': '.NET Core/.NET 5+'},
            {'value': 'react', 'label': 'React'},
            {'value': 'angular', 'label': 'Angular'},
            {'value': 'vue', 'label': 'Vue.js'},
            {'value': 'python', 'label': 'Python'},
            {'value': 'nodejs', 'label': 'Node.js'},
            {'value': 'static', 'label': 'Static HTML'}
        ]

    # =================== COMPONENT STATISTICS ===================

    def get_component_statistics(self, project_id: Optional[int] = None) -> Dict[str, Any]:
        """Get component statistics"""
        try:
            with pyodbc.connect(self.conn_str) as conn:
                with conn.cursor() as cursor:
                    if project_id:
                        # Project-specific statistics
                        cursor.execute("""
                            SELECT
                                COUNT(*) as total_components,
                                SUM(CASE WHEN is_enabled = 1 THEN 1 ELSE 0 END) as enabled_components,
                                SUM(CASE WHEN is_enabled = 0 THEN 1 ELSE 0 END) as disabled_components
                            FROM components WHERE project_id = ?
                        """, (project_id,))

                        row = cursor.fetchone()
                        stats = {
                            'total_components': row[0],
                            'enabled_components': row[1],
                            'disabled_components': row[2]
                        }

                        # Component type breakdown
                        cursor.execute("""
                            SELECT component_type, COUNT(*) as count
                            FROM components
                            WHERE project_id = ?
                            GROUP BY component_type
                        """, (project_id,))

                        type_breakdown = {}
                        for row in cursor.fetchall():
                            type_breakdown[row[0]] = row[1]

                        stats['type_breakdown'] = type_breakdown

                    else:
                        # Global statistics
                        cursor.execute("""
                            SELECT
                                COUNT(*) as total_components,
                                SUM(CASE WHEN is_enabled = 1 THEN 1 ELSE 0 END) as enabled_components,
                                SUM(CASE WHEN is_enabled = 0 THEN 1 ELSE 0 END) as disabled_components
                            FROM components
                        """)

                        row = cursor.fetchone()
                        stats = {
                            'total_components': row[0],
                            'enabled_components': row[1],
                            'disabled_components': row[2]
                        }

                    return stats

        except Exception as e:
            logging.error(f"Error getting component statistics: {str(e)}")
            return {
                'total_components': 0,
                'enabled_components': 0,
                'disabled_components': 0,
                'type_breakdown': {}
            }


# =================== UTILITY FUNCTIONS ===================

def get_component_manager() -> ComponentManager:
    """Get a ComponentManager instance"""
    return ComponentManager()

# Quick access functions
def toggle_component(component_id: int, project_id: int, username: str = 'system') -> Tuple[bool, str]:
    """Quick function to toggle a component's status"""
    manager = ComponentManager()
    return manager.toggle_component_status(component_id, project_id, username)

def enable_component(component_id: int, project_id: int, username: str = 'system') -> Tuple[bool, str]:
    """Quick function to enable a component"""
    manager = ComponentManager()
    return manager.set_component_status(component_id, project_id, True, username)

def disable_component(component_id: int, project_id: int, username: str = 'system') -> Tuple[bool, str]:
    """Quick function to disable a component"""
    manager = ComponentManager()
    return manager.set_component_status(component_id, project_id, False, username)

def create_component(project_id: int, component_data: Dict, username: str = 'system') -> Tuple[bool, str, Optional[int]]:
    """Quick function to create a component"""
    manager = ComponentManager()
    return manager.create_component(project_id, component_data, username)

def toggle_component_status(component_id: int, is_enabled: bool, username: str = 'system') -> Tuple[bool, str]:
    """Quick function to toggle component status"""
    manager = ComponentManager()
    return manager.toggle_component_status(component_id, is_enabled, username)

def get_project_components(project_id: int, include_disabled: bool = True) -> List[Dict]:
    """Quick function to get project components"""
    manager = ComponentManager()
    return manager.get_project_components(project_id, include_disabled)

def validate_component(component_data: Dict) -> Tuple[bool, List[str]]:
    """Quick function to validate component data"""
    manager = ComponentManager()
    return manager.validate_component_data(component_data)