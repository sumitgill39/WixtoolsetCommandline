"""
ProjectManager API Module
Complete project management system using API pattern - handles all project operations
"""

import pyodbc
import logging
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
import uuid

class ProjectManager:
    """Complete project management system - handles all project operations via API"""

    def __init__(self):
        self.conn_str = (
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=SUMEETGILL7E47\\MSSQLSERVER01;"
            "DATABASE=MSIFactory;"
            "Trusted_Connection=yes;"
            "Connection Timeout=10;"
        )
        self.logger = logging.getLogger(__name__)

    # =================== PROJECT CRUD OPERATIONS ===================

    def create_project(self, project_data: Dict, username: str = 'system') -> Tuple[bool, str, Optional[int]]:
        """
        Create a new project with validation

        Args:
            project_data: Dictionary containing project details
            username: User creating the project

        Returns:
            Tuple of (success, message, project_id)
        """
        try:
            # Validate required fields
            if not project_data.get('project_name'):
                return False, "Project name is required", None

            if not project_data.get('project_key'):
                return False, "Project key is required", None

            project_key = project_data['project_key'].upper().strip()

            with pyodbc.connect(self.conn_str) as conn:
                with conn.cursor() as cursor:
                    # Check for duplicate project key
                    cursor.execute(
                        "SELECT COUNT(*) FROM projects WHERE project_key = ?",
                        (project_key,)
                    )
                    if cursor.fetchone()[0] > 0:
                        return False, f"Project key '{project_key}' already exists", None

                    # Generate project GUID if not provided
                    project_guid = project_data.get('project_guid') or str(uuid.uuid4())

                    # Insert project
                    cursor.execute("""
                        INSERT INTO projects (
                            project_name, project_key, project_guid, description,
                            project_type, owner_team, status,
                            color_primary, color_secondary,
                            created_by, created_date, is_active
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE(), 1)
                    """, (
                        project_data.get('project_name'),
                        project_key,
                        project_guid,
                        project_data.get('description', ''),
                        project_data.get('project_type', 'WebApp'),
                        project_data.get('owner_team', ''),
                        project_data.get('status', 'active'),
                        project_data.get('color_primary', '#2c3e50'),
                        project_data.get('color_secondary', '#3498db'),
                        username
                    ))

                    # Get the new project ID
                    cursor.execute("SELECT @@IDENTITY")
                    project_id = cursor.fetchone()[0]

                    # Add environments if provided
                    environments = project_data.get('environments', [])
                    for env_name in environments:
                        cursor.execute("""
                            INSERT INTO project_environments (
                                project_id, environment_name, environment_description, is_active
                            ) VALUES (?, ?, ?, 1)
                        """, (project_id, env_name.upper(), f"{env_name} Environment"))

                    conn.commit()
                    self.logger.info(f"Created project: {project_data['project_name']} (ID: {project_id})")
                    return True, f"Project created successfully", project_id

        except Exception as e:
            self.logger.error(f"Error creating project: {e}")
            return False, f"Error creating project: {str(e)}", None

    def get_project_by_id(self, project_id: int) -> Optional[Dict]:
        """Get project details by ID"""
        try:
            with pyodbc.connect(self.conn_str) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT project_id, project_name, project_key, project_guid,
                               description, project_type, owner_team, status,
                               color_primary, color_secondary,
                               created_date, created_by, updated_date, updated_by,
                               is_active
                        FROM projects
                        WHERE project_id = ? AND is_active = 1
                    """, (project_id,))

                    row = cursor.fetchone()
                    if not row:
                        return None

                    project = {
                        'project_id': row[0],
                        'project_name': row[1],
                        'project_key': row[2],
                        'project_guid': row[3],
                        'description': row[4],
                        'project_type': row[5],
                        'owner_team': row[6],
                        'status': row[7],
                        'color_primary': row[8],
                        'color_secondary': row[9],
                        'created_date': row[10],
                        'created_by': row[11],
                        'updated_date': row[12],
                        'updated_by': row[13],
                        'is_active': row[14]
                    }

                    # Get environments
                    cursor.execute("""
                        SELECT env_id, environment_name, environment_description
                        FROM project_environments
                        WHERE project_id = ? AND is_active = 1
                    """, (project_id,))

                    project['environments'] = []
                    for env_row in cursor.fetchall():
                        project['environments'].append({
                            'env_id': env_row[0],
                            'environment_name': env_row[1],
                            'environment_description': env_row[2]
                        })

                    return project

        except Exception as e:
            self.logger.error(f"Error getting project {project_id}: {e}")
            return None

    def get_all_projects(self, include_inactive: bool = False) -> List[Dict]:
        """Get all projects"""
        try:
            with pyodbc.connect(self.conn_str) as conn:
                with conn.cursor() as cursor:
                    query = """
                        SELECT project_id, project_name, project_key, project_guid,
                               description, project_type, owner_team, status,
                               color_primary, color_secondary,
                               created_date, created_by, is_active
                        FROM projects
                    """
                    if not include_inactive:
                        query += " WHERE is_active = 1"
                    query += " ORDER BY project_name"

                    cursor.execute(query)

                    projects = []
                    for row in cursor.fetchall():
                        projects.append({
                            'project_id': row[0],
                            'project_name': row[1],
                            'project_key': row[2],
                            'project_guid': row[3],
                            'description': row[4],
                            'project_type': row[5],
                            'owner_team': row[6],
                            'status': row[7],
                            'color_primary': row[8],
                            'color_secondary': row[9],
                            'created_date': row[10],
                            'created_by': row[11],
                            'is_active': row[12]
                        })

                    return projects

        except Exception as e:
            self.logger.error(f"Error getting all projects: {e}")
            return []

    def update_project(self, project_id: int, project_data: Dict, username: str = 'system') -> Tuple[bool, str]:
        """Update an existing project"""
        try:
            with pyodbc.connect(self.conn_str) as conn:
                with conn.cursor() as cursor:
                    # Check if project exists
                    cursor.execute(
                        "SELECT COUNT(*) FROM projects WHERE project_id = ? AND is_active = 1",
                        (project_id,)
                    )
                    if cursor.fetchone()[0] == 0:
                        return False, "Project not found"

                    # Build update query dynamically based on provided fields
                    update_fields = []
                    params = []

                    if 'project_name' in project_data:
                        update_fields.append("project_name = ?")
                        params.append(project_data['project_name'])

                    if 'description' in project_data:
                        update_fields.append("description = ?")
                        params.append(project_data['description'])

                    if 'project_type' in project_data:
                        update_fields.append("project_type = ?")
                        params.append(project_data['project_type'])

                    if 'owner_team' in project_data:
                        update_fields.append("owner_team = ?")
                        params.append(project_data['owner_team'])

                    if 'status' in project_data:
                        update_fields.append("status = ?")
                        params.append(project_data['status'])

                    if 'color_primary' in project_data:
                        update_fields.append("color_primary = ?")
                        params.append(project_data['color_primary'])

                    if 'color_secondary' in project_data:
                        update_fields.append("color_secondary = ?")
                        params.append(project_data['color_secondary'])

                    # Always update metadata
                    update_fields.append("updated_by = ?")
                    params.append(username)
                    update_fields.append("updated_date = GETDATE()")

                    # Add project_id at the end for WHERE clause
                    params.append(project_id)

                    query = f"""
                        UPDATE projects
                        SET {', '.join(update_fields)}
                        WHERE project_id = ?
                    """

                    cursor.execute(query, params)

                    # Handle status cascading to components if status changed
                    if 'status' in project_data:
                        self._cascade_component_status(cursor, project_id, project_data['status'], username)

                    conn.commit()
                    self.logger.info(f"Updated project ID: {project_id}")
                    return True, "Project updated successfully"

        except Exception as e:
            self.logger.error(f"Error updating project {project_id}: {e}")
            return False, f"Error updating project: {str(e)}"

    def delete_project(self, project_id: int, hard_delete: bool = False, username: str = 'system') -> Tuple[bool, str]:
        """Delete a project (soft or hard delete)"""
        try:
            with pyodbc.connect(self.conn_str) as conn:
                with conn.cursor() as cursor:
                    # Check if project exists
                    cursor.execute(
                        "SELECT project_name FROM projects WHERE project_id = ?",
                        (project_id,)
                    )
                    result = cursor.fetchone()
                    if not result:
                        return False, "Project not found"

                    project_name = result[0]

                    if hard_delete:
                        # Delete all related data
                        cursor.execute("DELETE FROM components WHERE project_id = ?", (project_id,))
                        cursor.execute("DELETE FROM project_environments WHERE project_id = ?", (project_id,))
                        cursor.execute("DELETE FROM user_projects WHERE project_id = ?", (project_id,))
                        cursor.execute("DELETE FROM projects WHERE project_id = ?", (project_id,))
                        message = f"Project '{project_name}' permanently deleted"
                    else:
                        # Soft delete
                        cursor.execute("""
                            UPDATE projects
                            SET is_active = 0, status = 'archived',
                                updated_by = ?, updated_date = GETDATE()
                            WHERE project_id = ?
                        """, (username, project_id))
                        message = f"Project '{project_name}' archived"

                    conn.commit()
                    self.logger.info(f"Deleted project: {project_name} (ID: {project_id}, hard={hard_delete})")
                    return True, message

        except Exception as e:
            self.logger.error(f"Error deleting project {project_id}: {e}")
            return False, f"Error deleting project: {str(e)}"

    # =================== PROJECT COMPONENTS OPERATIONS ===================

    def get_project_components(self, project_id: int, include_disabled: bool = False) -> List[Dict]:
        """Get all components for a project"""
        try:
            with pyodbc.connect(self.conn_str) as conn:
                with conn.cursor() as cursor:
                    query = """
                        SELECT component_id, component_name, component_type,
                               framework, description, is_enabled,
                               app_name, app_version, manufacturer,
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
                            'description': row[4],
                            'is_enabled': row[5],
                            'app_name': row[6],
                            'app_version': row[7],
                            'manufacturer': row[8],
                            'created_date': row[9],
                            'created_by': row[10]
                        })

                    return components

        except Exception as e:
            self.logger.error(f"Error getting project components: {e}")
            return []

    # =================== HELPER METHODS ===================

    def _cascade_component_status(self, cursor, project_id: int, project_status: str, username: str):
        """Cascade project status changes to components"""
        try:
            if project_status in ['inactive', 'archived']:
                # Disable all components
                cursor.execute("""
                    UPDATE components
                    SET is_enabled = 0, updated_by = ?, updated_date = GETDATE()
                    WHERE project_id = ?
                """, (username, project_id))
            elif project_status == 'active':
                # Re-enable components (optionally)
                cursor.execute("""
                    UPDATE components
                    SET is_enabled = 1, updated_by = ?, updated_date = GETDATE()
                    WHERE project_id = ?
                """, (username, project_id))

        except Exception as e:
            self.logger.error(f"Error cascading component status: {e}")

    def validate_project_data(self, project_data: Dict) -> Tuple[bool, List[str]]:
        """Validate project data"""
        errors = []

        # Required fields
        if not project_data.get('project_name'):
            errors.append("Project name is required")

        if not project_data.get('project_key'):
            errors.append("Project key is required")
        elif len(project_data['project_key']) < 3:
            errors.append("Project key must be at least 3 characters")

        if not project_data.get('project_type'):
            errors.append("Project type is required")
        elif project_data['project_type'] not in ['WebApp', 'Service', 'Website', 'Desktop', 'API']:
            errors.append("Invalid project type")

        # Color format validation
        if project_data.get('color_primary'):
            if not project_data['color_primary'].startswith('#') or len(project_data['color_primary']) != 7:
                errors.append("Primary color must be in hex format (#RRGGBB)")

        if project_data.get('color_secondary'):
            if not project_data['color_secondary'].startswith('#') or len(project_data['color_secondary']) != 7:
                errors.append("Secondary color must be in hex format (#RRGGBB)")

        return len(errors) == 0, errors


# =================== CONVENIENCE FUNCTIONS ===================
# These are standalone functions that can be imported directly

def create_project(project_data: Dict, username: str = 'system') -> Tuple[bool, str, Optional[int]]:
    """Quick function to create a project"""
    manager = ProjectManager()
    return manager.create_project(project_data, username)

def get_project(project_id: int) -> Optional[Dict]:
    """Quick function to get a project"""
    manager = ProjectManager()
    return manager.get_project_by_id(project_id)

def get_all_projects(include_inactive: bool = False) -> List[Dict]:
    """Quick function to get all projects"""
    manager = ProjectManager()
    return manager.get_all_projects(include_inactive)

def update_project(project_id: int, project_data: Dict, username: str = 'system') -> Tuple[bool, str]:
    """Quick function to update a project"""
    manager = ProjectManager()
    return manager.update_project(project_id, project_data, username)

def delete_project(project_id: int, hard_delete: bool = False, username: str = 'system') -> Tuple[bool, str]:
    """Quick function to delete a project"""
    manager = ProjectManager()
    return manager.delete_project(project_id, hard_delete, username)

def validate_project(project_data: Dict) -> Tuple[bool, List[str]]:
    """Quick function to validate project data"""
    manager = ProjectManager()
    return manager.validate_project_data(project_data)