#!/usr/bin/env python3
"""
Authorization Module for MSI Factory
Handles role-based access control and permission checking

COMPREHENSIVE KNOWLEDGE BASE - THREE-TIER ROLE-BASED AUTHORIZATION SYSTEM
=========================================================================

OVERVIEW:
This module implements a complete three-tier role-based authorization system for MSI Factory,
designed to provide granular access control for Technical Project Managers (PowerUsers) while
maintaining security and audit trails.

THREE-TIER ROLE SYSTEM:
-----------------------
1. USER (Standard Role):
   - Read-only access to all modules
   - Can view components, projects, MSI status, CMDB
   - Suitable for: Standard developers, viewers, stakeholders

2. POWERUSER (Technical Project Manager Role):
   - Component CRUD permissions (Create, Read, Update, Enable/Disable)
   - Project Update permissions (modify existing projects)
   - MSI Generation permissions (create deployment packages)
   - CMDB Update permissions (maintain configuration data)
   - Suitable for: Technical Project Managers governing development teams

3. ADMIN (Full System Access):
   - All permissions across all modules
   - User management and role assignment
   - System settings and configuration
   - Full CRUD on all entities (except component deletion)
   - Suitable for: System administrators

POWERUSER SPECIFIC PERMISSIONS:
-------------------------------
PowerUsers are designed for Technical Project Managers who need to:
✅ Add Components (create new components for their projects)
✅ Update Components (modify existing component configurations)
✅ Enable/Disable Components (control component deployment status - Active/Inactive)
✅ Update Projects (modify project details and settings)
✅ Generate MSI (create deployment packages)
✅ Update CMDB (maintain configuration management database)

❌ NOT allowed: User management, system settings, project creation/deletion, component deletion

DATABASE SCHEMA:
---------------
Tables created by role_authorization_update.sql:
- user_permissions: Granular permission definitions
- role_permissions: Role-to-permission mappings
- user_permission_audit: Audit trail for role changes
- v_user_permissions: View for easy permission lookup

IMPLEMENTATION EXAMPLES:
-----------------------
Route Protection:
    @require_admin_or_poweruser()
    def add_component():
        # PowerUsers and Admins can add components
        pass

    @require_permission('components', 'delete')
    def delete_component():
        # Check specific permission for component deletion
        pass

Template Integration:
    {% if can_create_components %}
        <a href="{{ url_for('add_component') }}">Add Component</a>
    {% endif %}

MIGRATION STEPS:
---------------
1. Execute database/role_authorization_update.sql
2. Replace old admin-only checks with new decorators
3. Add template permission helpers
4. Deploy user role management interface
5. Train Technical Project Managers

BUSINESS LOGIC:
--------------
- Maintains soft delete for components (is_enabled = 0)
- Full audit trail for all role changes
- Granular permissions for fine-tuned access control
- Designed for enterprise governance and compliance

SECURITY FEATURES:
-----------------
- Database-driven permission checking
- Decorator-based route protection
- Audit logging for all permission changes
- Role hierarchy validation
- Session-based authentication integration
"""

import pyodbc
import logging
from functools import wraps
from flask import session, flash, redirect, url_for, jsonify, request
from typing import Dict, List, Tuple, Optional

class AuthorizationManager:
    """
    Manages role-based authorization and permissions

    USAGE EXAMPLES:
    --------------
    # Initialize the manager
    auth_manager = AuthorizationManager()

    # Check if user can perform specific action
    can_delete = auth_manager.has_permission('john.doe', 'components', 'delete')

    # Get user's role
    role = auth_manager.get_user_role('jane.smith')

    # Check admin status
    is_admin = auth_manager.is_admin('admin.user')

    # Update user role with audit trail
    success, msg = auth_manager.update_user_role(123, 'poweruser', 'admin.user', 'Promoted to Technical PM')

    DECORATOR USAGE:
    ---------------
    @require_admin_or_poweruser()
    def component_management():
        # Only admins and powerusers can access
        pass

    @require_permission('components', 'create')
    def add_component():
        # Check specific permission
        pass
    """

    def __init__(self):
        self.conn_str = (
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=SUMEETGILL7E47\\MSSQLSERVER01;"
            "DATABASE=MSIFactory;"
            "Trusted_Connection=yes;"
            "Connection Timeout=10;"
        )

        # Role hierarchy (higher number = more permissions)
        self.ROLE_HIERARCHY = {
            'user': 1,
            'poweruser': 2,
            'admin': 3
        }

        # Define role capabilities - This matrix defines what each role can do
        # Format: 'role': {'module': ['action1', 'action2', ...]}
        # Actions: create, read, update, delete, enable_disable, role_manage
        self.ROLE_PERMISSIONS = {
            'user': {
                'components': ['read'],
                'projects': ['read'],
                'msi': ['read'],
                'cmdb': ['read']
            },
            'poweruser': {
                'components': ['create', 'read', 'update', 'enable_disable'],
                'projects': ['read', 'update'],
                'msi': ['create', 'read', 'update'],
                'cmdb': ['read', 'update']
            },
            'admin': {
                'components': ['create', 'read', 'update', 'enable_disable'],
                'projects': ['create', 'read', 'update', 'delete'],
                'users': ['create', 'read', 'update', 'delete', 'role_manage'],
                'msi': ['create', 'read', 'update', 'delete'],
                'cmdb': ['create', 'read', 'update', 'delete'],
                'system': ['read', 'update']
            }
        }

    def get_user_role(self, username: str) -> Optional[str]:
        """Get user role from database"""
        try:
            with pyodbc.connect(self.conn_str) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT role FROM users
                        WHERE username = ? AND is_active = 1
                    """, (username,))

                    row = cursor.fetchone()
                    return row[0] if row else None
        except Exception as e:
            logging.error(f"Error getting user role: {str(e)}")
            return None

    def has_permission(self, username: str, module: str, action: str) -> bool:
        """Check if user has specific permission"""
        try:
            user_role = self.get_user_role(username)
            if not user_role:
                return False

            # Check role permissions
            role_perms = self.ROLE_PERMISSIONS.get(user_role, {})
            module_perms = role_perms.get(module, [])

            return action in module_perms

        except Exception as e:
            logging.error(f"Error checking permission: {str(e)}")
            return False

    def check_user_permission_db(self, username: str, permission_name: str) -> bool:
        """Check permission using database function"""
        try:
            with pyodbc.connect(self.conn_str) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT dbo.CheckUserPermission(?, ?)
                    """, (username, permission_name))

                    result = cursor.fetchone()
                    return bool(result[0]) if result else False
        except Exception as e:
            logging.error(f"Error checking database permission: {str(e)}")
            return False

    def get_user_permissions(self, username: str) -> List[Dict]:
        """Get all permissions for a user"""
        try:
            with pyodbc.connect(self.conn_str) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT permission_name, module_name, action_type, permission_description
                        FROM v_user_permissions
                        WHERE username = ?
                        ORDER BY module_name, action_type
                    """, (username,))

                    permissions = []
                    for row in cursor.fetchall():
                        permissions.append({
                            'permission_name': row[0],
                            'module_name': row[1],
                            'action_type': row[2],
                            'permission_description': row[3]
                        })

                    return permissions
        except Exception as e:
            logging.error(f"Error getting user permissions: {str(e)}")
            return []

    def update_user_role(self, user_id: int, new_role: str, changed_by: str, reason: str = '') -> Tuple[bool, str]:
        """Update user role with audit trail"""
        try:
            with pyodbc.connect(self.conn_str) as conn:
                with conn.cursor() as cursor:
                    # Get current role for audit
                    cursor.execute("SELECT role FROM users WHERE user_id = ?", (user_id,))
                    current_role = cursor.fetchone()

                    if not current_role:
                        return False, "User not found"

                    old_role = current_role[0]

                    # Update role
                    cursor.execute("""
                        UPDATE users SET role = ? WHERE user_id = ?
                    """, (new_role, user_id))

                    # Add audit record
                    cursor.execute("""
                        INSERT INTO user_permission_audit
                        (user_id, old_role, new_role, changed_by, change_reason)
                        VALUES (?, ?, ?, ?, ?)
                    """, (user_id, old_role, new_role, changed_by, reason))

                    conn.commit()
                    logging.info(f"User {user_id} role changed from {old_role} to {new_role} by {changed_by}")
                    return True, f"Role updated successfully from {old_role} to {new_role}"

        except Exception as e:
            error_msg = f"Error updating user role: {str(e)}"
            logging.error(error_msg)
            return False, error_msg

    def is_admin_or_poweruser(self, username: str) -> bool:
        """Check if user is admin or poweruser"""
        role = self.get_user_role(username)
        return role in ['admin', 'poweruser']

    def is_admin(self, username: str) -> bool:
        """Check if user is admin"""
        role = self.get_user_role(username)
        return role == 'admin'

    def can_manage_components(self, username: str) -> bool:
        """Check if user can manage components (admin or poweruser)"""
        return self.has_permission(username, 'components', 'create')


# Global authorization manager instance
auth_manager = AuthorizationManager()


# ROUTE PROTECTION DECORATORS
# ===========================
# These decorators provide easy-to-use route protection for Flask applications.
# They automatically check user permissions and redirect unauthorized users.

def require_permission(module: str, action: str):
    """Decorator to require specific permission for a route"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'username' not in session:
                if request.is_json:
                    return jsonify({'error': 'Authentication required'}), 401
                flash('Please log in to access this page', 'error')
                return redirect(url_for('login'))

            username = session.get('username')
            if not auth_manager.has_permission(username, module, action):
                if request.is_json:
                    return jsonify({'error': 'Insufficient permissions'}), 403
                flash(f'Insufficient permissions for {module} {action}', 'error')
                return redirect(url_for('dashboard'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_admin():
    """Decorator to require admin role"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'username' not in session:
                if request.is_json:
                    return jsonify({'error': 'Authentication required'}), 401
                flash('Please log in to access this page', 'error')
                return redirect(url_for('login'))

            username = session.get('username')
            if not auth_manager.is_admin(username):
                if request.is_json:
                    return jsonify({'error': 'Admin access required'}), 403
                flash('Admin access required', 'error')
                return redirect(url_for('dashboard'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_admin_or_poweruser():
    """Decorator to require admin or poweruser role"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'username' not in session:
                if request.is_json:
                    return jsonify({'error': 'Authentication required'}), 401
                flash('Please log in to access this page', 'error')
                return redirect(url_for('login'))

            username = session.get('username')
            if not auth_manager.is_admin_or_poweruser(username):
                if request.is_json:
                    return jsonify({'error': 'Admin or PowerUser access required'}), 403
                flash('Admin or PowerUser access required', 'error')
                return redirect(url_for('dashboard'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator


# Utility functions
def get_current_user_role() -> Optional[str]:
    """Get current user's role from session"""
    username = session.get('username')
    if username:
        return auth_manager.get_user_role(username)
    return None


def can_user_access(module: str, action: str) -> bool:
    """Check if current user can access specific module/action"""
    username = session.get('username')
    if username:
        return auth_manager.has_permission(username, module, action)
    return False


def get_user_permissions_for_display() -> List[Dict]:
    """Get current user's permissions for UI display"""
    username = session.get('username')
    if username:
        return auth_manager.get_user_permissions(username)
    return []