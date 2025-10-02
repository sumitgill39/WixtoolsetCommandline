"""
Project API Module
Independent API for all project-related database operations
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import List, Dict, Optional, Tuple
from database.db_manager_sqlserver import SQLServerDatabaseManager
from database.models import Project, ProjectEnvironment, User
import uuid
import logging
import time
from .simple_logger import get_simple_logger

class ProjectAPI:
    """API for project management operations"""
    
    def __init__(self):
        """Initialize Project API with database connection"""
        self.logger = logging.getLogger(__name__)
        self.simple_logger = get_simple_logger()
        try:
            self.db = SQLServerDatabaseManager()
            self.logger.info("Project API initialized with database connection")
            self.simple_logger.log_action("INIT", "project_api", success=True)
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            self.simple_logger.log_action("INIT", "project_api", success=False, error=str(e))
            self.db = None
    
    # ==================== CREATE ====================
    
    def create_project(self, data: Dict) -> Tuple[bool, str, Optional[int]]:
        """
        Create a new project
        
        Args:
            data: Dictionary containing project details
                - project_name (required)
                - project_key (required)
                - description
                - project_type
                - owner_team
                - status
                - created_by
        
        Returns:
            Tuple of (success, message, project_id)
        """
        start_time = time.time()
        project_name = data.get('project_name', 'Unknown')
        project_key = data.get('project_key', 'Unknown')
        user_id = data.get('created_by', 'system')
        
        if not self.db:
            error_msg = "Database not available"
            self.system_logger.log_action(
                action_type='CREATE',
                entity_type='project',
                entity_name=project_name,
                user_id=user_id,
                success=False,
                error_message=error_msg,
                details={'project_key': project_key}
            )
            return False, error_msg, None
        
        try:
            with self.db.get_session() as session:
                # Check if project key already exists
                existing = session.query(Project).filter_by(
                    project_key=data.get('project_key')
                ).first()
                
                if existing:
                    error_msg = f"Project with key '{data['project_key']}' already exists"
                    duration_ms = int((time.time() - start_time) * 1000)
                    
                    self.system_logger.log_action(
                        action_type='CREATE',
                        entity_type='project',
                        entity_name=project_name,
                        user_id=user_id,
                        success=False,
                        error_message=error_msg,
                        duration_ms=duration_ms,
                        details={'project_key': project_key, 'conflict_with_existing': True}
                    )
                    
                    # Log audit event for security
                    self.system_logger.log_audit(
                        event_type='PROJECT_CREATE_CONFLICT',
                        event_category='DATA',
                        severity='LOW',
                        resource_type='project',
                        resource_id=project_key,
                        action_performed='CREATE_PROJECT',
                        action_result='DENIED_DUPLICATE_KEY',
                        user_id=user_id,
                        reason='Project key already exists'
                    )
                    
                    return False, error_msg, None
                
                # Create new project
                project = Project(
                    project_name=data.get('project_name'),
                    project_key=data.get('project_key'),
                    description=data.get('description', ''),
                    project_type=data.get('project_type', 'WebApp'),
                    owner_team=data.get('owner_team', ''),
                    status=data.get('status', 'active'),
                    color_primary=data.get('color_primary', '#2c3e50'),
                    color_secondary=data.get('color_secondary', '#3498db'),
                    created_by=data.get('created_by', 'system')
                )
                
                session.add(project)
                session.flush()  # Get the project_id before commit
                project_id = project.project_id
                session.commit()
                
                duration_ms = int((time.time() - start_time) * 1000)
                success_msg = f"Project '{project.project_name}' created successfully"
                
                # Log successful action
                self.system_logger.log_action(
                    action_type='CREATE',
                    entity_type='project',
                    entity_id=str(project_id),
                    entity_name=project.project_name,
                    user_id=user_id,
                    success=True,
                    duration_ms=duration_ms,
                    new_values={
                        'project_name': project.project_name,
                        'project_key': project.project_key,
                        'project_type': project.project_type,
                        'owner_team': project.owner_team,
                        'status': project.status
                    },
                    details={
                        'project_id': project_id,
                        'description': project.description,
                        'colors': {
                            'primary': project.color_primary,
                            'secondary': project.color_secondary
                        }
                    }
                )
                
                # Log audit event for compliance
                self.system_logger.log_audit(
                    event_type='PROJECT_CREATED',
                    event_category='DATA',
                    severity='INFO',
                    resource_type='project',
                    resource_id=str(project_id),
                    resource_name=project.project_name,
                    action_performed='CREATE_PROJECT',
                    action_result='SUCCESS',
                    user_id=user_id,
                    reason='New project creation',
                    compliance_flags='DATA_CREATION',
                    data_classification='INTERNAL'
                )
                
                self.logger.info(f"Created project: {project.project_name} (ID: {project_id})")
                return True, success_msg, project_id
                
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            error_msg = f"Error creating project: {str(e)}"
            
            # Log failed action
            self.system_logger.log_action(
                action_type='CREATE',
                entity_type='project',
                entity_name=project_name,
                user_id=user_id,
                success=False,
                error_message=str(e),
                duration_ms=duration_ms,
                details={'project_key': project_key, 'attempted_data': data}
            )
            
            # Log error details
            self.system_logger.log_error(
                error=e,
                user_id=user_id,
                context_data={
                    'operation': 'create_project',
                    'project_name': project_name,
                    'project_key': project_key,
                    'data': data
                },
                module_name=__name__,
                function_name='create_project'
            )
            
            self.logger.error(f"Error creating project: {e}")
            return False, error_msg, None
    
    # ==================== READ ====================
    
    def get_all_projects(self, user_id: str = 'system') -> Tuple[bool, str, Optional[List[Dict]]]:
        """
        Get all projects
        
        Args:
            user_id: User making the request
        
        Returns:
            Tuple of (success, message, projects_list)
        """
        start_time = time.time()
        
        if not self.db:
            return False, "Database not available", None
        
        try:
            with self.db.get_session() as session:
                projects = session.query(Project).filter_by(is_active=True).all()
                
                projects_list = []
                for project in projects:
                    projects_list.append({
                        'project_id': project.project_id,
                        'project_name': project.project_name,
                        'project_key': project.project_key,
                        'description': project.description,
                        'project_type': project.project_type,
                        'owner_team': project.owner_team,
                        'status': project.status,
                        'color_primary': project.color_primary,
                        'color_secondary': project.color_secondary,
                        'created_date': str(project.created_date),
                        'created_by': project.created_by
                    })
                
                duration_ms = int((time.time() - start_time) * 1000)
                
                # Log successful read action
                self.system_logger.log_action(
                    action_type='READ',
                    entity_type='project',
                    user_id=user_id,
                    success=True,
                    duration_ms=duration_ms,
                    details={
                        'query_type': 'get_all_projects',
                        'result_count': len(projects_list),
                        'filter': 'is_active=True'
                    }
                )
                
                return True, f"Found {len(projects_list)} projects", projects_list
                
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Log failed action
            self.system_logger.log_action(
                action_type='READ',
                entity_type='project',
                user_id=user_id,
                success=False,
                error_message=str(e),
                duration_ms=duration_ms,
                details={'query_type': 'get_all_projects'}
            )
            
            # Log error details
            self.system_logger.log_error(
                error=e,
                module_name=__name__,
                function_name='get_all_projects',
                user_id=user_id,
                context={'operation': 'get_all_projects'}
            )
            
            self.logger.error(f"Error getting projects: {e}")
            return False, f"Error getting projects: {str(e)}", None
    
    def get_project_by_id(self, project_id: int, user_id: str = 'system') -> Tuple[bool, str, Optional[Dict]]:
        """
        Get a specific project by ID
        
        Args:
            project_id: The project ID
            user_id: User making the request
        
        Returns:
            Tuple of (success, message, project_data)
        """
        start_time = time.time()
        
        if not self.db:
            return False, "Database not available", None
        
        try:
            with self.db.get_session() as session:
                project = session.query(Project).filter_by(
                    project_id=project_id,
                    is_active=True
                ).first()
                
                if not project:
                    duration_ms = int((time.time() - start_time) * 1000)
                    
                    # Log failed read attempt
                    self.system_logger.log_action(
                        action_type='READ',
                        entity_type='project',
                        entity_id=str(project_id),
                        user_id=user_id,
                        success=False,
                        error_message=f"Project with ID {project_id} not found",
                        duration_ms=duration_ms,
                        details={'query_type': 'get_project_by_id', 'project_id': project_id}
                    )
                    
                    return False, f"Project with ID {project_id} not found", None
                
                # Get environments
                environments = session.query(ProjectEnvironment).filter_by(
                    project_id=project_id
                ).all()
                
                project_data = {
                    'project_id': project.project_id,
                    'project_name': project.project_name,
                    'project_key': project.project_key,
                    'description': project.description,
                    'project_type': project.project_type,
                    'owner_team': project.owner_team,
                    'status': project.status,
                    'color_primary': project.color_primary,
                    'color_secondary': project.color_secondary,
                    'created_date': str(project.created_date),
                    'created_by': project.created_by,
                    'environments': [
                        {
                            'env_id': env.env_id,
                            'environment_name': env.environment_name,
                            'environment_description': env.environment_description,
                            'is_active': env.is_active
                        } for env in environments
                    ]
                }
                
                duration_ms = int((time.time() - start_time) * 1000)
                
                # Log successful read action
                self.system_logger.log_action(
                    action_type='READ',
                    entity_type='project',
                    entity_id=str(project_id),
                    entity_name=project.project_name,
                    user_id=user_id,
                    success=True,
                    duration_ms=duration_ms,
                    details={
                        'query_type': 'get_project_by_id',
                        'project_id': project_id,
                        'project_key': project.project_key,
                        'environments_count': len(environments)
                    }
                )
                
                return True, "Project found", project_data
                
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Log failed action
            self.system_logger.log_action(
                action_type='READ',
                entity_type='project',
                entity_id=str(project_id),
                user_id=user_id,
                success=False,
                error_message=str(e),
                duration_ms=duration_ms,
                details={'query_type': 'get_project_by_id', 'project_id': project_id}
            )
            
            # Log error details
            self.system_logger.log_error(
                error=e,
                module_name=__name__,
                function_name='get_project_by_id',
                user_id=user_id,
                context={'operation': 'get_project_by_id', 'project_id': project_id}
            )
            
            self.logger.error(f"Error getting project: {e}")
            return False, f"Error getting project: {str(e)}", None
    
    def get_project_by_key(self, project_key: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        Get a specific project by key
        
        Args:
            project_key: The project key
        
        Returns:
            Tuple of (success, message, project_data)
        """
        if not self.db:
            return False, "Database not available", None
        
        try:
            with self.db.get_session() as session:
                project = session.query(Project).filter_by(
                    project_key=project_key,
                    is_active=True
                ).first()
                
                if not project:
                    return False, f"Project with key '{project_key}' not found", None
                
                return self.get_project_by_id(project.project_id)
                
        except Exception as e:
            self.logger.error(f"Error getting project by key: {e}")
            return False, f"Error getting project: {str(e)}", None
    
    # ==================== UPDATE ====================
    
    def update_project(self, project_id: int, data: Dict, user_id: str = 'system') -> Tuple[bool, str]:
        """
        Update an existing project
        
        Args:
            project_id: The project ID to update
            data: Dictionary containing fields to update
            user_id: User making the update
        
        Returns:
            Tuple of (success, message)
        """
        start_time = time.time()
        
        if not self.db:
            return False, "Database not available"
        
        try:
            with self.db.get_session() as session:
                project = session.query(Project).filter_by(
                    project_id=project_id,
                    is_active=True
                ).first()
                
                if not project:
                    duration_ms = int((time.time() - start_time) * 1000)
                    
                    # Log failed update attempt
                    self.system_logger.log_action(
                        action_type='UPDATE',
                        entity_type='project',
                        entity_id=str(project_id),
                        user_id=user_id,
                        success=False,
                        error_message=f"Project with ID {project_id} not found",
                        duration_ms=duration_ms,
                        details={'update_data': data}
                    )
                    
                    return False, f"Project with ID {project_id} not found"
                
                # Capture old values for audit trail
                old_values = {
                    'project_name': project.project_name,
                    'description': project.description,
                    'project_type': project.project_type,
                    'owner_team': project.owner_team,
                    'status': project.status,
                    'color_primary': project.color_primary,
                    'color_secondary': project.color_secondary
                }
                
                # Update fields if provided
                updated_fields = []
                if 'project_name' in data:
                    project.project_name = data['project_name']
                    updated_fields.append('project_name')
                if 'description' in data:
                    project.description = data['description']
                    updated_fields.append('description')
                if 'project_type' in data:
                    project.project_type = data['project_type']
                    updated_fields.append('project_type')
                if 'owner_team' in data:
                    project.owner_team = data['owner_team']
                    updated_fields.append('owner_team')
                if 'status' in data:
                    project.status = data['status']
                    updated_fields.append('status')
                if 'color_primary' in data:
                    project.color_primary = data['color_primary']
                    updated_fields.append('color_primary')
                if 'color_secondary' in data:
                    project.color_secondary = data['color_secondary']
                    updated_fields.append('color_secondary')
                if 'updated_by' in data:
                    project.updated_by = data['updated_by']
                    updated_fields.append('updated_by')
                
                session.commit()
                
                duration_ms = int((time.time() - start_time) * 1000)
                
                # Capture new values for audit trail
                new_values = {
                    'project_name': project.project_name,
                    'description': project.description,
                    'project_type': project.project_type,
                    'owner_team': project.owner_team,
                    'status': project.status,
                    'color_primary': project.color_primary,
                    'color_secondary': project.color_secondary
                }
                
                # Log successful update action
                self.system_logger.log_action(
                    action_type='UPDATE',
                    entity_type='project',
                    entity_id=str(project_id),
                    entity_name=project.project_name,
                    user_id=user_id,
                    success=True,
                    duration_ms=duration_ms,
                    old_values=old_values,
                    new_values=new_values,
                    details={
                        'updated_fields': updated_fields,
                        'project_key': project.project_key
                    }
                )
                
                # Log audit event for compliance
                self.system_logger.log_audit(
                    event_type='PROJECT_UPDATED',
                    event_category='DATA',
                    severity='INFO',
                    resource_type='project',
                    resource_id=str(project_id),
                    resource_name=project.project_name,
                    action_performed='UPDATE_PROJECT',
                    action_result='SUCCESS',
                    user_id=user_id,
                    reason='Project data modification',
                    compliance_flags='DATA_MODIFICATION',
                    data_classification='INTERNAL',
                    additional_metadata={
                        'updated_fields': updated_fields,
                        'changes_count': len(updated_fields)
                    }
                )
                
                self.logger.info(f"Updated project: {project.project_name} (ID: {project_id})")
                return True, f"Project '{project.project_name}' updated successfully"
                
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Log failed action
            self.system_logger.log_action(
                action_type='UPDATE',
                entity_type='project',
                entity_id=str(project_id),
                user_id=user_id,
                success=False,
                error_message=str(e),
                duration_ms=duration_ms,
                details={'update_data': data}
            )
            
            # Log error details
            self.system_logger.log_error(
                error=e,
                module_name=__name__,
                function_name='update_project',
                user_id=user_id,
                context={'operation': 'update_project', 'project_id': project_id, 'data': data}
            )
            
            self.logger.error(f"Error updating project: {e}")
            return False, f"Error updating project: {str(e)}"
    
    # ==================== DELETE ====================
    
    def delete_project(self, project_id: int, hard_delete: bool = False, user_id: str = 'system') -> Tuple[bool, str]:
        """Delete a project - simplified version"""
        if not self.db:
            self.simple_logger.log_action("DELETE", "project", str(project_id), user_id, False, "Database not available")
            return False, "Database not available"
        
        try:
            with self.db.get_session() as session:
                project = session.query(Project).filter_by(project_id=project_id).first()
                
                if not project:
                    self.simple_logger.log_action("DELETE", "project", str(project_id), user_id, False, "Project not found")
                    return False, f"Project with ID {project_id} not found"
                
                project_name = project.project_name
                
                if hard_delete:
                    # Delete environments first
                    session.query(ProjectEnvironment).filter_by(project_id=project_id).delete()
                    # Delete the project
                    session.delete(project)
                    message = f"Project '{project_name}' permanently deleted"
                else:
                    # Soft delete
                    project.is_active = False
                    project.status = 'archived'
                    message = f"Project '{project_name}' archived"
                
                session.commit()
                
                self.simple_logger.log_action("DELETE", "project", str(project_id), user_id, True)
                self.logger.info(f"Deleted project: {project_name} (ID: {project_id})")
                return True, message
                
        except Exception as e:
            self.simple_logger.log_action("DELETE", "project", str(project_id), user_id, False, str(e))
            self.logger.error(f"Error deleting project: {e}")
            return False, f"Error deleting project: {str(e)}"
    
    # ==================== ENVIRONMENT MANAGEMENT ====================
    
    def add_environment(self, project_id: int, env_name: str, description: str = '') -> Tuple[bool, str]:
        """
        Add an environment to a project
        
        Args:
            project_id: The project ID
            env_name: Environment name (will be uppercased)
            description: Environment description
        
        Returns:
            Tuple of (success, message)
        """
        if not self.db:
            return False, "Database not available"
        
        try:
            with self.db.get_session() as session:
                # Check project exists
                project = session.query(Project).filter_by(
                    project_id=project_id,
                    is_active=True
                ).first()
                
                if not project:
                    return False, f"Project with ID {project_id} not found"
                
                env_name = env_name.upper()
                
                # Check if environment already exists
                existing = session.query(ProjectEnvironment).filter_by(
                    project_id=project_id,
                    environment_name=env_name
                ).first()
                
                if existing:
                    return False, f"Environment '{env_name}' already exists for this project"
                
                # Add new environment
                env = ProjectEnvironment(
                    project_id=project_id,
                    environment_name=env_name,
                    environment_description=description,
                    is_active=True
                )
                
                session.add(env)
                session.commit()
                
                self.logger.info(f"Added environment {env_name} to project ID {project_id}")
                return True, f"Environment '{env_name}' added successfully"
                
        except Exception as e:
            self.logger.error(f"Error adding environment: {e}")
            return False, f"Error adding environment: {str(e)}"
    
    def remove_environment(self, project_id: int, env_name: str) -> Tuple[bool, str]:
        """
        Remove an environment from a project
        
        Args:
            project_id: The project ID
            env_name: Environment name to remove
        
        Returns:
            Tuple of (success, message)
        """
        if not self.db:
            return False, "Database not available"
        
        try:
            with self.db.get_session() as session:
                env_name = env_name.upper()
                
                # Find and delete environment
                env = session.query(ProjectEnvironment).filter_by(
                    project_id=project_id,
                    environment_name=env_name
                ).first()
                
                if not env:
                    return False, f"Environment '{env_name}' not found for this project"
                
                session.delete(env)
                session.commit()
                
                self.logger.info(f"Removed environment {env_name} from project ID {project_id}")
                return True, f"Environment '{env_name}' removed successfully"
                
        except Exception as e:
            self.logger.error(f"Error removing environment: {e}")
            return False, f"Error removing environment: {str(e)}"
    
    def get_project_environments(self, project_id: int) -> Tuple[bool, str, Optional[List[Dict]]]:
        """
        Get all environments for a project

        DISABLED: Environment concept removed from MSI Factory

        Args:
            project_id: The project ID

        Returns:
            Tuple of (success, message, environments_list)
        """
        # Environment concept has been removed - return empty list
        self.logger.info(f"Environment query disabled for project {project_id}")
        return True, "Environment functionality disabled", []