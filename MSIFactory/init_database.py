#!/usr/bin/env python3
"""
Database Initialization Script for MSI Factory
Production-ready database setup with robust connection handling
"""

import sys
import os
from datetime import datetime

# Add paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'database'))

from database.connection_manager import (
    connection_manager, test_database_connection, 
    get_db_connection_info, get_robust_session
)
from database.models import (
    Base, User, Project, ProjectEnvironment, Application,
    user_projects_association, engine
)
from config import get_config, validate_environment

def initialize_database():
    """Initialize database with tables and default data"""
    print("=" * 60)
    print("MSI FACTORY - DATABASE INITIALIZATION")
    print("=" * 60)
    
    try:
        # Validate configuration
        print("[INFO] Validating configuration...")
        if not validate_environment():
            print("[ERROR] Configuration validation failed")
            return False
        
        config = get_config()
        
        # Show connection information
        print(f"[INFO] Database Server: {config.DB_SERVER}")
        print(f"[INFO] Database Name: {config.DB_NAME}")
        print(f"[INFO] Authentication: {'Windows' if not config.DB_USERNAME else 'SQL Server'}")
        
        # Test database connection
        print("[INFO] Testing database connection...")
        if not test_database_connection():
            print("[ERROR] Database connection test failed")
            return False
        
        # Create all tables
        print("[INFO] Creating database tables...")
        Base.metadata.create_all(bind=engine)
        print("[OK] Database tables created successfully")
        
        # Insert default data
        print("[INFO] Inserting default data...")
        insert_default_data()
        print("[OK] Default data inserted successfully")
        
        # Verify installation
        print("[INFO] Verifying database installation...")
        if verify_installation():
            print("[OK] Database installation verified")
        else:
            print("[WARNING] Database installation verification failed")
        
        print("=" * 60)
        print("DATABASE INITIALIZATION COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print()
        print("Default Accounts:")
        print("  Admin: admin")
        print("  User:  john.doe")
        print()
        print("You can now start the MSI Factory application:")
        print("  python main.py")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Database initialization failed: {e}")
        return False

def insert_default_data():
    """Insert default system data"""
    with get_robust_session() as session:
        # Insert default admin user
        admin_user = session.query(User).filter_by(username='admin').first()
        if not admin_user:
            admin_user = User(
                username='admin',
                email='admin@company.com',
                first_name='System',
                middle_name='',
                last_name='Administrator',
                status='approved',
                role='admin',
                approved_date=datetime.now(),
                approved_by='system'
            )
            session.add(admin_user)
            session.flush()
            print("  [OK] Admin user created")
        else:
            print("  [INFO] Admin user already exists")
            
        # Insert default regular user
        regular_user = session.query(User).filter_by(username='john.doe').first()
        if not regular_user:
            regular_user = User(
                username='john.doe',
                email='john.doe@company.com',
                first_name='John',
                middle_name='M',
                last_name='Doe',
                status='approved',
                role='user',
                approved_date=datetime.now(),
                approved_by='admin'
            )
            session.add(regular_user)
            session.flush()
            print("  [OK] Regular user created")
        else:
            print("  [INFO] Regular user already exists")
            
        # Insert default projects
        default_projects = [
            {
                'project_name': 'Customer Portal Web Application',
                'project_key': 'WEBAPP01',
                'description': 'Customer-facing web portal for service requests and account management',
                'project_type': 'WebApp',
                'owner_team': 'Customer Experience Team',
                'color_primary': '#2c3e50',
                'color_secondary': '#3498db',
                'created_by': 'admin',
                'environments': ['DEV', 'QA', 'UAT', 'PROD']
            },
            {
                'project_name': 'Employee Portal Website',
                'project_key': 'PORTAL',
                'description': 'Internal employee self-service portal for HR and IT services',
                'project_type': 'Website',
                'owner_team': 'HR Technology',
                'color_primary': '#27ae60',
                'color_secondary': '#2ecc71',
                'created_by': 'admin',
                'environments': ['DEV', 'QA', 'PROD']
            },
            {
                'project_name': 'Data Synchronization Service',
                'project_key': 'DATASYNC',
                'description': 'Background service for synchronizing data between systems',
                'project_type': 'Service',
                'owner_team': 'Integration Team',
                'color_primary': '#e74c3c',
                'color_secondary': '#c0392b',
                'created_by': 'admin',
                'environments': ['DEV', 'QA', 'UAT', 'PREPROD', 'PROD']
            }
        ]
        
        for proj_data in default_projects:
            existing_project = session.query(Project).filter_by(project_key=proj_data['project_key']).first()
            if not existing_project:
                environments = proj_data.pop('environments')
                project = Project(**proj_data)
                session.add(project)
                session.flush()
                
                # Add environments for this project
                for env_name in environments:
                    env = ProjectEnvironment(
                        project_id=project.project_id,
                        environment_name=env_name,
                        environment_description=f'{env_name} Environment'
                    )
                    session.add(env)
                
                # Grant admin user access to all projects
                session.execute(
                    user_projects_association.insert().values(
                        user_id=admin_user.user_id,
                        project_id=project.project_id,
                        access_level='admin',
                        granted_by='system'
                    )
                )
                
                print(f"  [OK] Project '{proj_data['project_key']}' created")
            else:
                print(f"  [INFO] Project '{proj_data['project_key']}' already exists")
        
        # Grant regular user access to specific projects
        webapp_project = session.query(Project).filter_by(project_key='WEBAPP01').first()
        portal_project = session.query(Project).filter_by(project_key='PORTAL').first()
        
        if webapp_project and regular_user:
            # Check if relationship already exists
            existing = session.execute(
                user_projects_association.select().where(
                    user_projects_association.c.user_id == regular_user.user_id,
                    user_projects_association.c.project_id == webapp_project.project_id
                )
            ).first()
            
            if not existing:
                session.execute(
                    user_projects_association.insert().values(
                        user_id=regular_user.user_id,
                        project_id=webapp_project.project_id,
                        access_level='user',
                        granted_by='admin'
                    )
                )
        
        if portal_project and regular_user:
            # Check if relationship already exists
            existing = session.execute(
                user_projects_association.select().where(
                    user_projects_association.c.user_id == regular_user.user_id,
                    user_projects_association.c.project_id == portal_project.project_id
                )
            ).first()
            
            if not existing:
                session.execute(
                    user_projects_association.insert().values(
                        user_id=regular_user.user_id,
                        project_id=portal_project.project_id,
                        access_level='user',
                        granted_by='admin'
                    )
                )
        
        # Insert legacy applications for compatibility
        legacy_apps = [
            {
                'app_short_key': 'WEBAPP01',
                'app_name': 'Customer Portal Web App',
                'description': 'Customer-facing web portal',
                'owner_team': 'Customer Experience'
            },
            {
                'app_short_key': 'PORTAL',
                'app_name': 'Employee Portal Website',
                'description': 'Employee self-service portal',
                'owner_team': 'HR Technology'
            },
            {
                'app_short_key': 'DATASYNC',
                'app_name': 'Data Synchronization Service',
                'description': 'Background data sync service',
                'owner_team': 'Integration Team'
            }
        ]
        
        for app_data in legacy_apps:
            existing_app = session.query(Application).filter_by(app_short_key=app_data['app_short_key']).first()
            if not existing_app:
                app = Application(**app_data)
                session.add(app)
                print(f"  [OK] Legacy application '{app_data['app_short_key']}' created")
            else:
                print(f"  [INFO] Legacy application '{app_data['app_short_key']}' already exists")

def verify_installation():
    """Verify database installation"""
    try:
        with get_robust_session() as session:
            # Check users
            user_count = session.query(User).count()
            print(f"  [INFO] Users in database: {user_count}")
            
            # Check projects
            project_count = session.query(Project).count()
            print(f"  [INFO] Projects in database: {project_count}")
            
            # Check applications
            app_count = session.query(Application).count()
            print(f"  [INFO] Applications in database: {app_count}")
            
            # Verify admin user exists
            admin_user = session.query(User).filter_by(username='admin', role='admin').first()
            if not admin_user:
                print("  [ERROR] Admin user not found")
                return False
            
            print("  [OK] Database installation verification completed")
            return True
            
    except Exception as e:
        print(f"  [ERROR] Database verification failed: {e}")
        return False

def main():
    """Main initialization function"""
    if len(sys.argv) > 1 and sys.argv[1] == '--force':
        print("[WARNING] Force initialization requested")
        print("[INFO] This will recreate all database tables")
        response = input("Are you sure? (yes/no): ")
        if response.lower() != 'yes':
            print("[INFO] Initialization cancelled")
            return
        
        # Drop and recreate tables
        print("[INFO] Dropping existing tables...")
        Base.metadata.drop_all(bind=engine)
        print("[OK] Tables dropped")
    
    success = initialize_database()
    
    if success:
        print("[SUCCESS] Database initialization completed successfully")
        sys.exit(0)
    else:
        print("[FAILURE] Database initialization failed")
        sys.exit(1)

if __name__ == '__main__':
    main()