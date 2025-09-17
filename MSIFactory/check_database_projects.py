#!/usr/bin/env python3
"""
Check what projects exist in the database vs JSON file
"""

import sys
sys.path.append('.')

from auth.simple_auth import SimpleAuth

def check_json_projects():
    """Check projects in JSON file"""
    print("=== Projects in JSON File ===")
    auth = SimpleAuth()
    projects = auth.load_projects()

    print(f"Total projects in JSON: {len(projects)}")
    for project in projects:
        print(f"  ID: {project['project_id']}, Name: {project['project_name']}")

    return projects

def check_database_projects():
    """Check projects in database"""
    print("\n=== Projects in Database ===")

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

        # Get all projects
        cursor.execute("SELECT project_id, project_name, project_key FROM Projects ORDER BY project_id")
        projects = cursor.fetchall()

        print(f"Total projects in database: {len(projects)}")
        for project in projects:
            print(f"  ID: {project[0]}, Name: {project[1]}, Key: {project[2]}")

        conn.close()
        return projects

    except Exception as e:
        print(f"Error connecting to database: {e}")
        return []

def main():
    print("MSI Factory Project Location Check")
    print("=" * 50)

    json_projects = check_json_projects()
    db_projects = check_database_projects()

    print(f"\n=== Summary ===")
    print(f"JSON projects: {len(json_projects)}")
    print(f"Database projects: {len(db_projects)}")

    if len(db_projects) > 0:
        print("\nThe web interface is using the DATABASE, not the JSON file.")
        print("Project ID 10 likely exists in the database.")
    else:
        print("\nDatabase connection failed, falling back to JSON file.")

if __name__ == "__main__":
    main()