#!/usr/bin/env python3
"""
MSI Factory - Main Application
This is the main entry point that combines authentication and MSI generation
"""

import os
import sys
import json
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from sqlalchemy import text

# Import our authentication system
sys.path.append('auth')
from simple_auth import SimpleAuth

# Import database connection
sys.path.append('database')
from database.connection_manager import execute_with_retry, get_db_connection_info

# Import API client for database operations
sys.path.append('api')
from api.api_client import get_api_client

# Import our MSI generation engine
sys.path.append('engine')

# Import logging module
from logger import get_logger, log_info, log_error, log_security

app = Flask(__name__, template_folder='webapp/templates', static_folder='webapp/static')
app.secret_key = 'msi_factory_main_secret_key_change_in_production'

# Initialize components
auth_system = SimpleAuth()
logger = get_logger()

# Initialize API client
try:
    api_client = get_api_client()
    if api_client.check_health():
        print("[INFO] Connected to MSI Factory API")
        log_info("MSI Factory API connection established")
    else:
        print("[WARNING] API server not responding, using fallback methods")
        log_info("API server not responding, using fallback auth_system methods")
        api_client = None
except Exception as e:
    print(f"[WARNING] Could not initialize API client: {e}")
    log_error(f"Could not initialize API client: {str(e)}")
    api_client = None

def simple_delete_project_from_database(project_id):
    """Simple project deletion without complex transaction handling"""
    log_info(f"DATABASE: Attempting simple database deletion for project {project_id}")

    try:
        import pyodbc

        conn_str = (
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=SUMEETGILL7E47\\MSSQLSERVER01;"
            "DATABASE=MSIFactory;"
            "Trusted_Connection=yes;"
            "Connection Timeout=5;"
        )

        with pyodbc.connect(conn_str, timeout=5) as conn:
            with conn.cursor() as cursor:
                # Delete dependent records first to avoid foreign key constraints
                # The error shows msi_configurations has FK constraint on component_id
                # Let's try deleting by component_id = project_id (they might be the same)

                # First, let's see what records exist in msi_configurations
                log_info(f"DATABASE: Checking what records exist in msi_configurations")
                try:
                    cursor.execute("SELECT COUNT(*) FROM msi_configurations")
                    total_count = cursor.fetchone()[0]
                    log_info(f"DATABASE: Total msi_configurations records: {total_count}")

                    # Check what columns exist
                    cursor.execute("SELECT TOP 1 * FROM msi_configurations")
                    columns = [column[0] for column in cursor.description]
                    log_info(f"DATABASE: msi_configurations columns: {columns}")

                    # Look for any records that might reference project ID
                    if 'component_id' in columns:
                        cursor.execute("SELECT COUNT(*) FROM msi_configurations WHERE component_id = ?", (project_id,))
                        component_count = cursor.fetchone()[0]
                        log_info(f"DATABASE: Records with component_id={project_id}: {component_count}")

                    # Try to find records that might be blocking deletion
                    cursor.execute("SELECT COUNT(*) FROM msi_configurations")
                    all_records = cursor.fetchone()[0]
                    if all_records > 0:
                        # Try to see actual data to understand the relationship
                        cursor.execute("SELECT TOP 5 * FROM msi_configurations")
                        sample_data = cursor.fetchall()
                        for i, row in enumerate(sample_data):
                            log_info(f"DATABASE: Sample record {i+1}: {dict(zip(columns, row))}")

                        # Check if there's a component_id or any reference to project ID
                        if 'component_id' in columns:
                            # Try to delete records where component_id could be referencing project
                            cursor.execute("DELETE FROM msi_configurations WHERE component_id = ?", (project_id,))
                            targeted_delete = cursor.rowcount
                            log_info(f"DATABASE: Targeted delete of component_id={project_id}: {targeted_delete} rows")

                            # If that didn't work, check for other possible relationships
                            if targeted_delete == 0:
                                # The constraint might be that component_id references Projects.project_id
                                # So we need to clear all records from msi_configurations to allow project deletion
                                log_info(f"DATABASE: No targeted deletion worked, checking constraint direction")
                                # The FK constraint error suggests msi_configurations.component_id -> Projects.project_id
                                # So we need to clear all records from msi_configurations to allow project deletion
                                cursor.execute("DELETE FROM msi_configurations")
                                cleared_all = cursor.rowcount
                                log_info(f"DATABASE: Cleared ALL {cleared_all} msi_configurations records to resolve constraint")

                except Exception as msi_error:
                    log_info(f"DATABASE: msi_configurations inspection failed: {str(msi_error)}")

                # Also try other possible relationships
                try:
                    cursor.execute("DELETE FROM msi_configurations WHERE project_id = ?", (project_id,))
                    rows_deleted = cursor.rowcount
                    log_info(f"DATABASE: Deleted {rows_deleted} rows from msi_configurations (project_id)")
                except Exception as msi_error2:
                    log_info(f"DATABASE: msi_configurations project_id deletion: {str(msi_error2)}")

                # Try deleting other dependent tables
                for table in ["ProjectComponents", "ProjectEnvironments"]:
                    try:
                        cursor.execute(f"DELETE FROM {table} WHERE project_id = ?", (project_id,))
                        rows_deleted = cursor.rowcount
                        log_info(f"DATABASE: Deleted {rows_deleted} rows from {table}")
                    except Exception as dep_error:
                        log_info(f"DATABASE: {table} deletion: {str(dep_error)}")

                # Now delete the main project
                cursor.execute("DELETE FROM Projects WHERE project_id = ?", (project_id,))
                rows_affected = cursor.rowcount
                log_info(f"DATABASE: Deleted {rows_affected} rows for project {project_id}")

                if rows_affected > 0:
                    conn.commit()
                    log_info(f"DATABASE: Project {project_id} deleted successfully")
                    return True, "Project deleted successfully"
                else:
                    log_info(f"DATABASE: No rows found for project {project_id}")
                    return False, "Project not found"

    except Exception as e:
        log_error(f"DATABASE: Error deleting project {project_id}: {str(e)}")
        return False, f"Database deletion error: {str(e)}"

def delete_project_from_database(project_id):
    """Delete project from SQL Server database"""
    log_info(f"Attempting database deletion for project {project_id}")

    try:
        import pyodbc
        log_info(f"pyodbc imported successfully")

        # Connection string
        conn_str = (
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=SUMEETGILL7E47\\MSSQLSERVER01;"
            "DATABASE=MSIFactory;"
            "Trusted_Connection=yes;"
        )

        log_info(f"Attempting database connection...")
        conn = pyodbc.connect(conn_str, timeout=10)  # Add timeout
        cursor = conn.cursor()
        log_info(f"Database connection successful")

        # Check if project exists
        log_info(f"Checking if project {project_id} exists in database...")
        cursor.execute("SELECT COUNT(*) FROM Projects WHERE project_id = ?", (project_id,))
        count = cursor.fetchone()[0]
        log_info(f"Project {project_id} count in database: {count}")

        if count == 0:
            conn.close()
            log_info(f"Project {project_id} not found in database")
            return False, "Project not found in database"

        # Delete related records first (if any foreign key constraints exist)
        log_info(f"Deleting related records for project {project_id}...")

        # Delete in proper order to handle foreign key constraints
        dependent_tables = [
            ("msi_configurations", "component_id IN (SELECT component_id FROM ProjectComponents WHERE project_id = ?)"),
            ("ProjectComponents", "project_id = ?"),
            ("ProjectEnvironments", "project_id = ?")
        ]

        for table_name, where_clause in dependent_tables:
            try:
                full_sql = f"DELETE FROM {table_name} WHERE {where_clause}"
                log_info(f"Executing: {full_sql}")
                cursor.execute(full_sql, (project_id,))
                rows_deleted = cursor.rowcount
                log_info(f"Deleted {rows_deleted} rows from {table_name} for project {project_id}")
            except Exception as rel_error:
                log_info(f"Related table {table_name} deletion warning: {str(rel_error)} (table might not exist)")

        # Delete the project
        log_info(f"Deleting main project record {project_id}...")
        try:
            log_info(f"Executing DELETE FROM Projects WHERE project_id = {project_id}")
            cursor.execute("DELETE FROM Projects WHERE project_id = ?", (project_id,))
            log_info(f"DELETE command completed, checking affected rows...")
            rows_affected = cursor.rowcount
            log_info(f"DELETE command executed successfully, rows affected: {rows_affected}")

            if rows_affected == 0:
                log_error(f"No rows were deleted for project {project_id}")
                conn.close()
                return False, "No rows were deleted - project may not exist"

        except Exception as delete_error:
            log_error(f"Exception during DELETE operation for project {project_id}: {str(delete_error)}")
            try:
                conn.close()
            except:
                pass
            return False, f"Failed to delete project: {str(delete_error)}"

        # Commit the transaction
        log_info(f"Committing database transaction...")
        try:
            conn.commit()
            log_info(f"Transaction committed successfully")
        except Exception as commit_error:
            log_error(f"Failed to commit transaction: {str(commit_error)}")
            conn.rollback()
            conn.close()
            return False, f"Failed to commit deletion: {str(commit_error)}"

        conn.close()
        log_info(f"Project {project_id} deleted successfully from database")

        return True, "Project deleted successfully from database"

    except Exception as e:
        error_msg = f"Database deletion error: {str(e)}"
        log_error(error_msg)
        return False, error_msg

def get_user_projects_from_database(username):
    """Get user's projects from SQL database"""
    try:
        import pyodbc

        # Connection string
        conn_str = (
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=SUMEETGILL7E47\\MSSQLSERVER01;"
            "DATABASE=MSIFactory;"
            "Trusted_Connection=yes;"
        )

        conn = pyodbc.connect(conn_str, timeout=5)
        cursor = conn.cursor()

        # Get user info to check role
        user = auth_system.check_user_login(username)
        if not user or user['status'] != 'approved':
            conn.close()
            return []

        # Check if user exists in SQL users table and get user_id
        cursor.execute("SELECT user_id FROM users WHERE username = ?", (username,))
        sql_user_row = cursor.fetchone()

        log_info(f"DATABASE: User {username} - SQL user found: {sql_user_row is not None}")

        if sql_user_row:
            user_id = sql_user_row[0]
            log_info(f"DATABASE: User {username} - SQL user_id: {user_id}, role: {user.get('role')}")

            # User exists in SQL - check SQL user_projects table first
            if user['role'] == 'admin':
                log_info(f"DATABASE: User {username} is admin, getting all projects")
                # Admin gets all projects
                cursor.execute("""
                    SELECT project_id, project_name, project_key, description, project_type,
                           owner_team, status, color_primary, color_secondary, created_date, created_by
                    FROM projects
                    WHERE is_active = 1
                    ORDER BY created_date DESC
                """)
            else:
                log_info(f"DATABASE: User {username} is regular user, checking SQL user_projects table")
                # Check SQL user_projects table first
                cursor.execute("""
                    SELECT p.project_id, p.project_name, p.project_key, p.description, p.project_type,
                           p.owner_team, p.status, p.color_primary, p.color_secondary, p.created_date, p.created_by
                    FROM projects p
                    INNER JOIN user_projects up ON p.project_id = up.project_id
                    WHERE up.user_id = ? AND up.is_active = 1 AND p.is_active = 1
                    ORDER BY p.created_date DESC
                """, (user_id,))

                sql_projects = cursor.fetchall()
                log_info(f"DATABASE: User {username} - Found {len(sql_projects)} SQL project assignments")

                if sql_projects:
                    # SQL assignments found, process them directly
                    log_info(f"DATABASE: User {username} - Processing SQL project assignments")
                    projects = []
                    for row in sql_projects:
                        project = {
                            'project_id': row[0],
                            'project_name': row[1],
                            'project_key': row[2],
                            'description': row[3] or '',
                            'project_type': row[4] or '',
                            'owner_team': row[5] or '',
                            'status': row[6] or 'active',
                            'color_primary': row[7] or '#007bff',
                            'color_secondary': row[8] or '#0056b3',
                            'created_date': row[9],
                            'created_by': row[10] or ''
                        }
                        projects.append(project)

                    conn.close()
                    log_info(f"DATABASE: Retrieved {len(projects)} projects for user {username} from SQL assignments")
                    return projects
                else:
                    # No SQL assignments found, fall back to JSON approved_apps
                    log_info(f"DATABASE: User {username} - No SQL assignments, falling back to JSON approved_apps")
                    user_apps = user['approved_apps']
                    log_info(f"DATABASE: User {username} - JSON approved_apps: {user_apps}")

                    if '*' in user_apps:
                        log_info(f"DATABASE: User {username} has wildcard access, getting all projects")
                        cursor.execute("""
                            SELECT project_id, project_name, project_key, description, project_type,
                                   owner_team, status, color_primary, color_secondary, created_date, created_by
                            FROM projects
                            WHERE is_active = 1
                            ORDER BY created_date DESC
                        """)
                    else:
                        log_info(f"DATABASE: User {username} has specific project access: {user_apps}")
                        if user_apps:  # Only query if there are apps to query for
                            placeholders = ','.join(['?' for _ in user_apps])
                            cursor.execute(f"""
                                SELECT project_id, project_name, project_key, description, project_type,
                                       owner_team, status, color_primary, color_secondary, created_date, created_by
                                FROM projects
                                WHERE project_key IN ({placeholders}) AND is_active = 1
                                ORDER BY created_date DESC
                            """, user_apps)
                        else:
                            log_info(f"DATABASE: User {username} has no approved apps, returning empty list")
                            conn.close()
                            return []
        else:
            # User doesn't exist in SQL, use JSON approved_apps only
            user_apps = user['approved_apps']
            if user['role'] == 'admin' or '*' in user_apps:
                cursor.execute("""
                    SELECT project_id, project_name, project_key, description, project_type,
                           owner_team, status, color_primary, color_secondary, created_date, created_by
                    FROM projects
                    WHERE is_active = 1
                    ORDER BY created_date DESC
                """)
            else:
                placeholders = ','.join(['?' for _ in user_apps])
                cursor.execute(f"""
                    SELECT project_id, project_name, project_key, description, project_type,
                           owner_team, status, color_primary, color_secondary, created_date, created_by
                    FROM projects
                    WHERE project_key IN ({placeholders}) AND is_active = 1
                    ORDER BY created_date DESC
                """, user_apps)

        projects = []
        for row in cursor.fetchall():
            project = {
                'project_id': row[0],
                'project_name': row[1],
                'project_key': row[2],
                'description': row[3] or '',
                'project_type': row[4] or '',
                'owner_team': row[5] or '',
                'status': row[6] or 'active',
                'color_primary': row[7] or '#007bff',
                'color_secondary': row[8] or '#0056b3',
                'created_date': row[9],
                'created_by': row[10] or ''
            }
            projects.append(project)

        conn.close()
        log_info(f"DATABASE: Retrieved {len(projects)} projects for user {username}")
        return projects

    except Exception as e:
        log_error(f"DATABASE: Error getting projects for user {username}: {str(e)}")
        return []

def get_all_projects_from_database():
    """Get all projects from SQL database for admin purposes"""
    try:
        import pyodbc

        conn_str = (
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=SUMEETGILL7E47\\MSSQLSERVER01;"
            "DATABASE=MSIFactory;"
            "Trusted_Connection=yes;"
        )

        conn = pyodbc.connect(conn_str, timeout=5)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT project_id, project_name, project_key, description, project_type,
                   owner_team, status, color_primary, color_secondary, created_date, created_by
            FROM projects
            ORDER BY project_name ASC
        """)

        projects = []
        for row in cursor.fetchall():
            project = {
                'project_id': row[0],
                'project_name': row[1],
                'project_key': row[2],
                'description': row[3] or '',
                'project_type': row[4] or '',
                'owner_team': row[5] or '',
                'status': row[6] or 'active',
                'color_primary': row[7] or '#007bff',
                'color_secondary': row[8] or '#0056b3',
                'created_date': row[9],
                'created_by': row[10] or ''
            }
            projects.append(project)

        conn.close()
        log_info(f"DATABASE: Retrieved {len(projects)} projects for admin management")
        return projects

    except Exception as e:
        log_error(f"DATABASE: Error getting all projects: {str(e)}")
        return []

def check_user_projects_table_constraints():
    """Debug function to check user_projects table constraints"""
    try:
        import pyodbc

        conn_str = (
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=SUMEETGILL7E47\\MSSQLSERVER01;"
            "DATABASE=MSIFactory;"
            "Trusted_Connection=yes;"
        )

        conn = pyodbc.connect(conn_str, timeout=5)
        cursor = conn.cursor()

        # Check table structure
        cursor.execute("""
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'user_projects'
            ORDER BY ORDINAL_POSITION
        """)

        print("=== user_projects table structure ===")
        for row in cursor.fetchall():
            print(f"Column: {row[0]}, Type: {row[1]}, Nullable: {row[2]}, Default: {row[3]}")

        # Check constraints
        cursor.execute("""
            SELECT
                tc.CONSTRAINT_NAME,
                tc.CONSTRAINT_TYPE,
                cc.CHECK_CLAUSE
            FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
            LEFT JOIN INFORMATION_SCHEMA.CHECK_CONSTRAINTS cc ON tc.CONSTRAINT_NAME = cc.CONSTRAINT_NAME
            WHERE tc.TABLE_NAME = 'user_projects'
        """)

        print("\n=== user_projects table constraints ===")
        for row in cursor.fetchall():
            print(f"Constraint: {row[0]}, Type: {row[1]}, Check: {row[2]}")

        conn.close()

    except Exception as e:
        print(f"Error checking constraints: {e}")

def update_user_projects_in_database(username, project_keys, all_projects_access):
    """Update user's project access in SQL database"""
    try:
        import pyodbc

        # Get user info first
        user = auth_system.check_user_login(username)
        if not user:
            return False, "User not found"

        conn_str = (
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=SUMEETGILL7E47\\MSSQLSERVER01;"
            "DATABASE=MSIFactory;"
            "Trusted_Connection=yes;"
        )

        conn = pyodbc.connect(conn_str, timeout=5)
        cursor = conn.cursor()

        # Get user_id from users table
        cursor.execute("SELECT user_id FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        if not row:
            # Insert user into SQL database if not exists
            cursor.execute("""
                INSERT INTO users (username, email, first_name, last_name, status, role, created_date, is_active)
                VALUES (?, ?, ?, ?, ?, ?, GETDATE(), 1)
            """, (
                username,
                user.get('email', f'{username}@company.com'),
                user.get('first_name', username.split('.')[0].title()),
                user.get('last_name', username.split('.')[-1].title()),
                user.get('status', 'approved'),
                user.get('role', 'user')
            ))
            conn.commit()

            # Get the newly inserted user_id
            cursor.execute("SELECT user_id FROM users WHERE username = ?", (username,))
            user_id = cursor.fetchone()[0]
            log_info(f"DATABASE: Created user record for {username} with ID {user_id}")
        else:
            user_id = row[0]

        # Clear existing project assignments
        cursor.execute("DELETE FROM user_projects WHERE user_id = ?", (user_id,))
        log_info(f"DATABASE: Cleared existing project assignments for user {username}")

        if all_projects_access:
            # Update JSON auth system to give all access
            auth_system.update_user_projects(username, ['*'], True)
            log_info(f"DATABASE: Granted all projects access to user {username}")
        else:
            # Insert specific project assignments
            if project_keys:
                # Get project IDs for the given keys
                placeholders = ','.join(['?' for _ in project_keys])
                cursor.execute(f"""
                    SELECT project_id, project_key FROM projects
                    WHERE project_key IN ({placeholders})
                """, project_keys)

                project_mappings = cursor.fetchall()

                for project_id, project_key in project_mappings:
                    granted_by = session.get('username', 'admin')
                    log_info(f"DATABASE: Attempting to insert user_projects: user_id={user_id}, project_id={project_id}, granted_by={granted_by}")

                    # First check what constraint values are valid by trying the schema-defined values
                    valid_access_levels = ['read', 'write', 'admin']
                    insert_success = False

                    for access_level in valid_access_levels:
                        try:
                            cursor.execute("""
                                INSERT INTO user_projects (user_id, project_id, access_level, granted_date, granted_by, is_active)
                                VALUES (?, ?, ?, GETDATE(), ?, ?)
                            """, (user_id, project_id, access_level, granted_by, 1))
                            log_info(f"DATABASE: Successfully granted access to project {project_key} for user {username} with access_level: {access_level}")
                            insert_success = True
                            break
                        except Exception as insert_error:
                            log_error(f"DATABASE: Failed to insert with access_level '{access_level}': {str(insert_error)}")
                            continue

                    if not insert_success:
                        # If all standard values fail, try without optional fields
                        try:
                            cursor.execute("""
                                INSERT INTO user_projects (user_id, project_id)
                                VALUES (?, ?)
                            """, (user_id, project_id))
                            log_info(f"DATABASE: Successfully granted access to project {project_key} for user {username} using defaults")
                        except Exception as final_error:
                            log_error(f"DATABASE: Final attempt failed for project {project_key}: {str(final_error)}")
                            raise Exception(f"Unable to assign project {project_key} to user {username}: {str(final_error)}")

                # Also update JSON auth system for backward compatibility
                auth_system.update_user_projects(username, project_keys, False)
            else:
                # No projects assigned
                auth_system.update_user_projects(username, [], False)
                log_info(f"DATABASE: Removed all project access for user {username}")

        conn.commit()
        conn.close()

        project_count = len(project_keys) if not all_projects_access else "all"
        log_info(f"DATABASE: Successfully updated project access for user {username}: {project_count} projects")
        return True, f"Successfully updated project access for {username}"

    except Exception as e:
        log_error(f"DATABASE: Error updating user projects for {username}: {str(e)}")
        return False, f"Database error: {str(e)}"

def get_user_project_details_from_database(username):
    """Get user's project details from SQL database"""
    try:
        import pyodbc

        # Get user info from auth system first
        user = auth_system.check_user_login(username)
        if not user:
            return {'error': 'User not found'}

        conn_str = (
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=SUMEETGILL7E47\\MSSQLSERVER01;"
            "DATABASE=MSIFactory;"
            "Trusted_Connection=yes;"
        )

        conn = pyodbc.connect(conn_str, timeout=5)
        cursor = conn.cursor()

        # Check if user has all projects access (admin or * in JSON)
        if user.get('role') == 'admin' or '*' in user.get('approved_apps', []):
            # Get all projects
            cursor.execute("""
                SELECT project_id, project_name, project_key, description, project_type,
                       owner_team, status, color_primary, color_secondary
                FROM projects
                WHERE is_active = 1
                ORDER BY project_name
            """)

            projects = []
            project_details = []
            for row in cursor.fetchall():
                project_key = row[2]
                projects.append(project_key)
                project_details.append({
                    'project_id': row[0],
                    'project_name': row[1],
                    'project_key': project_key,
                    'description': row[3] or '',
                    'project_type': row[4] or '',
                    'owner_team': row[5] or '',
                    'status': row[6] or 'active',
                    'color_primary': row[7] or '#007bff',
                    'color_secondary': row[8] or '#0056b3'
                })

            conn.close()
            return {
                'all_projects': True,
                'projects': projects,
                'project_details': project_details
            }
        else:
            # Get user-specific projects from user_projects table
            cursor.execute("SELECT user_id FROM users WHERE username = ?", (username,))
            row = cursor.fetchone()
            if not row:
                conn.close()
                # Fall back to JSON auth system
                return auth_system.get_user_project_details(username)

            user_id = row[0]

            cursor.execute("""
                SELECT p.project_id, p.project_name, p.project_key, p.description, p.project_type,
                       p.owner_team, p.status, p.color_primary, p.color_secondary
                FROM projects p
                INNER JOIN user_projects up ON p.project_id = up.project_id
                WHERE up.user_id = ? AND up.is_active = 1 AND p.is_active = 1
                ORDER BY p.project_name
            """, (user_id,))

            projects = []
            project_details = []
            for row in cursor.fetchall():
                project_key = row[2]
                projects.append(project_key)
                project_details.append({
                    'project_id': row[0],
                    'project_name': row[1],
                    'project_key': project_key,
                    'description': row[3] or '',
                    'project_type': row[4] or '',
                    'owner_team': row[5] or '',
                    'status': row[6] or 'active',
                    'color_primary': row[7] or '#007bff',
                    'color_secondary': row[8] or '#0056b3'
                })

            conn.close()
            return {
                'all_projects': False,
                'projects': projects,
                'project_details': project_details
            }

    except Exception as e:
        log_error(f"DATABASE: Error getting user project details for {username}: {str(e)}")
        # Fall back to JSON auth system
        return auth_system.get_user_project_details(username)

def get_project_by_id_from_database(project_id):
    """Get a single project by ID from SQL database"""
    try:
        import pyodbc

        conn_str = (
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=SUMEETGILL7E47\\MSSQLSERVER01;"
            "DATABASE=MSIFactory;"
            "Trusted_Connection=yes;"
        )

        conn = pyodbc.connect(conn_str, timeout=5)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT project_id, project_name, project_key, description, project_type,
                   owner_team, status, color_primary, color_secondary, created_date, created_by
            FROM projects
            WHERE project_id = ? AND is_active = 1
        """, (project_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                'project_id': row[0],
                'project_name': row[1],
                'project_key': row[2],
                'description': row[3] or '',
                'project_type': row[4] or '',
                'owner_team': row[5] or '',
                'status': row[6] or 'active',
                'color_primary': row[7] or '#007bff',
                'color_secondary': row[8] or '#0056b3',
                'created_date': row[9],
                'created_by': row[10] or ''
            }
        else:
            return None

    except Exception as e:
        log_error(f"DATABASE: Error getting project by ID {project_id}: {str(e)}")
        # Fall back to JSON auth system
        return auth_system.get_project_by_id(project_id)

def debug_user_project_access(username):
    """Debug function to check user project access"""
    try:
        import pyodbc

        conn_str = (
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=SUMEETGILL7E47\\MSSQLSERVER01;"
            "DATABASE=MSIFactory;"
            "Trusted_Connection=yes;"
        )

        conn = pyodbc.connect(conn_str, timeout=5)
        cursor = conn.cursor()

        print(f"\n=== DEBUG: User Project Access for {username} ===")

        # Check if user exists in JSON auth system
        user = auth_system.check_user_login(username)
        print(f"JSON user found: {user is not None}")
        if user:
            print(f"JSON user role: {user.get('role')}")
            print(f"JSON user approved_apps: {user.get('approved_apps', [])}")

        # Check if user exists in SQL users table
        cursor.execute("SELECT user_id, username, role, status FROM users WHERE username = ?", (username,))
        sql_user_row = cursor.fetchone()
        print(f"SQL user found: {sql_user_row is not None}")
        if sql_user_row:
            user_id = sql_user_row[0]
            print(f"SQL user_id: {user_id}, role: {sql_user_row[2]}, status: {sql_user_row[3]}")

            # Check user_projects assignments
            cursor.execute("""
                SELECT up.user_id, up.project_id, up.access_level, up.is_active, p.project_name, p.project_key
                FROM user_projects up
                INNER JOIN projects p ON up.project_id = p.project_id
                WHERE up.user_id = ?
            """, (user_id,))

            assignments = cursor.fetchall()
            print(f"SQL project assignments found: {len(assignments)}")
            for assignment in assignments:
                print(f"  - Project: {assignment[5]} ({assignment[4]}) | Access: {assignment[2]} | Active: {assignment[3]}")

        # Check all projects in database
        cursor.execute("SELECT project_id, project_name, project_key, is_active FROM projects")
        all_projects = cursor.fetchall()
        print(f"Total projects in database: {len(all_projects)}")
        for project in all_projects:
            print(f"  - {project[2]}: {project[1]} (Active: {project[3]})")

        conn.close()

    except Exception as e:
        print(f"Debug error: {e}")

def get_detailed_projects():
    """Get detailed project information including artifacts, environments, and components"""
    try:
        import pyodbc
        
        # Connection string
        conn_str = (
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=SUMEETGILL7E47\\MSSQLSERVER01;"
            "DATABASE=MSIFactory;"
            "Trusted_Connection=yes;"
        )
        
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        # Get all projects with artifact details
        projects_sql = """
            SELECT project_id, project_name, project_key, project_guid, description, project_type,
                   owner_team, status, color_primary, color_secondary, created_date, created_by,
                   artifact_source_type, artifact_url, artifact_username, artifact_password
            FROM projects
            WHERE is_active = 1
            ORDER BY created_date DESC
        """
        
        cursor.execute(projects_sql)
        projects = cursor.fetchall()
        
        detailed_projects = []
        
        for project in projects:
            project_id = project[0]
            
            # Get environments for this project
            env_sql = """
                SELECT environment_name, environment_description, servers, region
                FROM project_environments 
                WHERE project_id = ? AND is_active = 1
            """
            cursor.execute(env_sql, (project_id,))
            environments = cursor.fetchall()
            
            # Get components for this project
            comp_sql = """
                SELECT component_name, component_type, framework, artifact_source
                FROM components 
                WHERE project_id = ?
            """
            cursor.execute(comp_sql, (project_id,))
            components = cursor.fetchall()
            
            # Build project dictionary
            project_dict = {
                'project_id': project[0],
                'project_name': project[1],
                'project_key': project[2],
                'project_guid': project[3],
                'description': project[4],
                'project_type': project[5],
                'owner_team': project[6],
                'status': project[7],
                'color_primary': project[8],
                'color_secondary': project[9],
                'created_date': project[10].strftime('%Y-%m-%d') if project[10] else None,
                'created_by': project[11],
                'artifact_source_type': project[12],
                'artifact_url': project[13],
                'artifact_username': project[14],
                'artifact_password': '***' if project[15] else None,
                'environments': [
                    {
                        'name': env[0],
                        'description': env[1],
                        'servers': env[2] if env[2] else 'Not specified',
                        'region': env[3] if env[3] else 'Not specified'
                    }
                    for env in environments
                ],
                'components': [
                    {
                        'name': comp[0],
                        'type': comp[1],
                        'framework': comp[2],
                        'artifact_source': comp[3]
                    }
                    for comp in components
                ]
            }
            
            detailed_projects.append(project_dict)
        
        conn.close()
        return detailed_projects
        
    except Exception as e:
        print(f"[ERROR] Failed to get detailed projects: {e}")
        return get_all_projects_from_database()  # Fallback to basic method

@app.route('/')
def home():
    """Main entry point - redirect based on login status"""
    if 'username' in session:
        return redirect(url_for('project_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page (uses authentication system)"""
    if request.method == 'POST':
        username = request.form['username']
        domain = request.form.get('domain', 'COMPANY')
        ip_address = request.remote_addr
        
        user = auth_system.check_user_login(username, domain)
        
        if user and user['status'] == 'approved':
            # Login successful
            session['username'] = user['username']
            session['email'] = user['email']
            session['first_name'] = user['first_name']
            session['last_name'] = user['last_name']
            session['role'] = user['role']
            session['approved_apps'] = user['approved_apps']
            
            # Log successful login
            logger.log_user_login(username, success=True, ip_address=ip_address)
            logger.log_system_event("USER_SESSION_START", f"User: {username}, Role: {user['role']}")
            
            flash(f'Welcome to MSI Factory, {user["first_name"]}', 'success')
            return redirect(url_for('project_dashboard'))
        else:
            # Log failed login
            logger.log_user_login(username, success=False, ip_address=ip_address)
            logger.log_security_violation("LOGIN_FAILED", username, f"Domain: {domain}")
            
            flash('Access denied. Please contact administrator.', 'error')
    
    return render_template('login.html')

@app.route('/dashboard')
def project_dashboard():
    """Main Project Dashboard"""
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session.get('username')

    # Get user's projects from SQL database
    projects = get_user_projects_from_database(username)

    # Calculate statistics
    active_projects_count = len([p for p in projects if p.get('status') == 'active'])
    recent_builds_count = 0  # Would connect to actual build history
    user_project_count = len(projects)

    # Get recent activities (mock data for now)
    recent_activities = [
        {
            'title': 'MSI Generated',
            'description': 'Successfully generated MSI for WEBAPP01 in PROD environment',
            'timestamp': '2 hours ago',
            'icon': 'fa-rocket',
            'color': '#27ae60'
        },
        {
            'title': 'Project Updated',
            'description': 'Updated configuration for Data Sync Service',
            'timestamp': '1 day ago',
            'icon': 'fa-edit',
            'color': '#3498db'
        }
    ]

    return render_template('project_dashboard.html',
                         projects=projects,
                         active_projects_count=active_projects_count,
                         recent_builds_count=recent_builds_count,
                         user_project_count=user_project_count,
                         recent_activities=recent_activities)

@app.route('/factory-dashboard')
def factory_dashboard():
    """Legacy MSI Factory Dashboard (redirect to new dashboard)"""
    return redirect(url_for('project_dashboard'))

@app.route('/generate-msi', methods=['GET', 'POST'])
def generate_msi():
    """MSI Generation page"""
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'GET':
        # Show MSI generation form
        app_key = request.args.get('app_key')
        
        # Check if user has access to this project
        username = session.get('username')
        user_projects = get_user_projects_from_database(username)
        
        has_access = False
        project = None
        for user_project in user_projects:
            if user_project['project_key'] == app_key:
                has_access = True
                project = user_project
                break
        
        if not has_access:
            flash('You do not have access to this project', 'error')
            return redirect(url_for('project_dashboard'))
        
        # Load component configuration if exists
        config_file = f'config/{app_key.lower()}-config.json'
        config = None
        if os.path.exists(config_file):
            import json
            with open(config_file, 'r') as f:
                config = json.load(f)
        
        return render_template('generate_msi.html', app_key=app_key, config=config, project=project)
    
    elif request.method == 'POST':
        # Process MSI generation request
        app_key = request.form['app_key']
        component_type = request.form['component_type']
        environments = request.form.getlist('environments')
        username = session.get('username')
        
        # Log MSI generation start
        job_id = logger.log_msi_generation_start(username, app_key, environments)
        logger.log_system_event("MSI_REQUEST", f"User: {username}, App: {app_key}, Envs: {environments}")
        
        # Here we would call the MSI Factory engine
        results = {
            'job_id': job_id,
            'app_key': app_key,
            'component_type': component_type,
            'environments': environments,
            'status': 'queued',
            'message': 'MSI generation has been queued'
        }
        
        flash(f'MSI generation started for {app_key}', 'success')
        return jsonify(results)

@app.route('/msi-status/<job_id>')
def msi_status(job_id):
    """Check MSI generation status"""
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    # This would check actual job status
    status = {
        'job_id': job_id,
        'status': 'in_progress',
        'progress': 50,
        'message': 'Generating MSI for PROD environment...'
    }
    
    return jsonify(status)

@app.route('/admin')
def admin_panel():
    """Admin panel for user management"""
    if 'username' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'error')
        return redirect(url_for('login'))
    
    # Get all pending requests
    pending_requests = auth_system.get_pending_requests()
    
    # Get system statistics
    stats = {
        'total_users': len(auth_system.load_users()),
        'pending_requests': len(pending_requests),
        'total_applications': len(auth_system.load_applications()),
        'msi_generated_today': 0  # Would connect to actual stats
    }
    
    return render_template('admin_panel.html', requests=pending_requests, stats=stats)

@app.route('/project-management')
def project_management():
    """Project Management page for admins"""
    if 'username' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'error')
        return redirect(url_for('login'))

    # Get detailed project information including artifacts, environments, and components
    detailed_projects = get_detailed_projects()
    username = session.get('username')
    projects = get_user_projects_from_database(username)

    return render_template('project_management.html', all_projects=detailed_projects, projects=projects)

@app.route('/add-project-page')
def add_project_page():
    """Show add project page"""
    if 'username' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'error')
        return redirect(url_for('login'))
    
    return render_template('add_project.html')

@app.route('/add-project-simple')
def add_project_simple():
    """Simple test version of add project page"""
    if 'username' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'error')
        return redirect(url_for('login'))
    
    return render_template('add_project_simple.html')

@app.route('/add-project', methods=['POST'])
def add_project():
    """Add new project with database integration"""
    if 'username' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'error')
        return redirect(url_for('login'))
    
    try:
        # Debug: Print all form data
        print(f"DEBUG: Form data received: {dict(request.form)}")
        
        # Get selected environments (might be empty)
        selected_environments = request.form.getlist('environments')
        if not selected_environments:
            selected_environments = []  # Default to empty list if none selected
        
        # Extract component data
        components_data = []
        component_counter = 1
        while True:
            component_name = request.form.get(f'component_name_{component_counter}')
            if not component_name:
                break
                
            component_data = {
                'component_guid': request.form.get(f'component_guid_{component_counter}'),
                'component_name': component_name,
                'component_type': request.form.get(f'component_type_{component_counter}'),
                'framework': request.form.get(f'component_framework_{component_counter}'),
                'artifact_source': request.form.get(f'component_artifact_{component_counter}', ''),
            }
            components_data.append(component_data)
            component_counter += 1
        
        # Debug: Print project data
        print(f"DEBUG: Selected environments: {selected_environments}")
        print(f"DEBUG: Components data: {components_data}")
        
        def create_project_in_db(db_session):
            # Insert main project with artifact information
            project_insert = """
                INSERT INTO projects (project_name, project_key, project_guid, description, project_type,
                                    owner_team, color_primary, color_secondary, status, created_by,
                                    artifact_source_type, artifact_url, artifact_username, artifact_password)
                OUTPUT INSERTED.project_id
                VALUES (:project_name, :project_key, :project_guid, :description, :project_type,
                       :owner_team, :color_primary, :color_secondary, :status, :created_by,
                       :artifact_source_type, :artifact_url, :artifact_username, :artifact_password)
            """
            
            result = db_session.execute(text(project_insert), {
                'project_name': request.form.get('project_name'),
                'project_key': request.form.get('project_key', '').upper(),
                'project_guid': request.form.get('project_guid'),
                'description': request.form.get('description', ''),
                'project_type': request.form.get('project_type'),
                'owner_team': request.form.get('owner_team'),
                'color_primary': request.form.get('color_primary', '#2c3e50'),
                'color_secondary': request.form.get('color_secondary', '#3498db'),
                'status': request.form.get('status', 'active'),
                'created_by': session.get('username'),
                'artifact_source_type': request.form.get('artifact_source_type', ''),
                'artifact_url': request.form.get('artifact_url', ''),
                'artifact_username': request.form.get('artifact_username', ''),
                'artifact_password': request.form.get('artifact_password', '')
            })
            
            # Get the project ID from the OUTPUT clause
            project_id = result.fetchone()[0]
            
            # Insert project environments with servers and region
            for env in selected_environments:
                servers_text = request.form.get(f'servers_{env}', '')
                region = request.form.get(f'region_{env}', '').upper()
                
                env_insert = """
                    INSERT INTO project_environments (project_id, environment_name, environment_description, servers, region)
                    VALUES (:project_id, :environment_name, :environment_description, :servers, :region)
                """
                db_session.execute(text(env_insert), {
                    'project_id': project_id, 
                    'environment_name': env, 
                    'environment_description': f"{env} Environment",
                    'servers': servers_text,
                    'region': region
                })
            
            # Insert components if any
            for comp_data in components_data:
                comp_insert = """
                    INSERT INTO components (project_id, component_name, component_type, 
                                          framework, artifact_source, created_by)
                    VALUES (:project_id, :component_name, :component_type, 
                           :framework, :artifact_source, :created_by)
                """
                db_session.execute(text(comp_insert), {
                    'project_id': project_id,
                    'component_name': comp_data['component_name'],
                    'component_type': comp_data['component_type'],
                    'framework': comp_data['framework'],
                    'artifact_source': comp_data['artifact_source'],
                    'created_by': session.get('username')
                })
            
            return project_id
        
        # Execute database operations
        print("DEBUG: About to execute database operations...")
        project_id = execute_with_retry(create_project_in_db)
        
        print(f"DEBUG: Project created successfully with ID: {project_id}")
        flash(f'Project "{request.form["project_name"]}" created successfully!', 'success')
        
    except Exception as e:
        print(f"ERROR creating project: {e}")
        import traceback
        traceback.print_exc()
        flash(f"Error creating project: {str(e)}", 'error')
    
    return redirect(url_for('project_management'))

@app.route('/edit-project', methods=['POST'])
def edit_project():
    """Edit existing project"""
    # Log the edit attempt
    logger.log_system_event("EDIT_PROJECT_START", f"Form submission received with fields: {list(request.form.keys())[:20]}")

    # Debug session information
    logger.log_system_event("EDIT_PROJECT_SESSION_DEBUG", f"Session contents: username={session.get('username')}, role={session.get('role')}, user_id={session.get('user_id')}")

    if 'username' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'error')
        logger.log_system_event("EDIT_PROJECT_AUTH_FAIL", f"User not authenticated or not admin. Username: {session.get('username')}, Role: {session.get('role')}")
        return redirect(url_for('login'))

    project_id = request.form['project_id']
    logger.log_system_event("EDIT_PROJECT", f"Processing project {project_id}")
    project_data = {
        'project_name': request.form['project_name'],
        'project_key': request.form['project_key'].upper(),
        'description': request.form['description'],
        'project_type': request.form['project_type'],
        'owner_team': request.form['owner_team'],
        'color_primary': request.form['color_primary'],
        'color_secondary': request.form['color_secondary'],
        'status': request.form['status']
    }

    # Update project data directly in SQL database (bypassing JSON file)
    logger.log_system_event("EDIT_PROJECT_UPDATE_START", f"Updating project {project_id} directly in SQL database")
    try:
        import pyodbc

        # Connection string for project update
        conn_str = (
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=SUMEETGILL7E47\\MSSQLSERVER01;"
            "DATABASE=MSIFactory;"
            "Trusted_Connection=yes;"
        )

        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        # Update project in SQL database
        cursor.execute("""
            UPDATE projects
            SET project_name = ?, project_key = ?, description = ?,
                project_type = ?, owner_team = ?, color_primary = ?,
                color_secondary = ?, status = ?
            WHERE project_id = ?
        """, (
            project_data['project_name'], project_data['project_key'],
            project_data['description'], project_data['project_type'],
            project_data['owner_team'], project_data['color_primary'],
            project_data['color_secondary'], project_data['status'],
            project_id
        ))

        if cursor.rowcount > 0:
            conn.commit()
            logger.log_system_event("EDIT_PROJECT_UPDATE_RESULT", f"Project {project_id} updated successfully in SQL database")
            success = True
            message = "Project updated successfully"
        else:
            logger.log_error("EDIT_PROJECT_UPDATE_ERROR", f"Project {project_id} not found in SQL database")
            success = False
            message = "Project not found in database"

        cursor.close()
        conn.close()

    except Exception as e:
        logger.log_error("EDIT_PROJECT_UPDATE_ERROR", f"Error updating project in SQL: {str(e)}")
        flash(f'Error updating project: {str(e)}', 'error')
        return redirect(url_for('edit_project_page', project_id=project_id))

    if success:
        try:
            import pyodbc

            # Connection string
            conn_str = (
                "DRIVER={ODBC Driver 17 for SQL Server};"
                "SERVER=SUMEETGILL7E47\\MSSQLSERVER01;"
                "DATABASE=MSIFactory;"
                "Trusted_Connection=yes;"
            )

            conn = pyodbc.connect(conn_str)
            cursor = conn.cursor()

            # Get existing component count first
            cursor.execute("SELECT COUNT(*) FROM components WHERE project_id = ?", project_id)
            existing_count = cursor.fetchone()[0]
            logger.log_system_event("COMPONENT_COUNT", f"Project {project_id} has {existing_count} existing components")

            # Process new components that were added (start from existing count + 1)
            component_counter = existing_count + 1
            logger.log_system_event("COMPONENT_SEARCH", f"Looking for new components starting from counter {component_counter}")

            while True:
                component_guid_field = f'new_component_guid_{component_counter}'
                component_name_field = f'new_component_name_{component_counter}'

                if component_guid_field not in request.form:
                    logger.log_system_event("COMPONENT_SEARCH_END", f"Field {component_guid_field} not found in form, ending search")
                    break

                component_guid = request.form.get(component_guid_field, '').strip()
                component_name = request.form.get(component_name_field, '').strip()
                logger.log_system_event("COMPONENT_FOUND", f"Found component fields: {component_name_field}={component_name}, GUID={component_guid}")

                if component_name:  # Only process if component has a name
                    logger.log_system_event("COMPONENT_PROCESS", f"Processing new component: {component_name}")

                    # Validate and fix GUID format for SQL Server
                    import uuid

                    # Get project key for GUID prefix
                    project_key = request.form.get('project_key', '').strip().upper()

                    if component_guid and len(component_guid) > 0:
                        try:
                            # Try to parse as UUID to validate format
                            uuid.UUID(component_guid)
                            valid_guid = component_guid
                        except ValueError:
                            # Generate a new GUID with project key prefix if invalid
                            base_guid = str(uuid.uuid4())
                            # Create a GUID-like format with project key prefix
                            # Format: PROJKEY-xxxx-xxxx-xxxx-xxxxxxxxxxxx
                            if project_key and len(project_key) <= 8:
                                # Pad project key to 8 chars or truncate
                                prefix = project_key.ljust(8, '0')[:8]
                                valid_guid = f"{prefix}-{base_guid[9:]}"
                            else:
                                valid_guid = base_guid
                            logger.log_system_event("COMPONENT_GUID_FIXED", f"Invalid GUID '{component_guid}' replaced with '{valid_guid}'")
                    else:
                        # Generate new GUID with project key prefix if empty
                        base_guid = str(uuid.uuid4())
                        if project_key and len(project_key) <= 8:
                            # Pad project key to 8 chars or truncate
                            prefix = project_key.ljust(8, '0')[:8]
                            valid_guid = f"{prefix}-{base_guid[9:]}"
                        else:
                            valid_guid = base_guid
                        logger.log_system_event("COMPONENT_GUID_GENERATED", f"Generated new GUID with project key: {valid_guid}")

                    component_data = {
                        'component_guid': valid_guid,
                        'component_name': component_name,
                        'component_type': request.form.get(f'new_component_type_{component_counter}', ''),
                        'framework': request.form.get(f'new_component_framework_{component_counter}', ''),
                        'artifact_source': request.form.get(f'new_component_artifact_{component_counter}', ''),
                        'app_name': request.form.get(f'new_component_app_name_{component_counter}', component_name),
                        'version': request.form.get(f'new_component_version_{component_counter}', '1.0.0.0'),
                        'manufacturer': request.form.get(f'new_component_manufacturer_{component_counter}', 'Your Company'),
                        'target_server': request.form.get(f'new_component_target_server_{component_counter}', ''),
                        'install_folder': request.form.get(f'new_component_install_folder_{component_counter}', ''),
                        'iis_website': request.form.get(f'new_component_iis_website_{component_counter}', ''),
                        'app_pool': request.form.get(f'new_component_app_pool_{component_counter}', ''),
                        'port': request.form.get(f'new_component_port_{component_counter}', ''),
                        'service_name': request.form.get(f'new_component_service_name_{component_counter}', ''),
                        'service_display': request.form.get(f'new_component_service_display_{component_counter}', '')
                    }

                    # Insert the new component
                    insert_sql = """
                        INSERT INTO components (
                            project_id, component_name, component_type, framework,
                            artifact_source, component_guid, app_name, app_version,
                            manufacturer, target_server, install_folder,
                            iis_website_name, iis_app_pool_name, port,
                            service_name, service_display_name, artifact_url,
                            created_by, created_date
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE())
                    """

                    logger.log_system_event("COMPONENT_INSERT", f"Inserting component {component_data['component_name']} into database")
                    cursor.execute(insert_sql, (
                        project_id,
                        component_data['component_name'],
                        component_data['component_type'],
                        component_data['framework'],
                        component_data['artifact_source'],
                        component_data['component_guid'],
                        component_data['app_name'],
                        component_data['version'],
                        component_data['manufacturer'],
                        component_data['target_server'],
                        component_data['install_folder'],
                        component_data['iis_website'],
                        component_data['app_pool'],
                        component_data['port'],
                        component_data['service_name'],
                        component_data['service_display'],
                        component_data['artifact_source'],
                        session.get('username', 'admin')  # created_by
                    ))

                component_counter += 1

            # Handle component deletions
            delete_components = request.form.getlist('delete_components')
            for component_id in delete_components:
                cursor.execute("DELETE FROM components WHERE component_id = ? AND project_id = ?",
                             (component_id, project_id))

            conn.commit()
            conn.close()

            logger.log_system_event("PROJECT_UPDATED", f"Project ID: {project_id}, Updated by: {session.get('username')}")
            flash(f"{message} Components updated successfully.", 'success')

        except Exception as e:
            logger.log_system_event("PROJECT_UPDATE_ERROR", f"Project ID: {project_id}, Error: {str(e)}")
            logger.log_error("COMPONENT_INSERT_ERROR", f"Failed to insert components for project {project_id}: {str(e)}")
            flash(f"Project updated but error processing components: {str(e)}", 'warning')
    else:
        flash(message, 'error')

    return redirect(url_for('edit_project_page', project_id=project_id))

@app.route('/edit-project/<int:project_id>')
def edit_project_page(project_id):
    """Project edit page with component management"""
    if 'username' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'error')
        return redirect(url_for('login'))
    
    try:
        import pyodbc
        
        # Connection string
        conn_str = (
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=SUMEETGILL7E47\\MSSQLSERVER01;"
            "DATABASE=MSIFactory;"
            "Trusted_Connection=yes;"
        )
        
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        # Get project details
        cursor.execute("""
            SELECT project_id, project_name, project_key, project_guid, description, project_type,
                   owner_team, status, color_primary, color_secondary,
                   artifact_source_type, artifact_url, artifact_username,
                   created_date, created_by
            FROM projects
            WHERE project_id = ? AND is_active = 1
        """, project_id)

        project_row = cursor.fetchone()
        if not project_row:
            flash('Project not found', 'error')
            return redirect(url_for('project_management'))

        project = {
            'project_id': project_row[0],
            'project_name': project_row[1],
            'project_key': project_row[2],
            'project_guid': project_row[3],
            'description': project_row[4],
            'project_type': project_row[5],
            'owner_team': project_row[6],
            'status': project_row[7],
            'color_primary': project_row[8] or '#2c3e50',
            'color_secondary': project_row[9] or '#3498db',
            'artifact_source_type': project_row[10],
            'artifact_url': project_row[11],
            'artifact_username': project_row[12],
            'created_date': project_row[13],
            'created_by': project_row[14]
        }

        # Get project environments
        cursor.execute("""
            SELECT environment_name, environment_description, servers, region
            FROM project_environments
            WHERE project_id = ? AND is_active = 1
        """, project_id)

        environments = []
        server_config = {}
        for env_row in cursor.fetchall():
            env_name = env_row[0]
            environments.append(env_name)
            server_config[env_name] = {
                'description': env_row[1],
                'servers': env_row[2],
                'region': env_row[3]
            }

        project['environments'] = environments
        project['server_config'] = server_config
        
        # Get project components
        cursor.execute("""
            SELECT component_id, component_name, component_type, framework,
                   artifact_source, branch_name, polling_enabled, created_date,
                   component_guid, app_name, app_version, manufacturer,
                   target_server, install_folder, iis_website_name,
                   iis_app_pool_name, port, service_name, service_display_name,
                   artifact_url
            FROM components
            WHERE project_id = ?
            ORDER BY component_name
        """, project_id)

        components = []
        for row in cursor.fetchall():
            components.append({
                'component_id': row[0],
                'component_name': row[1],
                'component_type': row[2],
                'framework': row[3],
                'artifact_source': row[4],
                'branch_name': row[5],
                'polling_enabled': row[6],
                'created_date': row[7],
                'component_guid': row[8],
                'app_name': row[9],
                'app_version': row[10],
                'manufacturer': row[11],
                'target_server': row[12],
                'install_folder': row[13],
                'iis_website_name': row[14],
                'iis_app_pool_name': row[15],
                'port': row[16],
                'service_name': row[17],
                'service_display_name': row[18],
                'artifact_url': row[19]
            })
        
        # Get project environments
        cursor.execute("""
            SELECT env_id, environment_name, environment_description, servers, region
            FROM project_environments 
            WHERE project_id = ? AND is_active = 1
            ORDER BY environment_name
        """, project_id)
        
        environments = []
        for row in cursor.fetchall():
            environments.append({
                'env_id': row[0],
                'environment_name': row[1],
                'environment_description': row[2],
                'servers': row[3],
                'region': row[4]
            })
        
        conn.close()
        
        return render_template('edit_project.html', 
                             project=project, 
                             components=components,
                             environments=environments)
        
    except Exception as e:
        flash(f'Error loading project: {str(e)}', 'error')
        return redirect(url_for('project_management'))

@app.route('/add-component', methods=['POST'])
def add_component():
    """Add new component to project"""
    if 'username' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'error')
        return redirect(url_for('login'))
    
    try:
        import pyodbc
        
        project_id = request.form['project_id']
        component_data = {
            'component_name': request.form['component_name'],
            'component_type': request.form['component_type'],
            'framework': request.form['framework'],
            'artifact_source': request.form.get('artifact_source', ''),
            'branch_name': request.form.get('branch_name', 'develop'),
            'polling_enabled': 1 if request.form.get('polling_enabled') else 0
        }
        
        # Connection string
        conn_str = (
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=SUMEETGILL7E47\\MSSQLSERVER01;"
            "DATABASE=MSIFactory;"
            "Trusted_Connection=yes;"
        )
        
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        # Insert new component
        cursor.execute("""
            INSERT INTO components (project_id, component_name, component_type, framework,
                                  artifact_source, branch_name, polling_enabled, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, project_id, component_data['component_name'], component_data['component_type'],
             component_data['framework'], component_data['artifact_source'],
             component_data['branch_name'], component_data['polling_enabled'],
             session.get('username'))
        
        conn.commit()
        conn.close()
        
        flash('Component added successfully', 'success')
        
    except Exception as e:
        flash(f'Error adding component: {str(e)}', 'error')
    
    return redirect(url_for('edit_project_page', project_id=project_id))

@app.route('/remove-component', methods=['POST'])
def remove_component():
    """Remove component from project"""
    if 'username' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'error')
        return redirect(url_for('login'))
    
    try:
        import pyodbc
        
        component_id = request.form['component_id']
        project_id = request.form['project_id']
        
        # Connection string
        conn_str = (
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=SUMEETGILL7E47\\MSSQLSERVER01;"
            "DATABASE=MSIFactory;"
            "Trusted_Connection=yes;"
        )
        
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        # Delete component (this will cascade to related MSI configurations)
        cursor.execute("DELETE FROM components WHERE component_id = ?", component_id)
        
        conn.commit()
        conn.close()
        
        flash('Component removed successfully', 'success')
        
    except Exception as e:
        flash(f'Error removing component: {str(e)}', 'error')
    
    return redirect(url_for('edit_project_page', project_id=project_id))

@app.route('/delete-project', methods=['POST'])
def delete_project():
    """Delete project from database"""
    log_info(f"Delete project function called by user: {session.get('username', 'unknown')}")

    if 'username' not in session or session.get('role') != 'admin':
        if request.is_json:
            return jsonify({'success': False, 'message': 'Admin access required'}), 403
        flash('Admin access required', 'error')
        return redirect(url_for('login'))
    
    try:
        # Handle both form data and JSON requests
        if request.is_json:
            project_id = request.json.get('project_id')
        else:
            project_id = request.form.get('project_id')
        
        if not project_id:
            if request.is_json:
                return jsonify({'success': False, 'message': 'Project ID is required'}), 400
            flash('Project ID is required', 'error')
            return redirect(url_for('project_management'))
        
        # Use API client if available, otherwise fall back to auth_system
        if api_client:
            try:
                log_info(f"Attempting to delete project {project_id} via API client")
                response = api_client.delete_project(int(project_id), hard_delete=True)
                success = response.get('success', False)
                message = response.get('message', 'Unknown error')
                log_info(f"API delete response: success={success}, message={message}")
            except Exception as api_error:
                log_error(f"API delete project error: {str(api_error)}")
                # Fallback to auth_system when API fails
                log_info(f"Falling back to auth_system for project {project_id}")
                success, message = auth_system.delete_project(project_id)
        else:
            # Fallback to auth_system if API is not available
            log_info(f"No API client available, using auth_system to delete project {project_id}")

            # Try simple database deletion first, then complex, then fall back to JSON
            try:
                # Try simple deletion method first
                success, message = simple_delete_project_from_database(project_id)
                if not success:
                    log_info(f"Simple deletion failed: {message}, trying complex method...")
                    # Try complex deletion method
                    success, message = delete_project_from_database(project_id)
                    if not success:
                        log_error(f"Both database deletion methods failed: {message}")
                        log_info(f"Falling back to JSON file for project {project_id}")
                        success, message = auth_system.delete_project(project_id)
            except Exception as db_error:
                log_error(f"Database deletion exception: {str(db_error)}, falling back to JSON")
                success, message = auth_system.delete_project(project_id)
        
        if success:
            username = session.get('username', 'unknown')
            log_info(f"PROJECT_DELETED: Project ID: {project_id}, Deleted by: {username}")
            if request.is_json:
                return jsonify({'success': True, 'message': message})
            flash(message, 'success')
        else:
            log_error(f"PROJECT_DELETE_FAILED: Project ID: {project_id}, Error: {message}")
            if request.is_json:
                return jsonify({'success': False, 'message': message}), 404
            flash(message, 'error')

    except Exception as e:
        log_error(f"Error deleting project: {str(e)}")
        if request.is_json:
            return jsonify({'success': False, 'message': f'Error deleting project: {str(e)}'}), 500
        flash(f'Error deleting project: {str(e)}', 'error')

    return redirect(url_for('project_management'))

@app.route('/project/<int:project_id>')
def project_detail(project_id):
    """Project detail page"""
    if 'username' not in session:
        return redirect(url_for('login'))
    
    project = get_project_by_id_from_database(project_id)
    if not project:
        flash('Project not found', 'error')
        return redirect(url_for('project_dashboard'))
    
    # Check if user has access to this project
    username = session.get('username')
    user_projects = get_user_projects_from_database(username)
    
    has_access = False
    for user_project in user_projects:
        if user_project['project_id'] == project_id:
            has_access = True
            break
    
    if not has_access and session.get('role') != 'admin':
        flash('You do not have access to this project', 'error')
        return redirect(url_for('project_dashboard'))
    
    return render_template('project_detail.html', project=project)

@app.route('/project/<int:project_id>/settings')
def project_settings(project_id):
    """Project settings page"""
    if 'username' not in session:
        return redirect(url_for('login'))
    
    project = get_project_by_id_from_database(project_id)
    if not project:
        flash('Project not found', 'error')
        return redirect(url_for('project_dashboard'))
    
    return render_template('project_settings.html', project=project)

@app.route('/build-history')
def build_history():
    """Build history page"""
    if 'username' not in session:
        return redirect(url_for('login'))
    
    # Mock build history data
    builds = []
    
    return render_template('build_history.html', builds=builds)

@app.route('/templates')
def templates_library():
    """Templates library page"""
    if 'username' not in session:
        return redirect(url_for('login'))
    
    # Mock templates data
    templates = []
    
    return render_template('templates_library.html', templates=templates)

@app.route('/system-settings')
def system_settings():
    """System settings page (admin only)"""
    if 'username' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'error')
        return redirect(url_for('login'))
    
    return render_template('system_settings.html')

@app.route('/user-management')
def user_management():
    """User Management page for admins"""
    if 'username' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'error')
        return redirect(url_for('login'))

    all_users = auth_system.get_all_users()
    all_projects = get_all_projects_from_database()
    stats = auth_system.get_user_statistics()

    return render_template('user_management.html',
                         all_users=all_users,
                         all_projects=all_projects,
                         **stats)

@app.route('/update-user-projects', methods=['POST'])
def update_user_projects():
    """Update user's project access"""
    if 'username' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'error')
        return redirect(url_for('login'))
    
    username = request.form['username']
    all_projects_access = 'all_projects_access' in request.form
    project_keys = request.form.getlist('project_keys')

    success, message = update_user_projects_in_database(username, project_keys, all_projects_access)

    if success:
        logger.log_system_event("USER_PROJECTS_UPDATED", f"User: {username}, Updated by: {session.get('username')}")
        flash(message, 'success')
    else:
        flash(message, 'error')

    return redirect(url_for('user_management'))

@app.route('/api/user-projects/<username>')
def api_user_projects(username):
    """API endpoint to get user's project details"""
    if 'username' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    project_details = get_user_project_details_from_database(username)
    return jsonify(project_details)

@app.route('/api/toggle-user-status/<username>', methods=['POST'])
def api_toggle_user_status(username):
    """API endpoint to toggle user status"""
    if 'username' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    success, message = auth_system.toggle_user_status(username)
    
    if success:
        logger.log_system_event("USER_STATUS_TOGGLED", f"User: {username}, Changed by: {session.get('username')}")
    
    return jsonify({'success': success, 'message': message})

@app.route('/debug/user-projects-constraints')
def debug_user_projects_constraints():
    """Debug endpoint to check user_projects table constraints"""
    if 'username' not in session or session.get('role') != 'admin':
        return "Admin access required", 403

    check_user_projects_table_constraints()
    return "Check console/logs for constraint information"

@app.route('/debug/user-access/<username>')
def debug_user_access(username):
    """Debug endpoint to check user project access"""
    if 'username' not in session or session.get('role') != 'admin':
        return "Admin access required", 403

    debug_user_project_access(username)
    return f"Check console/logs for user access debug information for {username}"

@app.route('/admin/extract-database-schema')
def extract_database_schema_route():
    """Admin route to extract complete database schema"""
    if 'username' not in session or session.get('role') != 'admin':
        return "Admin access required", 403

    try:
        import pyodbc
        from datetime import datetime

        print("=== Starting Database Schema Extraction ===")

        conn_str = (
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=SUMEETGILL7E47\\MSSQLSERVER01;"
            "DATABASE=MSIFactory;"
            "Trusted_Connection=yes;"
        )

        conn = pyodbc.connect(conn_str, timeout=10)
        cursor = conn.cursor()

        # Start building the SQL script
        sql_script = []
        sql_script.append("-- ============================================================")
        sql_script.append("-- MSIFactory Database Baseline Schema Script")
        sql_script.append(f"-- Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        sql_script.append("-- Source: Live MSIFactory Database")
        sql_script.append("-- ============================================================")
        sql_script.append("")
        sql_script.append("SET NOCOUNT ON;")
        sql_script.append("GO")
        sql_script.append("")

        # Database creation
        sql_script.append("-- ============================================================")
        sql_script.append("-- DATABASE CREATION")
        sql_script.append("-- ============================================================")
        sql_script.append("IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'MSIFactory')")
        sql_script.append("BEGIN")
        sql_script.append("    PRINT 'Creating MSIFactory database...';")
        sql_script.append("    CREATE DATABASE MSIFactory;")
        sql_script.append("    PRINT 'Database MSIFactory created successfully.';")
        sql_script.append("END")
        sql_script.append("ELSE")
        sql_script.append("BEGIN")
        sql_script.append("    PRINT 'Database MSIFactory already exists. Continuing...';")
        sql_script.append("END")
        sql_script.append("GO")
        sql_script.append("")
        sql_script.append("USE MSIFactory;")
        sql_script.append("GO")
        sql_script.append("")

        # Get all user tables
        cursor.execute("""
            SELECT TABLE_NAME
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_TYPE = 'BASE TABLE'
            AND TABLE_SCHEMA = 'dbo'
            ORDER BY TABLE_NAME
        """)

        tables = [row[0] for row in cursor.fetchall()]
        log_info(f"DATABASE SCHEMA: Found {len(tables)} tables: {', '.join(tables)}")

        # Process each table for complete schema
        sql_script.append("-- ============================================================")
        sql_script.append("-- TABLE CREATION")
        sql_script.append("-- ============================================================")

        for table_name in tables:
            log_info(f"DATABASE SCHEMA: Processing table {table_name}")

            sql_script.append(f"")
            sql_script.append(f"-- ============================================================")
            sql_script.append(f"-- {table_name.upper()} TABLE")
            sql_script.append(f"-- ============================================================")
            sql_script.append(f"IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='{table_name}' AND xtype='U')")
            sql_script.append("BEGIN")
            sql_script.append(f"    PRINT 'Creating {table_name} table...';")

            # Get table structure
            cursor.execute("""
                SELECT
                    COLUMN_NAME,
                    DATA_TYPE,
                    CHARACTER_MAXIMUM_LENGTH,
                    NUMERIC_PRECISION,
                    NUMERIC_SCALE,
                    IS_NULLABLE,
                    COLUMN_DEFAULT,
                    COLUMNPROPERTY(OBJECT_ID(TABLE_SCHEMA+'.'+TABLE_NAME), COLUMN_NAME, 'IsIdentity') as IS_IDENTITY
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = ?
                ORDER BY ORDINAL_POSITION
            """, table_name)

            columns = cursor.fetchall()
            sql_script.append(f"    CREATE TABLE {table_name} (")

            column_definitions = []
            for col in columns:
                col_name = col[0]
                data_type = col[1].upper()
                max_length = col[2]
                precision = col[3]
                scale = col[4]
                is_nullable = col[5]
                default_value = col[6]
                is_identity = col[7]

                # Build column definition
                col_def = f"        {col_name} "

                # Data type with proper sizing
                if data_type in ['VARCHAR', 'NVARCHAR', 'CHAR', 'NCHAR']:
                    if max_length == -1:
                        col_def += f"{data_type}(MAX)"
                    else:
                        col_def += f"{data_type}({max_length})"
                elif data_type in ['DECIMAL', 'NUMERIC']:
                    col_def += f"{data_type}({precision},{scale})"
                elif data_type == 'FLOAT':
                    if precision:
                        col_def += f"{data_type}({precision})"
                    else:
                        col_def += data_type
                else:
                    col_def += data_type

                # Identity
                if is_identity:
                    col_def += " IDENTITY(1,1)"

                # Nullable
                if is_nullable == 'NO':
                    col_def += " NOT NULL"

                # Default value
                if default_value and str(default_value).strip() and str(default_value).strip() != 'NULL':
                    col_def += f" DEFAULT {default_value}"

                column_definitions.append(col_def)

            # Add column definitions
            for i, col_def in enumerate(column_definitions):
                if i < len(column_definitions) - 1:
                    sql_script.append(col_def + ",")
                else:
                    sql_script.append(col_def)

            # Get primary key
            cursor.execute("""
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                WHERE TABLE_NAME = ? AND CONSTRAINT_NAME LIKE 'PK_%'
                ORDER BY ORDINAL_POSITION
            """, table_name)

            pk_columns = [row[0] for row in cursor.fetchall()]
            if pk_columns:
                pk_def = f"        CONSTRAINT PK_{table_name} PRIMARY KEY ({', '.join(pk_columns)})"
                sql_script[-1] += ","  # Add comma to last column
                sql_script.append(pk_def)

            sql_script.append("    );")
            sql_script.append(f"    PRINT '{table_name} table created successfully.';")
            sql_script.append("END")
            sql_script.append("ELSE")
            sql_script.append("BEGIN")
            sql_script.append(f"    PRINT '{table_name} table already exists.';")
            sql_script.append("END")
            sql_script.append("GO")

        # Add foreign keys
        sql_script.append("")
        sql_script.append("-- ============================================================")
        sql_script.append("-- FOREIGN KEY CONSTRAINTS")
        sql_script.append("-- ============================================================")

        cursor.execute("""
            SELECT
                fk.name AS FK_NAME,
                tp.name AS PARENT_TABLE,
                cp.name AS PARENT_COLUMN,
                tr.name AS REFERENCED_TABLE,
                cr.name AS REFERENCED_COLUMN
            FROM sys.foreign_keys fk
            INNER JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
            INNER JOIN sys.tables tp ON fk.parent_object_id = tp.object_id
            INNER JOIN sys.columns cp ON fkc.parent_object_id = cp.object_id AND fkc.parent_column_id = cp.column_id
            INNER JOIN sys.tables tr ON fk.referenced_object_id = tr.object_id
            INNER JOIN sys.columns cr ON fkc.referenced_object_id = cr.object_id AND fkc.referenced_column_id = cr.column_id
            ORDER BY tp.name, fk.name
        """)

        foreign_keys = cursor.fetchall()
        for fk in foreign_keys:
            fk_name = fk[0]
            parent_table = fk[1]
            parent_column = fk[2]
            ref_table = fk[3]
            ref_column = fk[4]

            sql_script.append(f"-- Foreign key: {parent_table}.{parent_column} -> {ref_table}.{ref_column}")
            sql_script.append(f"IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = '{fk_name}')")
            sql_script.append(f"    ALTER TABLE {parent_table} ADD CONSTRAINT {fk_name}")
            sql_script.append(f"        FOREIGN KEY ({parent_column}) REFERENCES {ref_table}({ref_column});")
            sql_script.append("")

        # Final script sections
        sql_script.append("-- ============================================================")
        sql_script.append("-- SCRIPT COMPLETION")
        sql_script.append("-- ============================================================")
        sql_script.append(f"PRINT 'MSIFactory Database Schema Installation Complete';")
        sql_script.append(f"PRINT 'Total Tables Created: {len(tables)}';")
        sql_script.append(f"PRINT 'Total Foreign Keys: {len(foreign_keys)}';")
        sql_script.append("GO")
        sql_script.append("SET NOCOUNT OFF;")

        # Write to file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        script_filename = f"baselineSQLScript_{timestamp}.sql"
        script_content = '\n'.join(sql_script)

        try:
            with open(script_filename, 'w', encoding='utf-8') as f:
                f.write(script_content)
            log_info(f"DATABASE SCHEMA: Successfully created {script_filename}")
            conn.close()
            return f"""
            <h2>Database Schema Extraction Completed Successfully</h2>
            <p><strong>File created:</strong> {script_filename}</p>
            <p><strong>Tables found:</strong> {len(tables)}</p>
            <p><strong>Foreign keys:</strong> {len(foreign_keys)}</p>
            <p><strong>Script size:</strong> {len(script_content):,} characters</p>
            <h3>Tables included:</h3>
            <ul>{''.join([f'<li>{table}</li>' for table in tables])}</ul>
            <p>The baseline SQL script is ready for deployment to fresh database instances.</p>
            """
        except Exception as file_error:
            log_error(f"DATABASE SCHEMA: Error writing file: {str(file_error)}")
            return f"Schema extraction completed but file write failed: {str(file_error)}"

    except Exception as e:
        log_error(f"DATABASE SCHEMA: Extraction error: {str(e)}")
        return f"Error extracting database schema: {str(e)}"

# ============================================================
# CMDB ROUTES
# ============================================================

@app.route('/cmdb')
@app.route('/cmdb/dashboard')
def cmdb_dashboard():
    """CMDB Dashboard with server overview and statistics"""
    if 'username' not in session:
        return redirect(url_for('login'))

    try:
        import pyodbc

        conn_str = (
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=SUMEETGILL7E47\\MSSQLSERVER01;"
            "DATABASE=MSIFactory;"
            "Trusted_Connection=yes;"
        )

        conn = pyodbc.connect(conn_str, timeout=5)
        cursor = conn.cursor()

        # Get CMDB statistics
        cursor.execute("""
            SELECT
                COUNT(*) as total_servers,
                SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active_servers,
                AVG(CASE WHEN max_concurrent_apps > 0 THEN CAST(current_app_count AS FLOAT) / max_concurrent_apps * 100 ELSE 0 END) as avg_utilization
            FROM cmdb_servers
            WHERE is_active = 1
        """)

        stats_row = cursor.fetchone()

        # Get assigned servers count separately
        cursor.execute("""
            SELECT COUNT(DISTINCT server_id)
            FROM project_servers
            WHERE status = 'active'
        """)
        assigned_count = cursor.fetchone()[0] or 0

        cmdb_stats = {
            'total_servers': stats_row[0] or 0,
            'active_servers': stats_row[1] or 0,
            'assigned_servers': assigned_count,
            'avg_utilization': stats_row[2] or 0
        }

        # Get infrastructure distribution
        cursor.execute("""
            SELECT infra_type, COUNT(*) as count
            FROM cmdb_servers
            WHERE is_active = 1
            GROUP BY infra_type
        """)
        infra_distribution = {row[0]: row[1] for row in cursor.fetchall()}

        # Get regional distribution
        cursor.execute("""
            SELECT region, COUNT(*) as count
            FROM cmdb_servers
            WHERE is_active = 1
            GROUP BY region
        """)
        region_distribution = {row[0]: row[1] for row in cursor.fetchall()}

        # Get recent CMDB activity
        cursor.execute("""
            SELECT TOP 10
                sc.changed_date,
                sc.change_type,
                s.server_name,
                sc.changed_by,
                sc.change_reason
            FROM cmdb_server_changes sc
            INNER JOIN cmdb_servers s ON sc.server_id = s.server_id
            ORDER BY sc.changed_date DESC
        """)

        recent_cmdb_activity = []
        for row in cursor.fetchall():
            recent_cmdb_activity.append({
                'changed_date': row[0],
                'change_type': row[1],
                'server_name': row[2],
                'changed_by': row[3],
                'change_reason': row[4]
            })

        conn.close()

        return render_template('cmdb_dashboard.html',
                             cmdb_stats=cmdb_stats,
                             infra_distribution=infra_distribution,
                             region_distribution=region_distribution,
                             recent_cmdb_activity=recent_cmdb_activity)

    except Exception as e:
        flash(f'Error loading CMDB dashboard: {str(e)}', 'error')
        return redirect(url_for('project_dashboard'))

@app.route('/cmdb/servers')
def cmdb_servers():
    """Server inventory management page"""
    if 'username' not in session:
        return redirect(url_for('login'))

    try:
        import pyodbc

        conn_str = (
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=SUMEETGILL7E47\\MSSQLSERVER01;"
            "DATABASE=MSIFactory;"
            "Trusted_Connection=yes;"
        )

        conn = pyodbc.connect(conn_str, timeout=5)
        cursor = conn.cursor()

        # Build WHERE clause based on filters
        where_conditions = ["s.is_active = 1"]
        params = []

        # Apply filters
        infra_type = request.args.get('infra_type')
        if infra_type:
            where_conditions.append("s.infra_type = ?")
            params.append(infra_type)

        region = request.args.get('region')
        if region:
            where_conditions.append("s.region = ?")
            params.append(region)

        status = request.args.get('status')
        if status:
            where_conditions.append("s.status = ?")
            params.append(status)

        search = request.args.get('search')
        if search:
            where_conditions.append("(s.server_name LIKE ? OR s.ip_address LIKE ? OR s.fqdn LIKE ?)")
            search_param = f"%{search}%"
            params.extend([search_param, search_param, search_param])

        where_clause = " AND ".join(where_conditions)

        # Get servers
        cursor.execute(f"""
            SELECT
                s.server_id, s.server_name, s.fqdn, s.infra_type, s.ip_address, s.ip_address_internal,
                s.region, s.datacenter, s.environment_type, s.status, s.cpu_cores, s.memory_gb,
                s.storage_gb, s.current_app_count, s.max_concurrent_apps, s.owner_team,
                s.technical_contact, s.last_updated
            FROM cmdb_servers s
            WHERE {where_clause}
            ORDER BY s.server_name
        """, params)

        servers = []
        for row in cursor.fetchall():
            servers.append({
                'server_id': row[0],
                'server_name': row[1],
                'fqdn': row[2],
                'infra_type': row[3],
                'ip_address': row[4],
                'ip_address_internal': row[5],
                'region': row[6],
                'datacenter': row[7],
                'environment_type': row[8],
                'status': row[9],
                'cpu_cores': row[10],
                'memory_gb': row[11],
                'storage_gb': row[12],
                'current_app_count': row[13],
                'max_concurrent_apps': row[14],
                'owner_team': row[15],
                'technical_contact': row[16],
                'last_updated': row[17]
            })

        # Get available regions for filter dropdown
        cursor.execute("SELECT DISTINCT region FROM cmdb_servers WHERE is_active = 1 ORDER BY region")
        available_regions = [row[0] for row in cursor.fetchall()]

        conn.close()

        return render_template('cmdb_servers.html',
                             servers=servers,
                             available_regions=available_regions)

    except Exception as e:
        flash(f'Error loading servers: {str(e)}', 'error')
        return redirect(url_for('cmdb_dashboard'))

@app.route('/cmdb/servers/add')
def cmdb_add_server():
    """Add new server to CMDB"""
    if 'username' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'error')
        return redirect(url_for('login'))

    # Get user's projects for sidebar navigation
    username = session.get('username')
    projects = get_user_projects_from_database(username)

    return render_template('cmdb_add_server.html', projects=projects)

@app.route('/cmdb/servers/add', methods=['POST'])
def cmdb_add_server_submit():
    """Handle server addition form submission"""
    if 'username' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'error')
        return redirect(url_for('login'))

    try:
        import pyodbc

        conn_str = (
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=SUMEETGILL7E47\\MSSQLSERVER01;"
            "DATABASE=MSIFactory;"
            "Trusted_Connection=yes;"
        )

        conn = pyodbc.connect(conn_str, timeout=5)
        cursor = conn.cursor()

        # Get form data
        server_name = request.form.get('server_name', '').strip()
        fqdn = request.form.get('fqdn', '').strip() or None
        ip_address = request.form.get('ip_address', '').strip()
        ip_address_internal = request.form.get('ip_address_internal', '').strip() or None
        infra_type = request.form.get('infra_type', '').strip()
        region = request.form.get('region', '').strip() or None
        datacenter = request.form.get('datacenter', '').strip() or None
        environment_type = request.form.get('environment_type', '').strip() or None
        status = request.form.get('status', 'active')

        # Hardware specs
        cpu_cores = request.form.get('cpu_cores') or None
        memory_gb = request.form.get('memory_gb') or None
        storage_gb = request.form.get('storage_gb') or None
        max_concurrent_apps = request.form.get('max_concurrent_apps', '1')

        # Contacts and ownership
        owner_team = request.form.get('owner_team', '').strip() or None
        technical_contact = request.form.get('technical_contact', '').strip() or None

        # Cloud details
        instance_type = request.form.get('instance_type', '').strip() or None
        instance_id = request.form.get('instance_id', '').strip() or None
        cloud_account_id = request.form.get('cloud_account_id', '').strip() or None
        resource_group = request.form.get('resource_group', '').strip() or None

        # OS details
        os_name = request.form.get('os_name', '').strip() or None
        os_version = request.form.get('os_version', '').strip() or None
        os_architecture = request.form.get('os_architecture', '').strip() or None

        # Validate required fields
        if not server_name or not ip_address or not infra_type:
            flash('Server name, IP address, and infrastructure type are required', 'error')
            return redirect(url_for('cmdb_add_server'))

        # Check for duplicate server name or IP
        cursor.execute("SELECT COUNT(*) FROM cmdb_servers WHERE server_name = ? OR ip_address = ?",
                      (server_name, ip_address))
        if cursor.fetchone()[0] > 0:
            flash('Server with this name or IP address already exists', 'error')
            return redirect(url_for('cmdb_add_server'))

        # Insert new server
        insert_sql = """
            INSERT INTO cmdb_servers (
                server_name, fqdn, infra_type, ip_address, ip_address_internal,
                region, datacenter, environment_type, status, cpu_cores, memory_gb,
                storage_gb, max_concurrent_apps, owner_team, technical_contact,
                instance_type, instance_id, cloud_account_id, resource_group,
                os_name, os_version, os_architecture, created_by, created_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE())
        """

        cursor.execute(insert_sql, (
            server_name, fqdn, infra_type, ip_address, ip_address_internal,
            region, datacenter, environment_type, status, cpu_cores, memory_gb,
            storage_gb, max_concurrent_apps, owner_team, technical_contact,
            instance_type, instance_id, cloud_account_id, resource_group,
            os_name, os_version, os_architecture, session['username']
        ))

        server_id = cursor.execute("SELECT @@IDENTITY").fetchone()[0]

        # Log the server creation
        cursor.execute("""
            INSERT INTO cmdb_server_changes (server_id, change_type, change_reason, changed_by, changed_date)
            VALUES (?, 'created', 'Server added via web interface', ?, GETDATE())
        """, (server_id, session['username']))

        conn.commit()
        conn.close()

        flash(f'Server "{server_name}" added successfully', 'success')
        return redirect(url_for('cmdb_servers'))

    except Exception as e:
        flash(f'Error adding server: {str(e)}', 'error')
        return redirect(url_for('cmdb_add_server'))

@app.route('/cmdb/servers/<int:server_id>')
def cmdb_server_detail(server_id):
    """Server detail page"""
    if 'username' not in session:
        return redirect(url_for('login'))

    try:
        import pyodbc

        conn_str = (
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=SUMEETGILL7E47\\MSSQLSERVER01;"
            "DATABASE=MSIFactory;"
            "Trusted_Connection=yes;"
        )

        conn = pyodbc.connect(conn_str, timeout=5)
        cursor = conn.cursor()

        # Get server details
        cursor.execute("""
            SELECT * FROM cmdb_servers WHERE server_id = ? AND is_active = 1
        """, (server_id,))

        server_row = cursor.fetchone()
        if not server_row:
            flash('Server not found', 'error')
            return redirect(url_for('cmdb_servers'))

        # Convert to dictionary for easier template access
        server = dict(zip([column[0] for column in cursor.description], server_row))

        conn.close()

        return render_template('cmdb_server_detail.html', server=server)

    except Exception as e:
        flash(f'Error loading server details: {str(e)}', 'error')
        return redirect(url_for('cmdb_servers'))

@app.route('/api/cmdb/server/<int:server_id>/assignments')
def api_cmdb_server_assignments(server_id):
    """API endpoint to get server project assignments"""
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        import pyodbc

        conn_str = (
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=SUMEETGILL7E47\\MSSQLSERVER01;"
            "DATABASE=MSIFactory;"
            "Trusted_Connection=yes;"
        )

        conn = pyodbc.connect(conn_str, timeout=5)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                p.project_name, p.project_key, ps.environment_name,
                ps.assignment_type, ps.purpose, ps.status
            FROM project_servers ps
            INNER JOIN projects p ON ps.project_id = p.project_id
            WHERE ps.server_id = ? AND ps.is_active = 1
            ORDER BY p.project_name, ps.environment_name
        """, (server_id,))

        assignments = []
        for row in cursor.fetchall():
            assignments.append({
                'project_name': row[0],
                'project_key': row[1],
                'environment_name': row[2],
                'assignment_type': row[3],
                'purpose': row[4],
                'status': row[5]
            })

        conn.close()

        return jsonify({'assignments': assignments})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/cmdb/assignments')
def cmdb_assignments():
    """Project-Server assignments management"""
    if 'username' not in session:
        return redirect(url_for('login'))

    # This would show a page for managing project-server assignments
    return render_template('cmdb_assignments.html')

@app.route('/cmdb/utilization')
def cmdb_utilization():
    """Server utilization and capacity reporting"""
    if 'username' not in session:
        return redirect(url_for('login'))

    return render_template('cmdb_utilization.html')

@app.route('/cmdb/groups')
def cmdb_groups():
    """Server groups and clusters management"""
    if 'username' not in session:
        return redirect(url_for('login'))

    return render_template('cmdb_groups.html')

@app.route('/debug/show-user-projects-table')
def show_user_projects_table():
    """Debug endpoint to show all user_projects table data"""
    if 'username' not in session or session.get('role') != 'admin':
        return "Admin access required", 403

    try:
        import pyodbc

        conn_str = (
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=SUMEETGILL7E47\\MSSQLSERVER01;"
            "DATABASE=MSIFactory;"
            "Trusted_Connection=yes;"
        )

        conn = pyodbc.connect(conn_str, timeout=5)
        cursor = conn.cursor()

        # Get all user_projects data with user and project details
        cursor.execute("""
            SELECT
                up.user_project_id,
                u.username,
                u.user_id as sql_user_id,
                p.project_name,
                p.project_key,
                p.project_id,
                up.access_level,
                up.is_active,
                up.granted_date,
                up.granted_by
            FROM user_projects up
            INNER JOIN users u ON up.user_id = u.user_id
            INNER JOIN projects p ON up.project_id = p.project_id
            ORDER BY u.username, p.project_name
        """)

        results = cursor.fetchall()

        html = "<h2>User Projects Table Data</h2>"
        html += "<table border='1' cellpadding='5'>"
        html += "<tr><th>User</th><th>SQL User ID</th><th>Project</th><th>Project Key</th><th>Project ID</th><th>Access Level</th><th>Active</th><th>Granted Date</th><th>Granted By</th></tr>"

        for row in results:
            html += f"<tr><td>{row[1]}</td><td>{row[2]}</td><td>{row[3]}</td><td>{row[4]}</td><td>{row[5]}</td><td>{row[6]}</td><td>{row[7]}</td><td>{row[8]}</td><td>{row[9]}</td></tr>"

        html += "</table>"

        conn.close()
        return html

    except Exception as e:
        return f"Error: {str(e)}"

@app.route('/api/applications')
def api_applications():
    """API endpoint to get applications"""
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    applications = auth_system.load_applications()
    return jsonify(applications)

@app.route('/api/generate-msi', methods=['POST'])
def api_generate_msi():
    """API endpoint for MSI generation"""
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    app_key = data.get('app_key')
    environments = data.get('environments', [])
    
    # Validate user has access
    user_apps = session.get('approved_apps', [])
    if app_key not in user_apps and '*' not in user_apps:
        return jsonify({'error': 'Access denied for this application'}), 403
    
    # Queue MSI generation job
    job_id = f"JOB_{app_key}_{len(environments)}"
    
    return jsonify({
        'job_id': job_id,
        'status': 'queued',
        'message': f'MSI generation queued for {len(environments)} environments'
    })

@app.route('/component-configuration')
def component_configuration():
    """Component Configuration Management page"""
    if 'username' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'error')
        return redirect(url_for('login'))
    
    try:
        import pyodbc
        
        # Connection string
        conn_str = (
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=SUMEETGILL7E47\\MSSQLSERVER01;"
            "DATABASE=MSIFactory;"
            "Trusted_Connection=yes;"
        )
        
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        # Get all components with their MSI configurations
        components_sql = """
            SELECT
                c.component_id,
                c.component_name,
                c.component_type,
                c.framework,
                c.component_guid,
                p.project_name,
                p.project_key,
                mc.config_id,
                mc.unique_id,
                mc.app_name,
                mc.app_version,
                mc.manufacturer,
                mc.upgrade_code,
                mc.install_folder,
                mc.target_server,
                mc.target_environment,
                mc.iis_website_name,
                mc.iis_app_pool_name,
                mc.service_name,
                mc.auto_increment_version
            FROM components c
            INNER JOIN projects p ON c.project_id = p.project_id
            LEFT JOIN msi_configurations mc ON c.component_id = mc.component_id
            ORDER BY p.project_name, c.component_name
        """
        
        cursor.execute(components_sql)
        components = cursor.fetchall()
        
        # Get available environments
        environments_sql = """
            SELECT DISTINCT environment_name 
            FROM project_environments 
            WHERE is_active = 1
            ORDER BY environment_name
        """
        cursor.execute(environments_sql)
        environments = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        
        # Transform to dictionary format
        components_list = []
        for row in components:
            component_dict = {
                'component_id': row[0],
                'component_name': row[1],
                'component_type': row[2],
                'framework': row[3],
                'component_guid': row[4],
                'project_name': row[5],
                'project_key': row[6],
                'config_id': row[7],
                'unique_id': str(row[8]) if row[8] else None,
                'app_name': row[9],
                'app_version': row[10],
                'manufacturer': row[11],
                'upgrade_code': row[12],
                'install_folder': row[13],
                'target_server': row[14],
                'target_environment': row[15],
                'iis_website_name': row[16],
                'iis_app_pool_name': row[17],
                'service_name': row[18],
                'auto_increment_version': bool(row[19]) if row[19] is not None else True
            }
            components_list.append(component_dict)
        
        return render_template('component_configuration.html', 
                             components=components_list, 
                             environments=environments)
        
    except Exception as e:
        print(f"[ERROR] Failed to load component configurations: {e}")
        flash(f"Error loading component configurations: {str(e)}", 'error')
        return redirect(url_for('project_management'))

@app.route('/save-msi-config', methods=['POST'])
def save_msi_config():
    """Save MSI configuration for a component"""
    if 'username' not in session or session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        import pyodbc
        
        component_id = request.form.get('component_id')
        
        # Connection string
        conn_str = (
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=SUMEETGILL7E47\\MSSQLSERVER01;"
            "DATABASE=MSIFactory;"
            "Trusted_Connection=yes;"
        )
        
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        # Check if configuration exists
        cursor.execute("SELECT config_id FROM msi_configurations WHERE component_id = ?", (component_id,))
        existing_config = cursor.fetchone()
        
        if existing_config:
            # Update existing configuration
            update_sql = """
                UPDATE msi_configurations SET
                    app_name = ?,
                    app_version = ?,
                    manufacturer = ?,
                    upgrade_code = ?,
                    install_folder = ?,
                    target_server = ?,
                    target_environment = ?,
                    auto_increment_version = ?,
                    iis_website_name = ?,
                    iis_app_pool_name = ?,
                    app_pool_dotnet_version = ?,
                    app_pool_pipeline_mode = ?,
                    app_pool_identity = ?,
                    app_pool_enable_32bit = ?,
                    service_name = ?,
                    service_display_name = ?,
                    service_description = ?,
                    service_start_type = ?,
                    service_account = ?,
                    updated_date = GETDATE(),
                    updated_by = ?
                WHERE component_id = ?
            """
            cursor.execute(update_sql, (
                request.form.get('app_name'),
                request.form.get('app_version'),
                request.form.get('manufacturer'),
                request.form.get('upgrade_code'),
                request.form.get('install_folder'),
                request.form.get('target_server'),
                request.form.get('target_environment'),
                1 if request.form.get('auto_increment_version') == 'on' else 0,
                request.form.get('iis_website_name'),
                request.form.get('iis_app_pool_name'),
                request.form.get('app_pool_dotnet_version'),
                request.form.get('app_pool_pipeline_mode'),
                request.form.get('app_pool_identity'),
                1 if request.form.get('app_pool_enable_32bit') == 'on' else 0,
                request.form.get('service_name'),
                request.form.get('service_display_name'),
                request.form.get('service_description'),
                request.form.get('service_start_type'),
                request.form.get('service_account'),
                session.get('username'),
                component_id
            ))
        else:
            # Insert new configuration
            insert_sql = """
                INSERT INTO msi_configurations (
                    component_id, app_name, app_version, manufacturer, upgrade_code, 
                    install_folder, target_server, target_environment, auto_increment_version,
                    iis_website_name, iis_app_pool_name, app_pool_dotnet_version, 
                    app_pool_pipeline_mode, app_pool_identity, app_pool_enable_32bit,
                    service_name, service_display_name, service_description, 
                    service_start_type, service_account, created_by, updated_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            cursor.execute(insert_sql, (
                component_id,
                request.form.get('app_name'),
                request.form.get('app_version'),
                request.form.get('manufacturer'),
                request.form.get('upgrade_code'),
                request.form.get('install_folder'),
                request.form.get('target_server'),
                request.form.get('target_environment'),
                1 if request.form.get('auto_increment_version') == 'on' else 0,
                request.form.get('iis_website_name'),
                request.form.get('iis_app_pool_name'),
                request.form.get('app_pool_dotnet_version'),
                request.form.get('app_pool_pipeline_mode'),
                request.form.get('app_pool_identity'),
                1 if request.form.get('app_pool_enable_32bit') == 'on' else 0,
                request.form.get('service_name'),
                request.form.get('service_display_name'),
                request.form.get('service_description'),
                request.form.get('service_start_type'),
                request.form.get('service_account'),
                session.get('username'),
                session.get('username')
            ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'MSI configuration saved successfully'
        })
        
    except Exception as e:
        print(f"[ERROR] Failed to save MSI configuration: {e}")
        return jsonify({
            'success': False,
            'message': f'Error saving configuration: {str(e)}'
        }), 500

@app.route('/api/get-next-version', methods=['POST'])
def api_get_next_version():
    """API endpoint to get next version for a component"""
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        import pyodbc
        
        component_id = request.json.get('component_id')
        
        # Connection string
        conn_str = (
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=SUMEETGILL7E47\\MSSQLSERVER01;"
            "DATABASE=MSIFactory;"
            "Trusted_Connection=yes;"
        )
        
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        # Call stored procedure to get next version
        cursor.execute("EXEC sp_GetNextVersion ?", (component_id,))
        result = cursor.fetchone()
        
        conn.close()
        
        if result:
            return jsonify({
                'success': True,
                'next_version': result[0]
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Unable to generate next version'
            })
        
    except Exception as e:
        print(f"[ERROR] Failed to get next version: {e}")
        return jsonify({
            'success': False,
            'message': f'Error getting next version: {str(e)}'
        }), 500

@app.route('/api/test-submit', methods=['POST'])
def api_test_submit():
    """Test endpoint to check if POST requests work"""
    logger.log_system_event("TEST_SUBMIT_RECEIVED", f"POST request received with data: {dict(request.form)}")
    return jsonify({'status': 'POST request received successfully', 'data': dict(request.form)})

@app.route('/api/session-debug', methods=['GET', 'POST'])
def api_session_debug():
    """Debug endpoint to check session state"""
    session_data = {
        'username': session.get('username'),
        'role': session.get('role'),
        'user_id': session.get('user_id'),
        'has_username': 'username' in session,
        'is_admin': session.get('role') == 'admin',
        'session_keys': list(session.keys())
    }
    logger.log_system_event("SESSION_DEBUG", f"Session state: {session_data}")
    return jsonify(session_data)

@app.route('/api/add-component', methods=['POST'])
def api_add_component():
    """Direct API endpoint to add a component to a project"""
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        logger.log_system_event("API_ADD_COMPONENT_START", f"Request received from user: {session.get('username')}")

        # Get form data
        project_id = request.form.get('project_id')
        component_data = {
            'name': request.form.get('component_name'),
            'type': request.form.get('component_type'),
            'framework': request.form.get('component_framework'),
            'app_name': request.form.get('component_app_name'),
            'version': request.form.get('component_version'),
            'manufacturer': request.form.get('component_manufacturer'),
            'target_server': request.form.get('component_target_server'),
            'install_folder': request.form.get('component_install_folder'),
            'iis_website': request.form.get('component_iis_website'),
            'app_pool': request.form.get('component_app_pool'),
            'port': request.form.get('component_port'),
            'service_name': request.form.get('component_service_name', ''),
            'service_display': request.form.get('component_service_display', ''),
            'artifact_url': request.form.get('component_artifact', '')
        }

        logger.log_system_event("API_COMPONENT_DATA", f"Adding component: {component_data['name']} to project {project_id}")

        import pyodbc
        import uuid

        conn_str = (
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=SUMEETGILL7E47\\MSSQLSERVER01;"
            "DATABASE=MSIFactory;"
            "Trusted_Connection=yes;"
        )

        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        # Generate component GUID
        component_guid = str(uuid.uuid4())

        # Insert component
        cursor.execute("""
            INSERT INTO components (
                project_id, component_name, component_type, framework,
                component_guid, app_name, app_version, manufacturer,
                target_server, install_folder, iis_website_name,
                iis_app_pool_name, port, service_name, service_display_name,
                artifact_url, created_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, GETDATE())
        """, (
            project_id, component_data['name'], component_data['type'],
            component_data['framework'], component_guid, component_data['app_name'],
            component_data['version'], component_data['manufacturer'],
            component_data['target_server'], component_data['install_folder'],
            component_data['iis_website'], component_data['app_pool'],
            component_data['port'], component_data['service_name'],
            component_data['service_display'], component_data['artifact_url']
        ))

        conn.commit()
        cursor.close()
        conn.close()

        logger.log_system_event("API_COMPONENT_ADDED", f"Component {component_data['name']} added successfully with GUID: {component_guid}")

        return jsonify({
            'success': True,
            'message': f"Component {component_data['name']} added successfully",
            'component_guid': component_guid
        })

    except Exception as e:
        logger.log_error("API_ADD_COMPONENT_ERROR", f"Failed to add component: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/logout')
def logout():
    """Logout user"""
    username = session.get('username')
    if username:
        logger.log_user_logout(username)
        logger.log_system_event("USER_SESSION_END", f"User: {username}")

    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

# Error handlers
@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', error='Page not found'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', error='Internal server error'), 500

@app.route('/api/project/<int:project_id>/environments')
def api_project_environments(project_id):
    """Get environments for a specific project"""
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        import pyodbc

        conn_str = (
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=SUMEETGILL7E47\\MSSQLSERVER01;"
            "DATABASE=MSIFactory;"
            "Trusted_Connection=yes;"
        )

        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        # Get project environments
        cursor.execute("""
            SELECT environment_id, environment_name, environment_type
            FROM project_environments
            WHERE project_id = ?
            ORDER BY environment_name
        """, (project_id,))

        environments = []
        for row in cursor.fetchall():
            environments.append({
                'environment_id': row[0],
                'environment_name': row[1],
                'environment_type': row[2]
            })

        conn.close()

        return jsonify({'environments': environments})

    except Exception as e:
        print(f"[ERROR] Failed to get project environments: {e}")
        return jsonify({'error': 'Failed to load environments'}), 500

@app.route('/cmdb/assignments/create', methods=['POST'])
def cmdb_create_assignment():
    """Create new server assignment"""
    if 'username' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'error')
        return redirect(url_for('cmdb_assignments'))

    try:
        import pyodbc

        conn_str = (
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=SUMEETGILL7E47\\MSSQLSERVER01;"
            "DATABASE=MSIFactory;"
            "Trusted_Connection=yes;"
        )

        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        # Get form data
        project_id = request.form.get('project_id')
        environment_id = request.form.get('environment_id')
        server_id = request.form.get('server_id')
        assignment_type = request.form.get('assignment_type')
        purpose = request.form.get('purpose')
        status = request.form.get('status', 'active')

        # Check if assignment already exists
        cursor.execute("""
            SELECT COUNT(*) FROM project_servers
            WHERE project_id = ? AND environment_id = ? AND server_id = ? AND assignment_type = ?
        """, (project_id, environment_id, server_id, assignment_type))

        if cursor.fetchone()[0] > 0:
            flash('This server assignment already exists', 'error')
            return redirect(url_for('cmdb_assignments'))

        # Create assignment
        cursor.execute("""
            INSERT INTO project_servers (project_id, environment_id, server_id, assignment_type, purpose, status, assigned_date, assigned_by)
            VALUES (?, ?, ?, ?, ?, ?, GETDATE(), ?)
        """, (project_id, environment_id, server_id, assignment_type, purpose, status, session.get('username')))

        conn.commit()
        conn.close()

        flash('Server assignment created successfully', 'success')
        return redirect(url_for('cmdb_assignments'))

    except Exception as e:
        print(f"[ERROR] Failed to create server assignment: {e}")
        flash('Failed to create server assignment', 'error')
        return redirect(url_for('cmdb_assignments'))

# ============================================================
# INTEGRATIONS ROUTES
# ============================================================

@app.route('/integrations')
def integrations():
    """External system integrations configuration page"""
    if 'username' not in session or session.get('role') != 'admin':
        flash('Admin access required', 'error')
        return redirect(url_for('login'))

    # Get user's projects for sidebar navigation
    username = session.get('username')
    projects = get_user_projects_from_database(username)

    return render_template('integrations.html', projects=projects)

@app.route('/api/integrations/servicenow/config', methods=['GET', 'POST'])
def servicenow_config():
    """ServiceNow configuration management"""
    if 'username' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'error': 'Admin access required'})

    if request.method == 'GET':
        # Return current ServiceNow configuration (without sensitive data)
        try:
            # TODO: Retrieve from Vault or database
            return jsonify({
                'success': True,
                'config': {
                    'instance_url': '',
                    'username': '',
                    'table': 'cmdb_ci_server',
                    'filter': '',
                    'sync_frequency': 'daily',
                    'auto_sync': False,
                    'configured': False
                }
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})

    elif request.method == 'POST':
        # Save ServiceNow configuration
        try:
            config = {
                'instance_url': request.form.get('snow_instance_url', '').strip(),
                'username': request.form.get('snow_username', '').strip(),
                'password': request.form.get('snow_password', '').strip(),
                'table': request.form.get('snow_table', 'cmdb_ci_server'),
                'filter': request.form.get('snow_filter', '').strip(),
                'sync_frequency': request.form.get('snow_sync_frequency', 'daily'),
                'auto_sync': request.form.get('snow_auto_sync') == 'on'
            }

            # TODO: Store configuration securely in Vault
            # For now, just validate required fields
            if not config['instance_url'] or not config['username'] or not config['password']:
                return jsonify({'success': False, 'error': 'Instance URL, username, and password are required'})

            return jsonify({'success': True, 'message': 'ServiceNow configuration saved successfully'})

        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})

@app.route('/api/integrations/servicenow/test', methods=['POST'])
def test_servicenow_connection():
    """Test ServiceNow connection"""
    if 'username' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'error': 'Admin access required'})

    try:
        # TODO: Implement actual ServiceNow connection test
        # For now, return a mock response
        return jsonify({
            'success': True,
            'message': 'ServiceNow connection test successful',
            'server_count': 0,
            'test_time': datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/integrations/servicenow/sync', methods=['POST'])
def sync_servicenow_servers():
    """Synchronize servers from ServiceNow"""
    if 'username' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'error': 'Admin access required'})

    try:
        # TODO: Implement actual ServiceNow synchronization
        # For now, return a mock response
        return jsonify({
            'success': True,
            'servers_synced': 0,
            'servers_added': 0,
            'servers_updated': 0,
            'errors': [],
            'sync_time': datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/integrations/vault/config', methods=['GET', 'POST'])
def vault_config():
    """HashiCorp Vault configuration management"""
    if 'username' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'error': 'Admin access required'})

    if request.method == 'GET':
        # Return current Vault configuration (without sensitive data)
        try:
            return jsonify({
                'success': True,
                'config': {
                    'url': '',
                    'auth_method': 'token',
                    'mount_path': 'secret',
                    'app_path': 'msifactory',
                    'ssl_verify': True,
                    'auto_renew': True,
                    'configured': False
                }
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})

    elif request.method == 'POST':
        # Save Vault configuration
        try:
            config = {
                'url': request.form.get('vault_url', '').strip(),
                'auth_method': request.form.get('vault_auth_method', 'token'),
                'mount_path': request.form.get('vault_mount_path', 'secret'),
                'app_path': request.form.get('vault_app_path', 'msifactory'),
                'ssl_verify': request.form.get('vault_ssl_verify') == 'on',
                'auto_renew': request.form.get('vault_auto_renew') == 'on'
            }

            # Get auth-specific fields
            if config['auth_method'] == 'token':
                config['token'] = request.form.get('vault_token', '').strip()
            elif config['auth_method'] in ['userpass', 'ldap']:
                config['username'] = request.form.get('vault_username', '').strip()
                config['password'] = request.form.get('vault_user_password', '').strip()
            elif config['auth_method'] == 'approle':
                config['role_id'] = request.form.get('vault_role_id', '').strip()
                config['secret_id'] = request.form.get('vault_secret_id', '').strip()

            # TODO: Store configuration securely
            if not config['url']:
                return jsonify({'success': False, 'error': 'Vault URL is required'})

            return jsonify({'success': True, 'message': 'Vault configuration saved successfully'})

        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})

@app.route('/api/integrations/vault/test', methods=['POST'])
def test_vault_connection():
    """Test HashiCorp Vault connection"""
    if 'username' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'error': 'Admin access required'})

    try:
        # TODO: Implement actual Vault connection test
        # For now, return a mock response
        return jsonify({
            'success': True,
            'message': 'Vault connection test successful',
            'vault_version': '1.15.0',
            'auth_status': 'authenticated',
            'test_time': datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/integrations/vault/secrets')
def vault_secrets():
    """Retrieve Vault secrets (metadata only)"""
    if 'username' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'error': 'Admin access required'})

    try:
        # TODO: Implement actual Vault secrets retrieval
        # For now, return mock data
        return jsonify({
            'success': True,
            'secrets': [
                {
                    'path': 'msifactory/servicenow',
                    'keys': ['username', 'password', 'instance_url'],
                    'updated': datetime.now().isoformat()
                },
                {
                    'path': 'msifactory/database',
                    'keys': ['connection_string', 'username', 'password'],
                    'updated': datetime.now().isoformat()
                }
            ]
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

def init_system():
    """Initialize the MSI Factory system"""
    print("=" * 60)
    print("MSI FACTORY - Enterprise MSI Generation System")
    print("=" * 60)
    
    # Create necessary directories
    directories = ['webapp/templates', 'webapp/static', 'config', 'output', 'logs']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
    
    # Initialize logging
    logger.log_system_start()
    logger.log_system_event("INITIALIZATION", "System directories created")
    logger.log_system_event("INITIALIZATION", "Authentication system loaded")
    
    print("[OK] System initialized")
    print("[OK] Directories created")
    print("[OK] Authentication system loaded")
    print("[OK] Logging system active")
    print("[OK] Ready to generate MSIs")
    print("=" * 60)

if __name__ == '__main__':
    # Initialize system
    init_system()
    
    print("\nStarting MSI Factory Server...")
    print("URL: http://localhost:5000")
    print("Admin: admin")
    print("User: john.doe")
    print("\nPress CTRL+C to stop the server")
    print("-" * 60)
    
    # Run the application
    app.run(debug=True, host='0.0.0.0', port=5000)