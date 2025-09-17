#!/usr/bin/env python3
"""
Test database connection and project deletion
"""

import sys
sys.path.append('.')

from logger import log_info, log_error

def test_database_connection():
    """Test database connection and list projects"""
    print("=== Testing Database Connection ===")

    try:
        import pyodbc
        print("✓ pyodbc imported successfully")

        # Connection string (same as in main.py)
        conn_str = (
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=SUMEETGILL7E47\\MSSQLSERVER01;"
            "DATABASE=MSIFactory;"
            "Trusted_Connection=yes;"
        )

        print("Attempting database connection...")
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        print("✓ Database connection successful")

        # Check if Projects table exists
        try:
            cursor.execute("SELECT COUNT(*) FROM Projects")
            total_projects = cursor.fetchone()[0]
            print(f"✓ Projects table exists with {total_projects} projects")
        except Exception as table_error:
            print(f"✗ Projects table error: {table_error}")
            conn.close()
            return False

        # List all projects
        cursor.execute("SELECT project_id, project_name FROM Projects ORDER BY project_id")
        projects = cursor.fetchall()

        if projects:
            print("Projects in database:")
            for project in projects:
                print(f"  ID: {project[0]}, Name: {project[1]}")
        else:
            print("No projects found in database")

        # Test if project 10 exists
        cursor.execute("SELECT COUNT(*) FROM Projects WHERE project_id = ?", (10,))
        project_10_count = cursor.fetchone()[0]
        print(f"\nProject ID 10 exists: {project_10_count > 0} (count: {project_10_count})")

        conn.close()
        return True

    except ImportError:
        print("✗ pyodbc not available")
        return False
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False

def test_delete_function():
    """Test the delete function from main.py"""
    print("\n=== Testing Delete Function ===")

    try:
        # Import the function
        from main import delete_project_from_database

        # Test with project 10
        print("Testing deletion of project 10...")
        success, message = delete_project_from_database(10)

        print(f"Deletion result: {success}")
        print(f"Message: {message}")

        return success

    except Exception as e:
        print(f"Error testing delete function: {e}")
        return False

def main():
    print("MSI Factory Database Test")
    print("=" * 50)

    connection_ok = test_database_connection()

    if connection_ok:
        delete_ok = test_delete_function()

        print(f"\n=== Results ===")
        print(f"Database connection: {'✓ PASS' if connection_ok else '✗ FAIL'}")
        print(f"Delete function: {'✓ PASS' if delete_ok else '✗ FAIL'}")
    else:
        print("\n✗ Cannot test delete function - database connection failed")

    print("\nCheck logs/system.log for detailed logging")

if __name__ == "__main__":
    main()