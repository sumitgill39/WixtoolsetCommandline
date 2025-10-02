"""
Database Operations Module
Handles all database interactions for the MSI Factory application
"""

import pyodbc
from logger import get_logger, log_info, log_error

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

def simple_delete_project_from_database(project_id):
    """Simple project deletion without complex transaction handling"""
    log_info(f"DATABASE: Attempting simple database deletion for project {project_id}")

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Delete dependent records first to avoid foreign key constraints
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
                        cursor.execute("SELECT TOP 5 * FROM msi_configurations")
                        sample_data = cursor.fetchall()
                        for i, row in enumerate(sample_data):
                            log_info(f"DATABASE: Sample record {i+1}: {dict(zip(columns, row))}")

                        if 'component_id' in columns:
                            cursor.execute("DELETE FROM msi_configurations WHERE component_id = ?", (project_id,))
                            targeted_delete = cursor.rowcount
                            log_info(f"DATABASE: Targeted delete of component_id={project_id}: {targeted_delete} rows")

                            if targeted_delete == 0:
                                log_info(f"DATABASE: No targeted deletion worked, checking constraint direction")
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
        log_info(f"pyodbc imported successfully")
        log_info(f"Attempting database connection...")

        conn = get_db_connection(timeout=10)
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

def get_user_projects_from_database(username, auth_system=None):
    """Get user's projects directly from SQL database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get user info and role from SQL database
        cursor.execute("SELECT user_id, role FROM users WHERE username = ? AND is_active = 1", (username,))
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
                cursor.execute("""
                    SELECT project_id, project_name, project_key, description, project_type,
                           owner_team, status, color_primary, color_secondary, created_date, created_by
                    FROM projects
                    WHERE is_active = 1
                    ORDER BY created_date DESC
                """)
            else:
                log_info(f"DATABASE: User {username} is regular user, checking SQL user_projects table")
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
                        if user_apps:
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
        conn = get_db_connection()
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
        conn = get_db_connection()
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

def update_user_projects_in_database(username, project_keys, all_projects_access, auth_system):
    """Update user's project access in SQL database"""
    try:
        # Get user info first
        user = auth_system.check_user_login(username)
        if not user:
            return False, "User not found"

        conn = get_db_connection()
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
            # User has access to all projects - we don't need individual entries
            log_info(f"DATABASE: User {username} granted all projects access (no individual entries needed)")
        else:
            # Add new project assignments
            for project_key in project_keys:
                cursor.execute("SELECT project_id FROM projects WHERE project_key = ?", (project_key,))
                project_row = cursor.fetchone()
                if project_row:
                    project_id = project_row[0]
                    cursor.execute("""
                        INSERT INTO user_projects (user_id, project_id, access_level, granted_date, granted_by, is_active)
                        VALUES (?, ?, 'admin', GETDATE(), 'system', 1)
                    """, (user_id, project_id))
                    log_info(f"DATABASE: Added project assignment for user {username} to project {project_key}")

        conn.commit()
        conn.close()

        # Also update JSON auth system for backward compatibility and UI display
        auth_system.update_user_projects(username, project_keys, all_projects_access)
        log_info(f"DATABASE: Successfully updated project assignments for user {username}")
        log_info(f"JSON: Synchronized project assignments to JSON file for user {username}")

        return True, "Project assignments updated successfully"

    except Exception as e:
        error_msg = f"Failed to update user projects: {str(e)}"
        log_error(f"DATABASE: {error_msg}")
        return False, error_msg

def get_user_project_details_from_database(username, auth_system):
    """Get detailed user project information from SQL database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get user info first
        user = auth_system.check_user_login(username)
        if not user:
            conn.close()
            return None

        # Get user_id from users table
        cursor.execute("SELECT user_id, role FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()

        if row:
            user_id = row[0]
            db_role = row[1]

            # Get project assignments
            if db_role == 'admin':
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
                'project_keys': project_keys,
                'all_projects_access': all_projects_access
            }
        else:
            conn.close()
            # Fall back to JSON data
            return {
                'username': username,
                'project_keys': user.get('approved_apps', []),
                'all_projects_access': '*' in user.get('approved_apps', [])
            }

    except Exception as e:
        log_error(f"DATABASE: Error getting user project details: {str(e)}")
        return None

def get_project_by_id_from_database(project_id):
    """Get single project by ID from database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT project_id, project_name, project_key, description, project_type,
                   owner_team, status, color_primary, color_secondary, created_date, created_by, project_guid
            FROM projects
            WHERE project_id = ?
        """, (project_id,))

        row = cursor.fetchone()
        if row:
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
                'created_by': row[10] or '',
                'project_guid': row[11]
            }
            conn.close()
            return project

        conn.close()
        return None

    except Exception as e:
        log_error(f"DATABASE: Error getting project {project_id}: {str(e)}")
        return None

def get_all_components_from_database():
    """Get all components from all projects with full details"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                c.component_id, c.component_name, c.component_type, c.framework,
                c.artifact_source, c.created_date, c.created_by, c.is_enabled,
                c.component_guid, c.description, c.app_name, c.app_version,
                c.manufacturer, c.install_folder, c.iis_website_name,
                c.iis_app_pool_name, c.port, c.service_name, c.service_display_name,
                p.project_name, p.project_key, p.project_id,
                mc.config_id, mc.target_server, mc.target_environment
            FROM components c
            INNER JOIN projects p ON c.project_id = p.project_id
            LEFT JOIN msi_configurations mc ON c.component_id = mc.component_id
            ORDER BY p.project_name, c.component_name
        """)

        rows = cursor.fetchall()
        components = []

        for row in rows:
            component = {
                'component_id': row[0],
                'component_name': row[1],
                'component_type': row[2] or 'Application',
                'framework': row[3],
                'artifact_source': row[4],
                'created_date': row[5],
                'created_by': row[6],
                'is_enabled': row[7],
                'component_guid': row[8],
                'description': row[9],
                'app_name': row[10],
                'app_version': row[11],
                'manufacturer': row[12],
                'install_folder': row[13],
                'iis_website_name': row[14],
                'iis_app_pool_name': row[15],
                'port': row[16],
                'service_name': row[17],
                'service_display_name': row[18],
                'project_name': row[19],
                'project_key': row[20],
                'project_id': row[21],
                'config_id': row[22],
                'target_server': row[23],
                'target_environment': row[24]
            }
            components.append(component)

        conn.close()
        return components

    except Exception as e:
        log_error(f"DATABASE: Error getting all components: {str(e)}")
        return []

def get_component_by_id_from_database(component_id):
    """Get a single component by ID with full details"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                c.component_id, c.component_name, c.component_type, c.framework,
                c.artifact_source, c.created_date, c.created_by, c.is_enabled,
                c.component_guid, c.description, c.app_name, c.app_version,
                c.manufacturer, c.install_folder, c.iis_website_name,
                c.iis_app_pool_name, c.port, c.service_name, c.service_display_name,
                p.project_name, p.project_key, p.project_id,
                mc.config_id, mc.target_server, mc.target_environment
            FROM components c
            INNER JOIN projects p ON c.project_id = p.project_id
            LEFT JOIN msi_configurations mc ON c.component_id = mc.component_id
            WHERE c.component_id = ?
        """, (component_id,))

        row = cursor.fetchone()

        if row:
            component = {
                'component_id': row[0],
                'component_name': row[1],
                'component_type': row[2] or 'Application',
                'framework': row[3],
                'artifact_source': row[4],
                'created_date': row[5],
                'created_by': row[6],
                'is_enabled': row[7],
                'component_guid': row[8],
                'description': row[9],
                'app_name': row[10],
                'app_version': row[11],
                'manufacturer': row[12],
                'install_folder': row[13],
                'iis_website_name': row[14],
                'iis_app_pool_name': row[15],
                'port': row[16],
                'service_name': row[17],
                'service_display_name': row[18],
                'project_name': row[19],
                'project_key': row[20],
                'project_id': row[21],
                'config_id': row[22],
                'target_server': row[23],
                'target_environment': row[24]
            }
            conn.close()
            return component
        else:
            conn.close()
            return None

    except Exception as e:
        log_error(f"DATABASE: Error getting component {component_id}: {str(e)}")
        return None

def debug_user_project_access(username, auth_system):
    """Debug function to check user's project access"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get user info
        user = auth_system.check_user_login(username)

        print(f"\n=== Debug Info for User: {username} ===")
        print(f"JSON User Data: {user}")

        if not user:
            print("User not found in JSON auth system")
            conn.close()
            return

        # Check SQL user table
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        sql_user = cursor.fetchone()

        if sql_user:
            columns = [column[0] for column in cursor.description]
            user_dict = dict(zip(columns, sql_user))
            print(f"\nSQL User Record: {user_dict}")

            user_id = sql_user[0]

            # Check user_projects assignments
            cursor.execute("""
                SELECT up.*, p.project_name, p.project_key
                FROM user_projects up
                INNER JOIN projects p ON up.project_id = p.project_id
                WHERE up.user_id = ?
            """, (user_id,))

            assignments = cursor.fetchall()
            print(f"\nSQL Project Assignments ({len(assignments)} total):")
            for assignment in assignments:
                print(f"  - {assignment}")
        else:
            print("\nNo SQL user record found")

        # Show what projects user can access
        projects = get_user_projects_from_database(username, auth_system)
        print(f"\nAccessible Projects ({len(projects)} total):")
        for project in projects:
            print(f"  - {project['project_key']}: {project['project_name']}")

        conn.close()

    except Exception as e:
        print(f"Error in debug: {e}")

# SQL-based Authentication Functions (replacing JSON dependency)
def authenticate_user_sql(username, password):
    """Authenticate user against SQL database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get user from database
        cursor.execute("""
            SELECT user_id, username, password_hash, role, is_active,
                   first_name, last_name, email
            FROM users
            WHERE username = ? AND is_active = 1
        """, (username,))

        row = cursor.fetchone()
        if not row:
            conn.close()
            return None, "User not found or inactive"

        # For now, simple password check (should use hashing in production)
        stored_password = row[2] or 'password123'  # Default password if NULL
        if password != stored_password:
            conn.close()
            return None, "Invalid credentials"

        # User authenticated successfully
        user_data = {
            'user_id': row[0],
            'username': row[1],
            'role': row[3],
            'is_active': row[4],
            'first_name': row[5] or '',
            'last_name': row[6] or '',
            'email': row[7] or f"{row[1]}@company.com"
        }

        # Update last login
        cursor.execute("""
            UPDATE users
            SET last_login = GETDATE()
            WHERE user_id = ?
        """, (row[0],))
        conn.commit()

        conn.close()
        log_info(f"User {username} authenticated successfully from SQL")
        return user_data, "Login successful"

    except Exception as e:
        log_error(f"Error authenticating user from SQL: {str(e)}")
        return None, "Authentication error"

def get_user_by_username_sql(username):
    """Get user data from SQL by username"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT user_id, username, role, is_active, first_name, last_name, email
            FROM users
            WHERE username = ?
        """, (username,))

        row = cursor.fetchone()
        if not row:
            conn.close()
            return None

        user_data = {
            'user_id': row[0],
            'username': row[1],
            'role': row[2],
            'is_active': row[3],
            'first_name': row[4] or '',
            'last_name': row[5] or '',
            'email': row[6] or f"{row[1]}@company.com"
        }

        conn.close()
        return user_data

    except Exception as e:
        log_error(f"Error getting user from SQL: {str(e)}")
        return None

def toggle_user_status_sql(username):
    """Toggle user active status in SQL database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get current status
        cursor.execute("SELECT is_active FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return False, "User not found"

        new_status = not row[0]

        # Update status
        cursor.execute("""
            UPDATE users
            SET is_active = ?
            WHERE username = ?
        """, (new_status, username))

        conn.commit()
        conn.close()

        status_text = "activated" if new_status else "deactivated"
        return True, f"User {username} has been {status_text}"

    except Exception as e:
        log_error(f"Error toggling user status: {str(e)}")
        return False, "Error updating user status"

def get_all_users_with_sql_projects(auth_system=None):
    """Get all users with their project assignments directly from SQL database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get all users directly from SQL database
        cursor.execute("""
            SELECT u.user_id, u.username, u.email, u.role, u.is_active,
                   u.first_name, u.last_name, u.created_date, u.last_login
            FROM users u
            ORDER BY u.username
        """)

        all_users = []
        for row in cursor.fetchall():
            user_id = row[0]
            username = row[1]
            role = row[3]

            # Create user dictionary
            user = {
                'user_id': user_id,
                'username': username,
                'email': row[2] or f"{username}@company.com",
                'role': role,
                'is_active': row[4],
                'first_name': row[5] or '',
                'last_name': row[6] or '',
                'created_date': row[7],
                'last_login': row[8],
                'approved_apps': []
            }

            # Get project assignments from SQL
            if role == 'admin':
                # Admin has access to all projects
                user['approved_apps'] = ['*']  # Admin marker
            else:
                # Get specific project assignments
                cursor.execute("""
                    SELECT p.project_key
                    FROM projects p
                    INNER JOIN user_projects up ON p.project_id = up.project_id
                    WHERE up.user_id = ? AND up.is_active = 1 AND p.is_active = 1
                    ORDER BY p.project_key
                """, (user_id,))
                project_keys = [row[0] for row in cursor.fetchall()]
                user['approved_apps'] = project_keys

            all_users.append(user)

        conn.close()
        return all_users

    except Exception as e:
        log_error(f"DATABASE: Error getting users from SQL: {str(e)}")
        # If SQL fails and auth_system provided, fall back to JSON
        if auth_system:
            return auth_system.get_all_users()
        return []

def get_detailed_projects():
    """Get all projects with additional details including components"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # First get all projects
        cursor.execute("""
            SELECT
                p.project_id,
                p.project_name,
                p.project_key,
                p.project_guid,
                p.description,
                p.project_type,
                p.owner_team,
                p.status,
                p.created_date,
                p.created_by,
                p.color_primary,
                p.color_secondary
            FROM projects p
            WHERE (p.is_active = 1 OR p.is_active IS NULL)
            ORDER BY p.created_date DESC
        """)

        projects = []
        for row in cursor.fetchall():
            project_id = row[0]
            project = {
                'project_id': project_id,
                'project_name': row[1],
                'project_key': row[2],
                'project_guid': row[3],
                'description': row[4] or '',
                'project_type': row[5] or 'Application',
                'owner_team': row[6] or '',
                'status': row[7] or 'active',
                'created_date': row[8],
                'created_by': row[9] or '',
                'color_primary': row[10] or '#2c3e50',
                'color_secondary': row[11] or '#3498db',
                'components': []
            }

            # Get components for this project with environment and server information
            cursor.execute("""
                SELECT
                    c.component_id,
                    c.component_name,
                    c.component_type,
                    c.framework,
                    c.component_guid,
                    c.app_name,
                    c.app_version,
                    c.manufacturer,
                    c.install_folder,
                    c.is_enabled,
                    c.created_date,
                    c.service_name,
                    c.iis_website_name,
                    c.port,
                    c.target_server,
                    c.deployment_strategy
                FROM components c
                WHERE c.project_id = ?
                ORDER BY c.component_name
            """, (project_id,))

            components = []
            for comp_row in cursor.fetchall():
                component_id = comp_row[0]
                component = {
                    'component_id': component_id,
                    'name': comp_row[1],
                    'type': comp_row[2],
                    'framework': comp_row[3],
                    'guid': comp_row[4],
                    'app_name': comp_row[5],
                    'version': comp_row[6],
                    'manufacturer': comp_row[7],
                    'install_folder': comp_row[8],
                    'is_enabled': comp_row[9],
                    'created_date': comp_row[10],
                    'service_name': comp_row[11],
                    'iis_website_name': comp_row[12],
                    'port': comp_row[13],
                    'target_server': comp_row[14],
                    'deployment_strategy': comp_row[15],
                    'environments': [],
                    'servers': []
                }

                # Get component environments
                cursor.execute("""
                    SELECT
                        ce.environment_id,
                        pe.environment_name,
                        ce.artifact_url,
                        ce.deployment_path,
                        ce.is_active
                    FROM component_environments ce
                    JOIN project_environments pe ON ce.environment_id = pe.env_id
                    WHERE ce.component_id = ? AND ce.is_active = 1
                """, (component_id,))

                for env_row in cursor.fetchall():
                    environment = {
                        'environment_id': env_row[0],
                        'environment_name': env_row[1],
                        'artifact_url': env_row[2],
                        'deployment_path': env_row[3],
                        'is_active': env_row[4]
                    }
                    component['environments'].append(environment)

                # Get component servers
                cursor.execute("""
                    SELECT
                        cs.server_id,
                        s.server_name,
                        s.infra_type,
                        cs.assignment_type,
                        cs.deployment_path,
                        cs.status
                    FROM component_servers cs
                    JOIN cmdb_servers s ON cs.server_id = s.server_id
                    WHERE cs.component_id = ? AND cs.status = 'active'
                """, (component_id,))

                for server_row in cursor.fetchall():
                    server = {
                        'server_id': server_row[0],
                        'server_name': server_row[1],
                        'infra_type': server_row[2],
                        'assignment_type': server_row[3],
                        'deployment_path': server_row[4],
                        'status': server_row[5]
                    }
                    component['servers'].append(server)

                components.append(component)

            project['components'] = components
            project['component_count'] = len(components)
            projects.append(project)

        conn.close()
        return projects

    except Exception as e:
        log_error(f"Error fetching detailed projects: {str(e)}")
        print(f"DEBUG: Error in get_detailed_projects: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

def get_component_branches(component_id):
    """Get all branches for a specific component"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT branch_id, component_id, branch_name, current_version, last_build_date,
                           last_build_number, branch_status, auto_build, description, is_active,
                           created_date, created_by, updated_date, updated_by,
                           major_version, minor_version, patch_version, build_number, path_pattern_override
                    FROM component_branches
                    WHERE component_id = ? AND is_active = 1
                    ORDER BY branch_name
                """, (component_id,))

                rows = cursor.fetchall()
                branches = []

                for row in rows:
                    branch = {
                        'branch_id': row[0],
                        'component_id': row[1],
                        'branch_name': row[2],
                        'current_version': row[3],
                        'last_build_date': row[4].isoformat() if row[4] else None,
                        'last_build_number': row[5],
                        'branch_status': row[6],
                        'auto_build': bool(row[7]),
                        'description': row[8],
                        'is_active': bool(row[9]),
                        'created_date': row[10].isoformat() if row[10] else None,
                        'created_by': row[11],
                        'updated_date': row[12].isoformat() if row[12] else None,
                        'updated_by': row[13],
                        'major_version': row[14],
                        'minor_version': row[15],
                        'patch_version': row[16],
                        'build_number': row[17],
                        'path_pattern_override': row[18]
                    }
                    branches.append(branch)

                return branches

    except Exception as e:
        log_error(f"Error fetching component branches: {str(e)}")
        return []

def add_component_branch(component_id, branch_name, branch_status, created_by):
    """Add a new branch for a component"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Check if branch already exists
                cursor.execute("""
                    SELECT COUNT(*) FROM component_branches
                    WHERE component_id = ? AND branch_name = ? AND is_active = 1
                """, (component_id, branch_name))

                if cursor.fetchone()[0] > 0:
                    return False, f"Branch '{branch_name}' already exists for this component"

                # Insert new branch
                cursor.execute("""
                    INSERT INTO component_branches
                    (component_id, branch_name, current_version, branch_status, auto_build,
                     is_active, created_date, created_by, major_version, minor_version,
                     patch_version, build_number)
                    VALUES (?, ?, 1, ?, 0, 1, GETDATE(), ?, 1, 0, 0, 0)
                """, (component_id, branch_name, branch_status, created_by))

                conn.commit()
                log_info(f"Added branch '{branch_name}' for component {component_id}")
                return True, f"Branch '{branch_name}' added successfully"

    except Exception as e:
        log_error(f"Error adding component branch: {str(e)}")
        return False, f"Error adding branch: {str(e)}"

def update_component_branch(branch_id, data, updated_by):
    """Update a component branch"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Build update query dynamically based on provided data
                updates = []
                params = []

                if 'branch_status' in data:
                    updates.append("branch_status = ?")
                    params.append(data['branch_status'])

                if 'auto_build' in data:
                    updates.append("auto_build = ?")
                    params.append(1 if data['auto_build'] else 0)

                if 'description' in data:
                    updates.append("description = ?")
                    params.append(data['description'])

                if 'path_pattern_override' in data:
                    updates.append("path_pattern_override = ?")
                    params.append(data['path_pattern_override'])

                if 'major_version' in data:
                    updates.append("major_version = ?")
                    params.append(data['major_version'])

                if 'minor_version' in data:
                    updates.append("minor_version = ?")
                    params.append(data['minor_version'])

                if 'patch_version' in data:
                    updates.append("patch_version = ?")
                    params.append(data['patch_version'])

                if 'build_number' in data:
                    updates.append("build_number = ?")
                    params.append(data['build_number'])

                if not updates:
                    return False, "No data provided for update"

                updates.append("updated_date = GETDATE()")
                updates.append("updated_by = ?")
                params.append(updated_by)
                params.append(branch_id)

                query = f"UPDATE component_branches SET {', '.join(updates)} WHERE branch_id = ?"
                cursor.execute(query, params)

                conn.commit()
                log_info(f"Updated branch {branch_id}")
                return True, "Branch updated successfully"

    except Exception as e:
        log_error(f"Error updating component branch: {str(e)}")
        return False, f"Error updating branch: {str(e)}"

def delete_component_branch(branch_id, updated_by):
    """Soft delete a component branch"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE component_branches
                    SET is_active = 0, updated_date = GETDATE(), updated_by = ?
                    WHERE branch_id = ?
                """, (updated_by, branch_id))

                conn.commit()
                log_info(f"Soft deleted branch {branch_id}")
                return True, "Branch deleted successfully"

    except Exception as e:
        log_error(f"Error deleting component branch: {str(e)}")
        return False, f"Error deleting branch: {str(e)}"