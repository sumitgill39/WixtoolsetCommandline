#!/usr/bin/env python3
"""
Direct Database Test - Check if we can insert projects
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
    
    # Test 1: Check if tables exist
    cursor.execute("SELECT COUNT(*) FROM projects")
    project_count = cursor.fetchone()[0]
    print(f"Current projects in database: {project_count}")
    
    # Test 2: Try to insert a test project with all new fields
    insert_sql = """
        INSERT INTO projects (project_name, project_key, description, project_type, 
                            owner_team, color_primary, color_secondary, status, created_by,
                            artifact_source_type, artifact_url, artifact_username, artifact_password)
        OUTPUT INSERTED.project_id
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    # Use a unique timestamp-based project key
    import datetime
    timestamp = datetime.datetime.now().strftime("%H%M%S")
    unique_key = f'TEST{timestamp}'
    
    cursor.execute(insert_sql, (
        'Direct Test Project with Artifacts',
        unique_key,
        'Testing direct database insertion with all new fields',
        'WebApp',
        'Test Team',
        '#2c3e50',
        '#3498db',
        'active',
        'admin',
        'http',
        'http://artifactory.example.com/repo',
        'test_user',
        'test_password'
    ))
    
    project_id = cursor.fetchone()[0]
    print(f"Successfully created project with ID: {project_id}")
    
    # Test 3: Try to add an environment with servers and region
    env_sql = """
        INSERT INTO project_environments (project_id, environment_name, environment_description, servers, region)
        VALUES (?, ?, ?, ?, ?)
    """
    
    cursor.execute(env_sql, (project_id, 'DEV1', 'Development Environment 1', 'SERVER1,SERVER2', 'US-EAST'))
    print("Successfully added environment DEV1 with servers and region")
    
    # Test 4: Try to add a component
    comp_sql = """
        INSERT INTO components (project_id, component_name, component_type, 
                              framework, artifact_source, created_by)
        VALUES (?, ?, ?, ?, ?, ?)
    """
    
    cursor.execute(comp_sql, (
        project_id,
        'Test Web Component',
        'webapp',
        'react',
        'http://artifacts/test',
        'admin'
    ))
    print("Successfully added component")
    
    # Commit the transaction
    conn.commit()
    print("\n[SUCCESS] All database operations completed successfully!")
    
    # Verify the data was saved
    cursor.execute("SELECT project_name, project_key FROM projects WHERE project_id = ?", (project_id,))
    result = cursor.fetchone()
    print(f"Verified: Project '{result[0]}' with key '{result[1]}' exists in database")
    
except Exception as e:
    print(f"\n[ERROR] Database operation failed: {e}")
    import traceback
    traceback.print_exc()
    
finally:
    if 'conn' in locals():
        conn.close()
        print("\nDatabase connection closed")