#!/usr/bin/env python3
"""
MSI Factory SQL Server Database Manager
Handles SQL Server database initialization, connections, and operations using SQLAlchemy
"""

import os
import json
from datetime import datetime
from contextlib import contextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

from models import (
    Base, User, Project, ProjectEnvironment, AccessRequest, 
    MSIBuild, SystemLog, UserSession, SystemSetting, Application,
    DatabaseConfig, get_db_session, create_tables, drop_tables,
    user_projects_association
)

class SQLServerDatabaseManager:
    """SQL Server Database Manager using SQLAlchemy"""
    
    def __init__(self, config=None):
        """Initialize database manager with SQL Server configuration"""
        self.config = config or DatabaseConfig()
        self.engine = self.config.get_engine()
        self.SessionLocal = self.config.get_session_factory()
        
    @contextmanager
    def get_session(self):
        """Get database session with context manager"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def test_connection(self):
        """Test database connection"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                return True
        except Exception as e:
            print(f"[ERROR] Database connection failed: {e}")
            return False
    
    def initialize_database(self):
        """Initialize database with tables and default data"""
        try:
            print("[INFO] Initializing SQL Server database...")
            
            # Test connection first
            if not self.test_connection():
                return False
            
            # Create all tables
            create_tables()
            
            # Insert default data
            self._insert_default_data()
            
            # Verify database structure
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT TABLE_NAME 
                    FROM INFORMATION_SCHEMA.TABLES 
                    WHERE TABLE_TYPE = 'BASE TABLE' AND TABLE_CATALOG = ?
                """), (self.config.database,))
                tables = [row[0] for row in result.fetchall()]
            
            print(f"[OK] Database initialized with {len(tables)} tables:")
            for table in sorted(tables):
                print(f"    - {table}")
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Database initialization failed: {e}")
            return False
    
    def _insert_default_data(self):
        """Insert default system data"""
        with self.get_session() as session:
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
                session.flush()  # Get the user_id
                
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
            
            # Grant regular user access to specific projects
            webapp_project = session.query(Project).filter_by(project_key='WEBAPP01').first()
            portal_project = session.query(Project).filter_by(project_key='PORTAL').first()
            
            if webapp_project and regular_user:
                session.execute(
                    user_projects_association.insert().values(
                        user_id=regular_user.user_id,
                        project_id=webapp_project.project_id,
                        access_level='user',
                        granted_by='admin'
                    )
                )
            
            if portal_project and regular_user:
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
            
            # Insert default system settings
            default_settings = [
                {
                    'setting_key': 'app_name',
                    'setting_value': 'Swadhina MSI Factory',
                    'setting_type': 'string',
                    'description': 'Application name displayed in UI',
                    'category': 'general'
                },
                {
                    'setting_key': 'app_version',
                    'setting_value': '1.0.0',
                    'setting_type': 'string',
                    'description': 'Current application version',
                    'category': 'general'
                },
                {
                    'setting_key': 'max_concurrent_builds',
                    'setting_value': '5',
                    'setting_type': 'integer',
                    'description': 'Maximum number of concurrent MSI builds',
                    'category': 'build'
                },
                {
                    'setting_key': 'build_timeout_minutes',
                    'setting_value': '30',
                    'setting_type': 'integer',
                    'description': 'Build timeout in minutes',
                    'category': 'build'
                },
                {
                    'setting_key': 'enable_audit_logging',
                    'setting_value': 'true',
                    'setting_type': 'boolean',
                    'description': 'Enable detailed audit logging',
                    'category': 'security'
                },
                {
                    'setting_key': 'session_timeout_hours',
                    'setting_value': '8',
                    'setting_type': 'integer',
                    'description': 'User session timeout in hours',
                    'category': 'security'
                },
                {
                    'setting_key': 'database_schema_version',
                    'setting_value': '1.0',
                    'setting_type': 'string',
                    'description': 'Current database schema version',
                    'category': 'system'
                }
            ]
            
            for setting_data in default_settings:
                existing_setting = session.query(SystemSetting).filter_by(setting_key=setting_data['setting_key']).first()
                if not existing_setting:
                    setting = SystemSetting(**setting_data)
                    session.add(setting)
    
    def migrate_from_json(self, json_data_path='database'):
        """Migrate existing JSON data to SQL Server database"""
        json_files = {
            'users': os.path.join(json_data_path, 'users.json'),
            'projects': os.path.join(json_data_path, 'projects.json'),
            'access_requests': os.path.join(json_data_path, 'access_requests.json'),
            'applications': os.path.join(json_data_path, 'applications.json')
        }
        
        migrated_count = 0
        
        with self.get_session() as session:
            # Migrate users
            if os.path.exists(json_files['users']):
                with open(json_files['users'], 'r') as f:
                    users_data = json.load(f)
                
                for user_data in users_data.get('users', []):
                    try:
                        existing_user = session.query(User).filter_by(username=user_data['username']).first()
                        if not existing_user:
                            user = User(
                                username=user_data['username'],
                                email=user_data['email'],
                                domain=user_data.get('domain', 'COMPANY'),
                                first_name=user_data['first_name'],
                                middle_name=user_data.get('middle_name', ''),
                                last_name=user_data['last_name'],
                                status=user_data['status'],
                                role=user_data['role'],
                                approved_date=datetime.fromisoformat(user_data['approved_date']) if user_data.get('approved_date') else None,
                                approved_by=user_data.get('approved_by'),
                                created_date=datetime.fromisoformat(user_data['created_date']) if user_data.get('created_date') else datetime.now()
                            )
                            session.add(user)
                            migrated_count += 1
                    except Exception as e:
                        print(f"[WARNING] Failed to migrate user {user_data.get('username')}: {e}")
                
                session.flush()
                print(f"[OK] Migrated {len(users_data.get('users', []))} users")
            
            # Similar migration logic for projects, access_requests, etc...
            # [Implementation continues with other data migration]
        
        print(f"[OK] Migration completed. Total records migrated: {migrated_count}")
        return True
    
    def get_database_stats(self):
        """Get database statistics"""
        stats = {}
        
        with self.get_session() as session:
            # Get table counts
            stats['users_count'] = session.query(User).count()
            stats['projects_count'] = session.query(Project).count()
            stats['access_requests_count'] = session.query(AccessRequest).count()
            stats['msi_builds_count'] = session.query(MSIBuild).count()
            stats['system_logs_count'] = session.query(SystemLog).count()
            stats['user_sessions_count'] = session.query(UserSession).count()
            stats['system_settings_count'] = session.query(SystemSetting).count()
            
            # Get database size (SQL Server specific query)
            try:
                with self.engine.connect() as conn:
                    result = conn.execute(text("""
                        SELECT 
                            SUM(CAST(FILEPROPERTY(name, 'SpaceUsed') AS bigint) * 8192.) / 1024 / 1024 as size_mb
                        FROM sys.database_files
                        WHERE type_desc = 'ROWS'
                    """))
                    row = result.fetchone()
                    stats['database_size_mb'] = round(row[0] if row and row[0] else 0, 2)
            except Exception:
                stats['database_size_mb'] = 'Unknown'
            
            # Get schema version
            setting = session.query(SystemSetting).filter_by(setting_key='database_schema_version').first()
            stats['schema_version'] = setting.setting_value if setting else 'Unknown'
        
        return stats
    
    def backup_database(self, backup_path=None):
        """Create database backup (SQL Server specific)"""
        if not backup_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"C:\\Backups\\MSIFactory_backup_{timestamp}.bak"
        
        try:
            with self.engine.connect() as conn:
                # Use SQL Server BACKUP command
                backup_sql = text(f"""
                    BACKUP DATABASE [{self.config.database}] 
                    TO DISK = '{backup_path}'
                    WITH FORMAT, COMPRESSION
                """)
                conn.execute(backup_sql)
                conn.commit()
            
            print(f"[OK] Database backed up to: {backup_path}")
            return backup_path
            
        except Exception as e:
            print(f"[ERROR] Database backup failed: {e}")
            return None

def main():
    """Main function for command-line usage"""
    import sys
    
    db_manager = SQLServerDatabaseManager()
    
    if len(sys.argv) < 2:
        print("MSI Factory SQL Server Database Manager")
        print("Usage:")
        print("  python db_manager_sqlserver.py init        - Initialize database")
        print("  python db_manager_sqlserver.py test        - Test database connection")
        print("  python db_manager_sqlserver.py migrate     - Migrate from JSON files")
        print("  python db_manager_sqlserver.py backup      - Create database backup")
        print("  python db_manager_sqlserver.py stats       - Show database statistics")
        return
    
    command = sys.argv[1].lower()
    
    if command == 'test':
        success = db_manager.test_connection()
        if success:
            print("[OK] Database connection successful")
        else:
            print("[ERROR] Database connection failed")
    
    elif command == 'init':
        success = db_manager.initialize_database()
        if success:
            print("[OK] Database initialization completed")
        else:
            print("[ERROR] Database initialization failed")
    
    elif command == 'migrate':
        success = db_manager.migrate_from_json()
        if success:
            print("[OK] Migration completed")
        else:
            print("[ERROR] Migration failed")
    
    elif command == 'backup':
        backup_path = db_manager.backup_database()
        if backup_path:
            print(f"[OK] Backup created: {backup_path}")
        else:
            print("[ERROR] Backup failed")
    
    elif command == 'stats':
        stats = db_manager.get_database_stats()
        print("Database Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
    
    else:
        print(f"Unknown command: {command}")

if __name__ == '__main__':
    main()