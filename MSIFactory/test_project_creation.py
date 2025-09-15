#!/usr/bin/env python3
"""
Test Project Creation
Simple test to verify database insertion works
"""

import sys
import os
sys.path.append('database')
from database.connection_manager import execute_with_retry
from sqlalchemy import text

def test_project_creation():
    """Test creating a project directly in database"""
    
    def create_test_project(db_session):
        # Insert main project
        project_insert = """
            INSERT INTO projects (project_name, project_key, description, project_type, 
                                owner_team, color_primary, color_secondary, status, created_by)
            OUTPUT INSERTED.project_id
            VALUES (:project_name, :project_key, :description, :project_type, 
                   :owner_team, :color_primary, :color_secondary, :status, :created_by)
        """
        
        result = db_session.execute(text(project_insert), {
            'project_name': 'Test Project',
            'project_key': 'TEST01',
            'description': 'Test project for validation',
            'project_type': 'WebApp',
            'owner_team': 'Test Team',
            'color_primary': '#2c3e50',
            'color_secondary': '#3498db',
            'status': 'active',
            'created_by': 'admin'
        })
        
        # Get the project ID from the OUTPUT clause
        project_id = result.fetchone()[0]
        print(f"Project created with ID: {project_id}")
        
        # Insert a test environment
        env_insert = """
            INSERT INTO project_environments (project_id, environment_name, environment_description)
            VALUES (:project_id, :environment_name, :environment_description)
        """
        db_session.execute(text(env_insert), {
            'project_id': project_id, 
            'environment_name': 'DEV1', 
            'environment_description': 'DEV1 Environment'
        })
        print("Environment added successfully")
        
        # Insert a test component
        comp_insert = """
            INSERT INTO components (project_id, component_name, component_type, 
                                  framework, artifact_source, created_by)
            VALUES (:project_id, :component_name, :component_type, 
                   :framework, :artifact_source, :created_by)
        """
        db_session.execute(text(comp_insert), {
            'project_id': project_id,
            'component_name': 'Test Component',
            'component_type': 'webapp',
            'framework': 'react',
            'artifact_source': 'test://artifact',
            'created_by': 'admin'
        })
        print("Component added successfully")
        
        return project_id
    
    try:
        # Execute database operations
        project_id = execute_with_retry(create_test_project)
        print(f"SUCCESS: Test project created with ID {project_id}")
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to create test project: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    print("Testing Project Creation...")
    success = test_project_creation()
    if success:
        print("[OK] Project creation test passed")
    else:
        print("[ERROR] Project creation test failed")