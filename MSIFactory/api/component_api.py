"""
Component API Module
API operations for component management
"""

import sys
import os
import logging
import time
from typing import Dict, List, Optional, Tuple

# Add parent directory to Python path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from database.db_manager_sqlserver import SQLServerDatabaseManager
    from database.models import Component
    from .system_logger import get_system_logger
except ImportError:
    # Fallback if database module not available
    SQLServerDatabaseManager = None
    Component = None

class ComponentAPI:
    """API class for component operations"""
    
    def __init__(self):
        """Initialize ComponentAPI with database connection"""
        self.logger = logging.getLogger(__name__)
        self.db = None
        
        try:
            if SQLServerDatabaseManager:
                self.db = SQLServerDatabaseManager()
                self.system_logger = get_system_logger()
                self.logger.info("ComponentAPI initialized with database connection")
                
                # Log system initialization
                self.system_logger.log_system_event(
                    event_name='COMPONENT_API_INIT',
                    event_source='COMPONENT_API',
                    event_level='INFO',
                    message='Component API initialized successfully'
                )
            else:
                self.logger.warning("Database manager not available")
                self.system_logger = None
        except Exception as e:
            self.logger.error(f"Failed to initialize database connection: {e}")
            if hasattr(self, 'system_logger') and self.system_logger:
                self.system_logger.log_error(
                    error=e,
                    module_name=__name__,
                    function_name='__init__'
                )
            self.system_logger = None
    
    # ==================== COMPONENT CRUD OPERATIONS ====================
    
    def get_all_components(self, project_id: Optional[int] = None) -> Tuple[bool, str, Optional[List[Dict]]]:
        """
        Get all components, optionally filtered by project
        
        Args:
            project_id: Optional project ID to filter components
            
        Returns:
            Tuple of (success, message, components_list)
        """
        try:
            if not self.db:
                return False, "Database not available", None
            
            components = []
            
            if project_id:
                # Get components for specific project
                query = """
                SELECT c.component_id, c.component_name, c.component_key, c.description,
                       c.component_type, c.file_path, c.install_path, c.guid,
                       c.project_id, p.project_name, c.created_date, c.modified_date,
                       c.is_active
                FROM Components c
                LEFT JOIN Projects p ON c.project_id = p.project_id
                WHERE c.project_id = ? AND c.is_active = 1
                ORDER BY c.component_name
                """
                results = self.db.execute_query(query, (project_id,))
            else:
                # Get all components
                query = """
                SELECT c.component_id, c.component_name, c.component_key, c.description,
                       c.component_type, c.file_path, c.install_path, c.guid,
                       c.project_id, p.project_name, c.created_date, c.modified_date,
                       c.is_active
                FROM Components c
                LEFT JOIN Projects p ON c.project_id = p.project_id
                WHERE c.is_active = 1
                ORDER BY c.component_name
                """
                results = self.db.execute_query(query)
            
            if results:
                for row in results:
                    component = {
                        'component_id': row[0],
                        'component_name': row[1],
                        'component_key': row[2],
                        'description': row[3],
                        'component_type': row[4],
                        'file_path': row[5],
                        'install_path': row[6],
                        'guid': row[7],
                        'project_id': row[8],
                        'project_name': row[9],
                        'created_date': row[10].isoformat() if row[10] else None,
                        'modified_date': row[11].isoformat() if row[11] else None,
                        'is_active': bool(row[12])
                    }
                    components.append(component)
            
            message = f"Found {len(components)} components"
            if project_id:
                message += f" for project {project_id}"
                
            return True, message, components
            
        except Exception as e:
            self.logger.error(f"Error getting components: {e}")
            return False, f"Error retrieving components: {str(e)}", None
    
    def get_component_by_id(self, component_id: int) -> Tuple[bool, str, Optional[Dict]]:
        """
        Get component by ID
        
        Args:
            component_id: Component ID
            
        Returns:
            Tuple of (success, message, component_dict)
        """
        try:
            if not self.db:
                return False, "Database not available", None
            
            query = """
            SELECT c.component_id, c.component_name, c.component_key, c.description,
                   c.component_type, c.file_path, c.install_path, c.guid,
                   c.project_id, p.project_name, c.created_date, c.modified_date,
                   c.is_active
            FROM Components c
            LEFT JOIN Projects p ON c.project_id = p.project_id
            WHERE c.component_id = ? AND c.is_active = 1
            """
            
            results = self.db.execute_query(query, (component_id,))
            
            if not results:
                return False, f"Component with ID {component_id} not found", None
            
            row = results[0]
            component = {
                'component_id': row[0],
                'component_name': row[1],
                'component_key': row[2],
                'description': row[3],
                'component_type': row[4],
                'file_path': row[5],
                'install_path': row[6],
                'guid': row[7],
                'project_id': row[8],
                'project_name': row[9],
                'created_date': row[10].isoformat() if row[10] else None,
                'modified_date': row[11].isoformat() if row[11] else None,
                'is_active': bool(row[12])
            }
            
            return True, f"Component {component_id} retrieved successfully", component
            
        except Exception as e:
            self.logger.error(f"Error getting component {component_id}: {e}")
            return False, f"Error retrieving component: {str(e)}", None
    
    def get_component_by_key(self, component_key: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        Get component by key
        
        Args:
            component_key: Component key
            
        Returns:
            Tuple of (success, message, component_dict)
        """
        try:
            if not self.db:
                return False, "Database not available", None
            
            query = """
            SELECT c.component_id, c.component_name, c.component_key, c.description,
                   c.component_type, c.file_path, c.install_path, c.guid,
                   c.project_id, p.project_name, c.created_date, c.modified_date,
                   c.is_active
            FROM Components c
            LEFT JOIN Projects p ON c.project_id = p.project_id
            WHERE c.component_key = ? AND c.is_active = 1
            """
            
            results = self.db.execute_query(query, (component_key,))
            
            if not results:
                return False, f"Component with key '{component_key}' not found", None
            
            row = results[0]
            component = {
                'component_id': row[0],
                'component_name': row[1],
                'component_key': row[2],
                'description': row[3],
                'component_type': row[4],
                'file_path': row[5],
                'install_path': row[6],
                'guid': row[7],
                'project_id': row[8],
                'project_name': row[9],
                'created_date': row[10].isoformat() if row[10] else None,
                'modified_date': row[11].isoformat() if row[11] else None,
                'is_active': bool(row[12])
            }
            
            return True, f"Component '{component_key}' retrieved successfully", component
            
        except Exception as e:
            self.logger.error(f"Error getting component by key {component_key}: {e}")
            return False, f"Error retrieving component: {str(e)}", None
    
    def create_component(self, data: Dict, user_id: str = 'system') -> Tuple[bool, str, Optional[int]]:
        """
        Create new component
        
        Args:
            data: Component data dictionary
            user_id: User creating the component
            
        Returns:
            Tuple of (success, message, component_id)
        """
        start_time = time.time()
        component_name = data.get('component_name', 'Unknown')
        component_key = data.get('component_key', 'Unknown')
        
        try:
            if not self.db:
                error_msg = "Database not available"
                if self.system_logger:
                    self.system_logger.log_action(
                        action_type='CREATE',
                        entity_type='component',
                        entity_name=component_name,
                        user_id=user_id,
                        success=False,
                        error_message=error_msg,
                        details={'component_key': component_key}
                    )
                return False, error_msg, None
            
            # Validate required fields
            required_fields = ['component_name', 'component_key', 'project_id']
            for field in required_fields:
                if not data.get(field):
                    duration_ms = int((time.time() - start_time) * 1000)
                    error_msg = f"Missing required field: {field}"
                    
                    if self.system_logger:
                        self.system_logger.log_action(
                            action_type='CREATE',
                            entity_type='component',
                            entity_name=component_name,
                            user_id=user_id,
                            success=False,
                            error_message=error_msg,
                            duration_ms=duration_ms,
                            details={'validation_error': field, 'data': data}
                        )
                    
                    return False, error_msg, None
            
            # Check if component key already exists
            check_query = "SELECT component_id FROM Components WHERE component_key = ?"
            existing = self.db.execute_query(check_query, (data['component_key'],))
            if existing:
                duration_ms = int((time.time() - start_time) * 1000)
                error_msg = f"Component with key '{data['component_key']}' already exists"
                
                if self.system_logger:
                    self.system_logger.log_action(
                        action_type='CREATE',
                        entity_type='component',
                        entity_name=component_name,
                        user_id=user_id,
                        success=False,
                        error_message=error_msg,
                        duration_ms=duration_ms,
                        details={'component_key': component_key, 'existing_id': existing[0][0]}
                    )
                
                return False, error_msg, None
            
            # Verify project exists
            project_check = "SELECT project_id FROM Projects WHERE project_id = ? AND is_active = 1"
            project_exists = self.db.execute_query(project_check, (data['project_id'],))
            if not project_exists:
                duration_ms = int((time.time() - start_time) * 1000)
                error_msg = f"Project with ID {data['project_id']} not found"
                
                if self.system_logger:
                    self.system_logger.log_action(
                        action_type='CREATE',
                        entity_type='component',
                        entity_name=component_name,
                        user_id=user_id,
                        success=False,
                        error_message=error_msg,
                        duration_ms=duration_ms,
                        details={'project_id': data['project_id'], 'component_key': component_key}
                    )
                
                return False, error_msg, None
            
            # Insert component
            insert_query = """
            INSERT INTO Components (
                component_name, component_key, description, component_type,
                file_path, install_path, guid, project_id, created_date, 
                modified_date, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, GETDATE(), GETDATE(), 1)
            """
            
            params = (
                data['component_name'],
                data['component_key'],
                data.get('description', ''),
                data.get('component_type', 'File'),
                data.get('file_path', ''),
                data.get('install_path', ''),
                data.get('guid', ''),
                data['project_id']
            )
            
            result = self.db.execute_non_query(insert_query, params)
            
            if result:
                # Get the new component ID
                id_query = "SELECT component_id FROM Components WHERE component_key = ?"
                id_result = self.db.execute_query(id_query, (data['component_key'],))
                component_id = id_result[0][0] if id_result else None
                
                duration_ms = int((time.time() - start_time) * 1000)
                success_msg = f"Component '{data['component_name']}' created successfully"
                
                # Log successful creation
                if self.system_logger:
                    self.system_logger.log_action(
                        action_type='CREATE',
                        entity_type='component',
                        entity_id=str(component_id) if component_id else None,
                        entity_name=data['component_name'],
                        user_id=user_id,
                        success=True,
                        duration_ms=duration_ms,
                        new_values={
                            'component_name': data['component_name'],
                            'component_key': data['component_key'],
                            'component_type': data.get('component_type', 'File'),
                            'project_id': data['project_id'],
                            'file_path': data.get('file_path', ''),
                            'install_path': data.get('install_path', '')
                        },
                        details={
                            'component_id': component_id,
                            'description': data.get('description', ''),
                            'guid': data.get('guid', '')
                        }
                    )
                    
                    # Log audit event for compliance
                    self.system_logger.log_audit(
                        event_type='COMPONENT_CREATED',
                        event_category='DATA',
                        severity='INFO',
                        resource_type='component',
                        resource_id=str(component_id) if component_id else None,
                        resource_name=data['component_name'],
                        action_performed='CREATE_COMPONENT',
                        action_result='SUCCESS',
                        user_id=user_id,
                        reason='New component creation',
                        compliance_flags='DATA_CREATION',
                        data_classification='INTERNAL',
                        additional_metadata={
                            'project_id': data['project_id'],
                            'component_type': data.get('component_type', 'File')
                        }
                    )
                
                return True, success_msg, component_id
            else:
                duration_ms = int((time.time() - start_time) * 1000)
                error_msg = "Failed to create component"
                
                if self.system_logger:
                    self.system_logger.log_action(
                        action_type='CREATE',
                        entity_type='component',
                        entity_name=component_name,
                        user_id=user_id,
                        success=False,
                        error_message=error_msg,
                        duration_ms=duration_ms,
                        details={'component_key': component_key, 'data': data}
                    )
                
                return False, error_msg, None
                
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Error creating component: {str(e)}"
            
            # Log failed action
            if self.system_logger:
                self.system_logger.log_action(
                    action_type='CREATE',
                    entity_type='component',
                    entity_name=component_name,
                    user_id=user_id,
                    success=False,
                    error_message=str(e),
                    duration_ms=duration_ms,
                    details={'component_key': component_key, 'data': data}
                )
                
                # Log error details
                self.system_logger.log_error(
                    error=e,
                    module_name=__name__,
                    function_name='create_component',
                    user_id=user_id,
                    context={'operation': 'create_component', 'data': data}
                )
            
            self.logger.error(f"Error creating component: {e}")
            return False, error_msg, None
    
    def update_component(self, component_id: int, data: Dict) -> Tuple[bool, str]:
        """
        Update existing component
        
        Args:
            component_id: Component ID
            data: Updated component data
            
        Returns:
            Tuple of (success, message)
        """
        try:
            if not self.db:
                return False, "Database not available"
            
            # Check if component exists
            check_query = "SELECT component_id FROM Components WHERE component_id = ? AND is_active = 1"
            existing = self.db.execute_query(check_query, (component_id,))
            if not existing:
                return False, f"Component with ID {component_id} not found"
            
            # Build update query dynamically
            update_fields = []
            params = []
            
            updatable_fields = [
                'component_name', 'component_key', 'description', 'component_type',
                'file_path', 'install_path', 'guid', 'project_id'
            ]
            
            for field in updatable_fields:
                if field in data:
                    update_fields.append(f"{field} = ?")
                    params.append(data[field])
            
            if not update_fields:
                return False, "No valid fields to update"
            
            # Always update modified_date
            update_fields.append("modified_date = GETDATE()")
            params.append(component_id)
            
            update_query = f"""
            UPDATE Components 
            SET {', '.join(update_fields)}
            WHERE component_id = ?
            """
            
            result = self.db.execute_non_query(update_query, params)
            
            if result:
                return True, f"Component {component_id} updated successfully"
            else:
                return False, "Failed to update component"
                
        except Exception as e:
            self.logger.error(f"Error updating component {component_id}: {e}")
            return False, f"Error updating component: {str(e)}"
    
    def delete_component(self, component_id: int, hard_delete: bool = False) -> Tuple[bool, str]:
        """
        Delete component (soft delete by default)
        
        Args:
            component_id: Component ID
            hard_delete: True for permanent deletion, False for soft delete
            
        Returns:
            Tuple of (success, message)
        """
        try:
            if not self.db:
                return False, "Database not available"
            
            # Check if component exists
            check_query = "SELECT component_name FROM Components WHERE component_id = ?"
            existing = self.db.execute_query(check_query, (component_id,))
            if not existing:
                return False, f"Component with ID {component_id} not found"
            
            component_name = existing[0][0]
            
            if hard_delete:
                # Permanent deletion
                delete_query = "DELETE FROM Components WHERE component_id = ?"
                action = "permanently deleted"
            else:
                # Soft delete
                delete_query = "UPDATE Components SET is_active = 0, modified_date = GETDATE() WHERE component_id = ?"
                action = "archived"
            
            result = self.db.execute_non_query(delete_query, (component_id,))
            
            if result:
                return True, f"Component '{component_name}' {action} successfully"
            else:
                return False, f"Failed to delete component"
                
        except Exception as e:
            self.logger.error(f"Error deleting component {component_id}: {e}")
            return False, f"Error deleting component: {str(e)}"