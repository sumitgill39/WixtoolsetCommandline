"""
Test script to verify SQL database and UI synchronization
"""

import sys
sys.path.append('auth')
sys.path.append('core')

from auth.simple_auth import SimpleAuth
from core.database_operations import get_all_users_with_sql_projects, get_db_connection
from logger import log_info

def test_sql_ui_sync():
    """Test that UI data reflects SQL database content"""
    print("\n" + "="*60)
    print("Testing SQL Database to UI Synchronization")
    print("="*60)

    # Initialize auth system
    auth_system = SimpleAuth()

    # Get users with SQL project assignments (no auth_system needed)
    print("\nFetching users directly from SQL database...")
    users = get_all_users_with_sql_projects()

    # Display results
    for user in users:
        username = user.get('username')
        role = user.get('role')
        projects = user.get('approved_apps', [])

        print(f"\nUser: {username}")
        print(f"  Role: {role}")
        print(f"  Projects from SQL: {projects}")

    # Also show raw SQL data for comparison
    print("\n" + "-"*60)
    print("Raw SQL Database Content:")
    print("-"*60)

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Show users table
        print("\nTable: [dbo].[users]")
        cursor.execute("SELECT user_id, username, role, is_active FROM users")
        for row in cursor.fetchall():
            print(f"  {row}")

        # Show user_projects table
        print("\nTable: [dbo].[user_projects]")
        cursor.execute("""
            SELECT up.user_id, u.username, p.project_key, up.access_level, up.is_active
            FROM user_projects up
            JOIN users u ON up.user_id = u.user_id
            JOIN projects p ON up.project_id = p.project_id
            ORDER BY u.username, p.project_key
        """)
        for row in cursor.fetchall():
            print(f"  {row}")

        conn.close()

    except Exception as e:
        print(f"Error accessing SQL database: {e}")

    print("\n" + "="*60)
    print("Test Complete - Check if UI data matches SQL content above")
    print("="*60)

if __name__ == "__main__":
    test_sql_ui_sync()