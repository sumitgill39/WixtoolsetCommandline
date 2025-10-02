"""
Permission Manager for MSI Factory
Handles user permission operations for viewing soft-deleted records
Follows hybrid API + database fallback pattern
"""

import pyodbc
from datetime import datetime
import json
from core.database_operations import get_db_connection


def log_info(message):
    """Simple logging function"""
    print(f"[INFO] {message}")


def log_error(message):
    """Simple logging function"""
    print(f"[ERROR] {message}")


def get_permission_presets(api_client=None):
    """Get all available permission presets using API first, database fallback"""

    # Try API first if available
    if api_client:
        try:
            log_info("Attempting to get permission presets via API")
            # Note: API endpoint would need to be implemented
            # response = api_client._make_request('GET', '/permissions/presets')
            # if response.get('success'):
            #     return response.get('data', [])
        except Exception as e:
            log_error(f"API call failed for permission presets: {str(e)}")

    # Fallback to direct database access
    log_info("Using database fallback for permission presets")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT preset_id, preset_name, preset_description, permissions
            FROM permission_presets
            WHERE is_active = 1
            ORDER BY preset_name
        """)

        presets = []
        for row in cursor.fetchall():
            presets.append({
                'preset_id': row.preset_id,
                'preset_name': row.preset_name,
                'preset_description': row.preset_description,
                'permissions': row.permissions
            })

        cursor.close()
        conn.close()

        return presets

    except Exception as e:
        log_error(f"Error getting permission presets: {str(e)}")
        return []


def get_user_permissions(user_id, api_client=None):
    """Get all active permissions for a specific user using API first, database fallback"""

    # Try API first if available
    if api_client:
        try:
            log_info(f"Attempting to get user permissions for user {user_id} via API")
            # Note: API endpoint would need to be implemented
            # response = api_client._make_request('GET', f'/permissions/users/{user_id}')
            # if response.get('success'):
            #     return response.get('data', [])
        except Exception as e:
            log_error(f"API call failed for user permissions: {str(e)}")

    # Fallback to direct database access
    log_info(f"Using database fallback for user {user_id} permissions")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT permission_id, permission_type, permission_value,
                   description, granted_by, granted_date, expires_date
            FROM user_permissions
            WHERE user_id = ?
            AND is_active = 1
            AND (expires_date IS NULL OR expires_date > GETDATE())
            ORDER BY permission_type
        """, (user_id,))

        permissions = []
        for row in cursor.fetchall():
            permissions.append({
                'permission_id': row.permission_id,
                'permission_type': row.permission_type,
                'permission_value': row.permission_value,
                'description': row.description,
                'granted_by': row.granted_by,
                'granted_date': row.granted_date,
                'expires_date': row.expires_date
            })

        cursor.close()
        conn.close()

        return permissions

    except Exception as e:
        log_error(f"Error getting user permissions: {str(e)}")
        return []


def get_users_with_permissions(api_client=None):
    """Get all users who have special permissions using API first, database fallback"""

    # Try API first if available
    if api_client:
        try:
            log_info("Attempting to get users with permissions via API")
            # Note: API endpoint would need to be implemented
            # response = api_client._make_request('GET', '/permissions/users-summary')
            # if response.get('success'):
            #     return response.get('data', [])
        except Exception as e:
            log_error(f"API call failed for users with permissions: {str(e)}")

    # Fallback to direct database access
    log_info("Using database fallback for users with permissions")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get users with their permissions summary
        cursor.execute("""
            SELECT DISTINCT
                u.user_id, u.first_name, u.last_name, u.email, u.role,
                MAX(up.updated_date) as last_modified
            FROM users u
            LEFT JOIN user_permissions up ON u.user_id = up.user_id
                AND up.is_active = 1
                AND (up.expires_date IS NULL OR up.expires_date > GETDATE())
            WHERE u.is_active = 1
            GROUP BY u.user_id, u.first_name, u.last_name, u.email, u.role
            ORDER BY u.first_name, u.last_name
        """)

        users = []
        for row in cursor.fetchall():
            user_data = {
                'user_id': row.user_id,
                'first_name': row.first_name,
                'last_name': row.last_name,
                'email': row.email,
                'role': row.role,
                'last_modified': row.last_modified,
                'permissions': []
            }

            # Get permission types for this user
            cursor2 = conn.cursor()
            cursor2.execute("""
                SELECT DISTINCT permission_type
                FROM user_permissions
                WHERE user_id = ?
                AND is_active = 1
                AND (expires_date IS NULL OR expires_date > GETDATE())
            """, (row.user_id,))

            for perm_row in cursor2.fetchall():
                user_data['permissions'].append(perm_row.permission_type)

            cursor2.close()
            users.append(user_data)

        cursor.close()
        conn.close()

        return users

    except Exception as e:
        log_error(f"Error getting users with permissions: {str(e)}")
        return []


def grant_user_permission(user_id, permission_type, granted_by, expires_date=None, description=None):
    """Grant a permission to a user"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if permission already exists
        cursor.execute("""
            SELECT permission_id
            FROM user_permissions
            WHERE user_id = ? AND permission_type = ? AND permission_value = ?
        """, (user_id, permission_type, 'granted'))

        existing = cursor.fetchone()

        if existing:
            # Update existing permission
            cursor.execute("""
                UPDATE user_permissions
                SET is_active = 1,
                    expires_date = ?,
                    description = ?,
                    updated_date = GETDATE(),
                    updated_by = ?
                WHERE permission_id = ?
            """, (expires_date, description, granted_by, existing.permission_id))
        else:
            # Insert new permission
            cursor.execute("""
                INSERT INTO user_permissions (
                    user_id, permission_type, permission_value,
                    description, granted_by, expires_date,
                    created_date, updated_date
                ) VALUES (?, ?, ?, ?, ?, ?, GETDATE(), GETDATE())
            """, (user_id, permission_type, 'granted', description, granted_by, expires_date))

        conn.commit()
        cursor.close()
        conn.close()

        log_info(f"Permission granted: User {user_id}, Type: {permission_type}, By: {granted_by}")
        return True, "Permission granted successfully"

    except Exception as e:
        log_error(f"Error granting permission: {str(e)}")
        return False, str(e)


def revoke_user_permission(permission_id):
    """Revoke a specific permission"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Soft delete the permission
        cursor.execute("""
            UPDATE user_permissions
            SET is_active = 0,
                updated_date = GETDATE()
            WHERE permission_id = ?
        """, (permission_id,))

        conn.commit()
        cursor.close()
        conn.close()

        log_info(f"Permission revoked: ID {permission_id}")
        return True, "Permission revoked successfully"

    except Exception as e:
        log_error(f"Error revoking permission: {str(e)}")
        return False, str(e)


def user_has_permission(user_id, permission_type, api_client=None):
    """Check if a user has a specific permission using API first, database fallback"""

    # Try API first if available
    if api_client:
        try:
            log_info(f"Attempting to check permission {permission_type} for user {user_id} via API")
            # Note: API endpoint would need to be implemented
            # response = api_client._make_request('GET', f'/permissions/check/{user_id}/{permission_type}')
            # if response.get('success'):
            #     return response.get('has_permission', False)
        except Exception as e:
            log_error(f"API call failed for permission check: {str(e)}")

    # Fallback to direct database access
    log_info(f"Using database fallback for permission check: user {user_id}, type {permission_type}")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if user is admin (admins have all permissions)
        cursor.execute("SELECT role FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()

        if user and user.role == 'admin':
            cursor.close()
            conn.close()
            return True

        # Check specific permission
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM user_permissions
            WHERE user_id = ?
            AND permission_type = ?
            AND is_active = 1
            AND (expires_date IS NULL OR expires_date > GETDATE())
        """, (user_id, permission_type))

        result = cursor.fetchone()
        has_permission = result.count > 0 if result else False

        cursor.close()
        conn.close()

        return has_permission

    except Exception as e:
        log_error(f"Error checking permission: {str(e)}")
        return False


def get_user_id_from_session(session):
    """Get user_id from session username"""
    try:
        username = session.get('username')
        if not username:
            return None

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT user_id FROM users WHERE email = ?", (username,))
        result = cursor.fetchone()

        cursor.close()
        conn.close()

        return result.user_id if result else None

    except Exception as e:
        log_error(f"Error getting user_id from session: {str(e)}")
        return None