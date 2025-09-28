"""
Clean SQL-only functions to replace auth_system dependent functions
"""

import pyodbc
from logger import log_info, log_error

# Database connection configuration
DB_CONNECTION_STRING = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=SUMEETGILL7E47\\MSSQLSERVER01;"
    "DATABASE=MSIFactory;"
    "Trusted_Connection=yes;"
    "Connection Timeout=5;"
)

def get_db_connection(timeout=5):
    """Create and return database connection"""
    return pyodbc.connect(DB_CONNECTION_STRING, timeout=timeout)

def get_user_projects_from_database_sql_only(username):
    """Get user's projects directly from SQL database - no JSON dependency"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get user info and role from SQL database
        cursor.execute("SELECT user_id, role FROM users WHERE username = ? AND is_active = 1", (username,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            log_info(f"DATABASE: User {username} not found in SQL database")
            return []

        user_id, role = row[0], row[1]
        log_info(f"DATABASE: User {username} found - ID: {user_id}, Role: {role}")

        # Get projects based on role
        if role == 'admin':
            log_info(f"DATABASE: User {username} is admin, getting all projects")
            cursor.execute("""
                SELECT project_id, project_name, project_key, description, project_type,
                       owner_team, status, color_primary, color_secondary, created_date, created_by
                FROM projects
                WHERE is_active = 1
                ORDER BY created_date DESC
            """)
        else:
            log_info(f"DATABASE: User {username} is regular user, getting assigned projects")
            cursor.execute("""
                SELECT p.project_id, p.project_name, p.project_key, p.description, p.project_type,
                       p.owner_team, p.status, p.color_primary, p.color_secondary, p.created_date, p.created_by
                FROM projects p
                INNER JOIN user_projects up ON p.project_id = up.project_id
                WHERE up.user_id = ? AND up.is_active = 1 AND p.is_active = 1
                ORDER BY p.created_date DESC
            """, (user_id,))

        # Process results
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
        log_error(f"DATABASE: Error getting user projects: {str(e)}")
        return []

def update_user_projects_in_database_sql_only(username, project_keys, all_projects_access):
    """Update user's project access in SQL database - no JSON dependency"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get user_id from SQL
        cursor.execute("SELECT user_id FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return False, f"User {username} not found in SQL database"

        user_id = row[0]
        log_info(f"DATABASE: Updating projects for user {username} (ID: {user_id})")

        # Remove existing project assignments
        cursor.execute("DELETE FROM user_projects WHERE user_id = ?", (user_id,))
        log_info(f"DATABASE: Removed existing project assignments for user {username}")

        # Add new project assignments (skip if admin with all access)
        if not all_projects_access and project_keys:
            for project_key in project_keys:
                # Get project_id for this project_key
                cursor.execute("SELECT project_id FROM projects WHERE project_key = ?", (project_key,))
                project_row = cursor.fetchone()

                if project_row:
                    project_id = project_row[0]
                    cursor.execute("""
                        INSERT INTO user_projects (user_id, project_id, access_level, granted_date, granted_by, is_active)
                        VALUES (?, ?, 'admin', GETDATE(), 'system', 1)
                    """, (user_id, project_id))
                    log_info(f"DATABASE: Added project assignment {project_key} for user {username}")

        conn.commit()
        conn.close()

        log_info(f"DATABASE: Successfully updated project assignments for user {username}")
        return True, "Project assignments updated successfully"

    except Exception as e:
        error_msg = f"Failed to update user projects: {str(e)}"
        log_error(f"DATABASE: {error_msg}")
        return False, error_msg

def get_user_project_details_from_database_sql_only(username):
    """Get detailed user project information from SQL database - no JSON dependency"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get user info from SQL
        cursor.execute("SELECT user_id, role FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return None

        user_id, role = row[0], row[1]

        # Get project assignments
        if role == 'admin':
            # Admin has access to all projects
            cursor.execute("SELECT project_key FROM projects WHERE is_active = 1")
            project_keys = [row[0] for row in cursor.fetchall()]
            all_projects_access = True
        else:
            cursor.execute("""
                SELECT p.project_key
                FROM projects p
                INNER JOIN user_projects up ON p.project_id = up.project_id
                WHERE up.user_id = ? AND up.is_active = 1 AND p.is_active = 1
            """, (user_id,))
            project_keys = [row[0] for row in cursor.fetchall()]
            all_projects_access = False

        conn.close()

        return {
            'username': username,
            'projects': project_keys,
            'all_projects': all_projects_access,
            'approved_apps': project_keys,
            'all_projects_access': all_projects_access
        }

    except Exception as e:
        log_error(f"DATABASE: Error getting user project details: {str(e)}")
        return None