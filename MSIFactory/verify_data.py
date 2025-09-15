#!/usr/bin/env python3
"""
Verify Database Data - Check that all project information is saved
"""

import pyodbc

# Direct connection to MS SQL Server
conn_str = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=SUMEETGILL7E47\\MSSQLSERVER01;"
    "DATABASE=MSIFactory;"
    "Trusted_Connection=yes;"
)

try:
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    
    print("=== Verifying All Project Data ===\n")
    
    # Get the latest project (highest ID)
    cursor.execute("SELECT TOP 1 * FROM projects ORDER BY project_id DESC")
    project = cursor.fetchone()
    
    if project:
        print(f"Latest Project (ID: {project[0]}):")
        print(f"  Name: {project[1]}")
        print(f"  Key: {project[2]}")
        print(f"  Description: {project[3]}")
        print(f"  Type: {project[4]}")
        print(f"  Owner Team: {project[5]}")
        print(f"  Status: {project[8]}")
        print(f"  Artifact Source Type: {project[10]}")
        print(f"  Artifact URL: {project[11]}")
        print(f"  Artifact Username: {project[12]}")
        print(f"  Artifact Password: {'***' if project[13] else 'None'}")
        
        project_id = project[0]
        
        # Check environments for this project
        print(f"\nEnvironments for Project {project_id}:")
        cursor.execute("SELECT * FROM project_environments WHERE project_id = ?", (project_id,))
        environments = cursor.fetchall()
        
        for env in environments:
            print(f"  - {env[2]} ({env[3]})")
            print(f"    Servers: {env[4] if env[4] else 'None'}")
            print(f"    Region: {env[5] if env[5] else 'None'}")
        
        # Check components for this project
        print(f"\nComponents for Project {project_id}:")
        cursor.execute("SELECT * FROM components WHERE project_id = ?", (project_id,))
        components = cursor.fetchall()
        
        for comp in components:
            print(f"  - {comp[2]} ({comp[3]})")
            print(f"    Framework: {comp[4]}")
            print(f"    Artifact Source: {comp[5]}")
    
    print(f"\n=== Summary ===")
    cursor.execute("SELECT COUNT(*) FROM projects")
    print(f"Total Projects: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM project_environments")
    print(f"Total Environments: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM components")
    print(f"Total Components: {cursor.fetchone()[0]}")
    
except Exception as e:
    print(f"\n[ERROR] Database verification failed: {e}")
    import traceback
    traceback.print_exc()
    
finally:
    if 'conn' in locals():
        conn.close()
        print("\nDatabase connection closed")