# Package Builder - Branch Management API
# Version: 1.0
# Description: RESTful API endpoints for managing component branches in MSI Factory
# Author: MSI Factory Team

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

# Database imports
import pyodbc
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

# Import integration manager for JFrog URL fetching
try:
    from PackageBuilder.integration_manager import integration_manager
except ImportError:
    integration_manager = None
    logger.warning("Integration manager not available - using placeholder URLs")

class BranchAPI:
    """
    Branch Management API class for handling component branch operations.
    Provides CRUD operations for component branches with proper error handling
    and database transaction management.
    """

    def __init__(self):
        """Initialize the BranchAPI with database configuration."""
        self.db_config = {
            'server': os.getenv('DB_SERVER', 'SUMEETGILL7E47\\MSSQLSERVER01'),
            'database': os.getenv('DB_NAME', 'MSIFactory'),
            'username': os.getenv('DB_USERNAME', ''),
            'password': os.getenv('DB_PASSWORD', ''),
            'driver': 'ODBC Driver 17 for SQL Server',
            'trusted_connection': os.getenv('DB_TRUST_CONNECTION', 'yes')
        }

    def _get_db_connection(self) -> pyodbc.Connection:
        """
        Establish and return a database connection.

        Returns:
            pyodbc.Connection: Database connection object

        Raises:
            Exception: If database connection fails
        """
        try:
            if self.db_config['username'] and self.db_config['password']:
                # SQL Server Authentication
                conn_string = (
                    f"DRIVER={{{self.db_config['driver']}}};"
                    f"SERVER={self.db_config['server']};"
                    f"DATABASE={self.db_config['database']};"
                    f"UID={self.db_config['username']};"
                    f"PWD={self.db_config['password']};"
                    f"TrustServerCertificate=yes;"
                )
            else:
                # Windows Authentication
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

    def get_all_branches(self) -> Dict[str, Any]:
        """
        Retrieve all component branches with their associated component and project information.

        Returns:
            Dict[str, Any]: Response containing success status and branch data
        """
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()

                # Query to get all branches with component and project details
                query = """
                SELECT
                    cb.branch_id,
                    cb.component_id,
                    cb.branch_name,
                    cb.path_pattern_override,
                    cb.major_version,
                    cb.minor_version,
                    cb.patch_version,
                    cb.build_number,
                    cb.auto_increment,
                    cb.branch_status,
                    cb.description,
                    cb.created_date,
                    cb.updated_date,
                    c.component_name,
                    p.project_name,
                    p.project_key
                FROM component_branches cb
                INNER JOIN components c ON cb.component_id = c.component_id
                INNER JOIN projects p ON c.project_id = p.project_id
                WHERE cb.is_active = 1 AND c.is_enabled = 1 AND p.is_active = 1
                ORDER BY p.project_name, c.component_name, cb.branch_name
                """

                cursor.execute(query)
                rows = cursor.fetchall()

                # Get JFrog base URL from integration configuration
                jfrog_base_url = '{baseURL}'  # Default placeholder
                if integration_manager:
                    try:
                        jfrog_base_url = integration_manager.get_jfrog_base_url()
                    except Exception as e:
                        logger.warning(f"Could not fetch JFrog base URL: {e}")

                branches = []
                for row in rows:
                    branch_data = {
                        'branch_id': row.branch_id,
                        'component_id': row.component_id,
                        'branch_name': row.branch_name,
                        'path_pattern_override': row.path_pattern_override,
                        'major_version': row.major_version,
                        'minor_version': row.minor_version,
                        'patch_version': row.patch_version,
                        'build_number': row.build_number,
                        'auto_increment': row.auto_increment,
                        'branch_status': row.branch_status,
                        'description': row.description,
                        'component_name': row.component_name,
                        'project_name': row.project_name,
                        'project_key': row.project_key,
                        'jfrog_base_url': jfrog_base_url,  # Include JFrog base URL
                        'created_date': row.created_date.strftime('%Y-%m-%d %H:%M:%S') if row.created_date else None,
                        'updated_date': row.updated_date.strftime('%Y-%m-%d %H:%M:%S') if row.updated_date else None
                    }
                    branches.append(branch_data)

                return {
                    'success': True,
                    'branches': branches,
                    'count': len(branches)
                }

        except Exception as e:
            logger.error(f"Error retrieving all branches: {str(e)}")
            return {
                'success': False,
                'error': f"Failed to retrieve branches: {str(e)}",
                'branches': []
            }

    def get_branch_by_id(self, branch_id: int) -> Dict[str, Any]:
        """
        Retrieve a specific branch by its ID.

        Args:
            branch_id (int): The ID of the branch to retrieve

        Returns:
            Dict[str, Any]: Response containing success status and branch data
        """
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()

                query = """
                SELECT
                    cb.branch_id,
                    cb.component_id,
                    cb.branch_name,
                    cb.path_pattern_override,
                    cb.major_version,
                    cb.minor_version,
                    cb.patch_version,
                    cb.build_number,
                    cb.auto_increment,
                    cb.branch_status,
                    cb.description,
                    cb.created_date,
                    cb.updated_date,
                    c.component_name,
                    p.project_name,
                    p.project_key
                FROM component_branches cb
                INNER JOIN components c ON cb.component_id = c.component_id
                INNER JOIN projects p ON c.project_id = p.project_id
                WHERE cb.branch_id = ? AND cb.is_active = 1
                """

                cursor.execute(query, (branch_id,))
                row = cursor.fetchone()

                if row:
                    branch_data = {
                        'branch_id': row.branch_id,
                        'component_id': row.component_id,
                        'branch_name': row.branch_name,
                        'path_pattern_override': row.path_pattern_override,
                        'major_version': row.major_version,
                        'minor_version': row.minor_version,
                        'patch_version': row.patch_version,
                        'build_number': row.build_number,
                        'auto_increment': row.auto_increment,
                        'branch_status': row.branch_status,
                        'description': row.description,
                        'component_name': row.component_name,
                        'project_name': row.project_name,
                        'project_key': row.project_key,
                        'created_date': row.created_date.strftime('%Y-%m-%d %H:%M:%S') if row.created_date else None,
                        'updated_date': row.updated_date.strftime('%Y-%m-%d %H:%M:%S') if row.updated_date else None
                    }

                    return {
                        'success': True,
                        'branch': branch_data
                    }
                else:
                    return {
                        'success': False,
                        'error': 'Branch not found'
                    }

        except Exception as e:
            logger.error(f"Error retrieving branch {branch_id}: {str(e)}")
            return {
                'success': False,
                'error': f"Failed to retrieve branch: {str(e)}"
            }

    def create_branch(self, branch_data: Dict[str, Any], created_by: str = 'system') -> Dict[str, Any]:
        """
        Create a new branch for a component.

        Args:
            branch_data (Dict[str, Any]): Branch information to create
            created_by (str): Username of the user creating the branch

        Returns:
            Dict[str, Any]: Response containing success status and new branch ID
        """
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()

                # Validate required fields
                required_fields = ['component_id', 'branch_name']
                for field in required_fields:
                    if field not in branch_data or not branch_data[field]:
                        return {
                            'success': False,
                            'error': f"Missing required field: {field}"
                        }

                # Check if branch already exists for this component
                check_query = """
                SELECT COUNT(*) FROM component_branches
                WHERE component_id = ? AND branch_name = ? AND is_active = 1
                """
                cursor.execute(check_query, (branch_data['component_id'], branch_data['branch_name']))
                existing_count = cursor.fetchone()[0]

                if existing_count > 0:
                    return {
                        'success': False,
                        'error': f"Branch '{branch_data['branch_name']}' already exists for this component"
                    }

                # Set default values
                path_pattern = branch_data.get('path_pattern_override',
                    '{ComponentName}/{branch}/Build{date}.{buildNumber}/{componentName}.zip')
                major_version = branch_data.get('major_version', 1)
                minor_version = branch_data.get('minor_version', 0)
                patch_version = branch_data.get('patch_version', 0)
                build_number = branch_data.get('build_number', 0)
                auto_increment = branch_data.get('auto_increment', 'build')
                branch_status = branch_data.get('branch_status', 'active')
                description = branch_data.get('description', '')

                # Insert new branch
                insert_query = """
                INSERT INTO component_branches
                (component_id, branch_name, path_pattern_override, major_version, minor_version,
                 patch_version, build_number, auto_increment, branch_status, description,
                 created_by, updated_by, created_date, updated_date, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE(), GETDATE(), 1)
                """

                cursor.execute(insert_query, (
                    branch_data['component_id'],
                    branch_data['branch_name'],
                    path_pattern,
                    major_version,
                    minor_version,
                    patch_version,
                    build_number,
                    auto_increment,
                    branch_status,
                    description,
                    created_by,
                    created_by
                ))

                # Get the new branch ID
                cursor.execute("SELECT @@IDENTITY")
                new_branch_id = cursor.fetchone()[0]

                conn.commit()

                logger.info(f"Branch '{branch_data['branch_name']}' created successfully with ID {new_branch_id}")

                return {
                    'success': True,
                    'branch_id': new_branch_id,
                    'message': f"Branch '{branch_data['branch_name']}' created successfully"
                }

        except Exception as e:
            logger.error(f"Error creating branch: {str(e)}")
            return {
                'success': False,
                'error': f"Failed to create branch: {str(e)}"
            }

    def update_branch(self, branch_id: int, branch_data: Dict[str, Any], updated_by: str = 'system') -> Dict[str, Any]:
        """
        Update an existing branch.

        Args:
            branch_id (int): ID of the branch to update
            branch_data (Dict[str, Any]): Updated branch information
            updated_by (str): Username of the user updating the branch

        Returns:
            Dict[str, Any]: Response containing success status
        """
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()

                # Check if branch exists
                check_query = "SELECT COUNT(*) FROM component_branches WHERE branch_id = ? AND is_active = 1"
                cursor.execute(check_query, (branch_id,))
                if cursor.fetchone()[0] == 0:
                    return {
                        'success': False,
                        'error': 'Branch not found'
                    }

                # Build update query dynamically based on provided fields
                update_fields = []
                params = []

                updatable_fields = [
                    'branch_name', 'path_pattern_override', 'major_version', 'minor_version',
                    'patch_version', 'build_number', 'auto_increment', 'branch_status', 'description'
                ]

                for field in updatable_fields:
                    if field in branch_data:
                        update_fields.append(f"{field} = ?")
                        params.append(branch_data[field])

                if not update_fields:
                    return {
                        'success': False,
                        'error': 'No valid fields provided for update'
                    }

                # Add updated_by and updated_date
                update_fields.extend(['updated_by = ?', 'updated_date = GETDATE()'])
                params.extend([updated_by, branch_id])

                update_query = f"""
                UPDATE component_branches
                SET {', '.join(update_fields)}
                WHERE branch_id = ?
                """

                cursor.execute(update_query, params)
                conn.commit()

                logger.info(f"Branch {branch_id} updated successfully")

                return {
                    'success': True,
                    'message': 'Branch updated successfully'
                }

        except Exception as e:
            logger.error(f"Error updating branch {branch_id}: {str(e)}")
            return {
                'success': False,
                'error': f"Failed to update branch: {str(e)}"
            }

    def delete_branch(self, branch_id: int, deleted_by: str = 'system') -> Dict[str, Any]:
        """
        Soft delete a branch by setting is_active to 0.

        Args:
            branch_id (int): ID of the branch to delete
            deleted_by (str): Username of the user deleting the branch

        Returns:
            Dict[str, Any]: Response containing success status
        """
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()

                # Check if branch exists
                check_query = "SELECT branch_name FROM component_branches WHERE branch_id = ? AND is_active = 1"
                cursor.execute(check_query, (branch_id,))
                row = cursor.fetchone()

                if not row:
                    return {
                        'success': False,
                        'error': 'Branch not found'
                    }

                branch_name = row[0]

                # Soft delete the branch
                delete_query = """
                UPDATE component_branches
                SET is_active = 0, updated_by = ?, updated_date = GETDATE()
                WHERE branch_id = ?
                """

                cursor.execute(delete_query, (deleted_by, branch_id))
                conn.commit()

                logger.info(f"Branch '{branch_name}' (ID: {branch_id}) soft deleted successfully")

                return {
                    'success': True,
                    'message': f"Branch '{branch_name}' deleted successfully"
                }

        except Exception as e:
            logger.error(f"Error deleting branch {branch_id}: {str(e)}")
            return {
                'success': False,
                'error': f"Failed to delete branch: {str(e)}"
            }

    def get_components_for_dropdown(self) -> Dict[str, Any]:
        """
        Get all active components for dropdown selection in the UI.

        Returns:
            Dict[str, Any]: Response containing success status and components list
        """
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()

                query = """
                SELECT
                    c.component_id,
                    c.component_name,
                    p.project_name,
                    p.project_key
                FROM components c
                INNER JOIN projects p ON c.project_id = p.project_id
                WHERE c.is_enabled = 1 AND p.is_active = 1
                ORDER BY p.project_name, c.component_name
                """

                cursor.execute(query)
                rows = cursor.fetchall()

                components = []
                for row in rows:
                    component_data = {
                        'component_id': row.component_id,
                        'component_name': row.component_name,
                        'project_name': row.project_name,
                        'project_key': row.project_key
                    }
                    components.append(component_data)

                return {
                    'success': True,
                    'components': components
                }

        except Exception as e:
            logger.error(f"Error retrieving components: {str(e)}")
            return {
                'success': False,
                'error': f"Failed to retrieve components: {str(e)}",
                'components': []
            }

    def get_projects_for_dropdown(self) -> Dict[str, Any]:
        """
        Get all active projects for dropdown selection in the UI.

        Returns:
            Dict[str, Any]: Response containing success status and projects list
        """
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()

                query = """
                SELECT
                    project_id,
                    project_name,
                    project_key
                FROM projects
                WHERE is_active = 1
                ORDER BY project_name
                """

                cursor.execute(query)
                rows = cursor.fetchall()

                projects = []
                for row in rows:
                    project_data = {
                        'project_id': row.project_id,
                        'project_name': row.project_name,
                        'project_key': row.project_key
                    }
                    projects.append(project_data)

                return {
                    'success': True,
                    'projects': projects
                }

        except Exception as e:
            logger.error(f"Error retrieving projects: {str(e)}")
            return {
                'success': False,
                'error': f"Failed to retrieve projects: {str(e)}",
                'projects': []
            }

    def get_components_by_project(self, project_id: int) -> Dict[str, Any]:
        """
        Get all active components for a specific project.

        Args:
            project_id (int): The ID of the project to get components for

        Returns:
            Dict[str, Any]: Response containing success status and components list
        """
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()

                query = """
                SELECT
                    c.component_id,
                    c.component_name,
                    p.project_name,
                    p.project_key
                FROM components c
                INNER JOIN projects p ON c.project_id = p.project_id
                WHERE c.project_id = ? AND c.is_enabled = 1 AND p.is_active = 1
                ORDER BY c.component_name
                """

                cursor.execute(query, (project_id,))
                rows = cursor.fetchall()

                components = []
                for row in rows:
                    component_data = {
                        'component_id': row.component_id,
                        'component_name': row.component_name,
                        'project_name': row.project_name,
                        'project_key': row.project_key
                    }
                    components.append(component_data)

                return {
                    'success': True,
                    'components': components,
                    'count': len(components)
                }

        except Exception as e:
            logger.error(f"Error retrieving components for project {project_id}: {str(e)}")
            return {
                'success': False,
                'error': f"Failed to retrieve components: {str(e)}",
                'components': []
            }

# Initialize the API instance
branch_api = BranchAPI()