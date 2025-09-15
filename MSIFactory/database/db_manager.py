#!/usr/bin/env python3
"""
MSI Factory Database Manager
Handles database initialization, connections, and operations
"""

import sqlite3
import os
import json
from datetime import datetime
from contextlib import contextmanager

class DatabaseManager:
    def __init__(self, db_path='database/msi_factory.db'):
        """Initialize database manager"""
        self.db_path = db_path
        self.schema_file = 'database/schema.sql'
        
        # Ensure database directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
    @contextmanager
    def get_connection(self):
        """Get database connection with context manager"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign key constraints
        try:
            yield conn
        finally:
            conn.close()
    
    def execute_schema(self):
        """Execute schema file to create/update database"""
        if not os.path.exists(self.schema_file):
            raise FileNotFoundError(f"Schema file not found: {self.schema_file}")
        
        with open(self.schema_file, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        with self.get_connection() as conn:
            # Execute schema in parts to handle multiple statements
            conn.executescript(schema_sql)
            conn.commit()
            
        print(f"[OK] Database schema executed successfully")
        return True
    
    def initialize_database(self):
        """Initialize database with schema and default data"""
        try:
            self.execute_schema()
            
            # Verify database structure
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                    ORDER BY name
                """)
                tables = [row[0] for row in cursor.fetchall()]
            
            print(f"[OK] Database initialized with {len(tables)} tables:")
            for table in tables:
                print(f"    - {table}")
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Database initialization failed: {e}")
            return False
    
    def migrate_from_json(self, json_data_path='database'):
        """Migrate existing JSON data to SQL database"""
        json_files = {
            'users': os.path.join(json_data_path, 'users.json'),
            'projects': os.path.join(json_data_path, 'projects.json'),
            'access_requests': os.path.join(json_data_path, 'access_requests.json'),
            'applications': os.path.join(json_data_path, 'applications.json')
        }
        
        migrated_count = 0
        
        with self.get_connection() as conn:
            # Migrate users
            if os.path.exists(json_files['users']):
                with open(json_files['users'], 'r') as f:
                    users_data = json.load(f)
                
                for user in users_data.get('users', []):
                    try:
                        conn.execute("""
                            INSERT OR REPLACE INTO users 
                            (username, email, domain, first_name, middle_name, last_name, 
                             status, role, approved_date, approved_by, created_date)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP))
                        """, (
                            user['username'], user['email'], user.get('domain', 'COMPANY'),
                            user['first_name'], user.get('middle_name', ''), user['last_name'],
                            user['status'], user['role'], user.get('approved_date'),
                            user.get('approved_by'), user.get('created_date')
                        ))
                        migrated_count += 1
                    except Exception as e:
                        print(f"[WARNING] Failed to migrate user {user.get('username')}: {e}")
                
                print(f"[OK] Migrated {len(users_data.get('users', []))} users")
            
            # Migrate projects
            if os.path.exists(json_files['projects']):
                with open(json_files['projects'], 'r') as f:
                    projects_data = json.load(f)
                
                for project in projects_data.get('projects', []):
                    try:
                        # Insert project
                        conn.execute("""
                            INSERT OR REPLACE INTO projects 
                            (project_id, project_name, project_key, description, project_type, 
                             owner_team, status, color_primary, color_secondary, created_date, created_by)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            project['project_id'], project['project_name'], project['project_key'],
                            project.get('description', ''), project['project_type'], project['owner_team'],
                            project['status'], project.get('color_primary', '#2c3e50'),
                            project.get('color_secondary', '#3498db'), 
                            project.get('created_date'), project.get('created_by', 'admin')
                        ))
                        
                        # Insert project environments
                        for env in project.get('environments', []):
                            conn.execute("""
                                INSERT OR IGNORE INTO project_environments (project_id, environment_name)
                                VALUES (?, ?)
                            """, (project['project_id'], env))
                        
                        migrated_count += 1
                    except Exception as e:
                        print(f"[WARNING] Failed to migrate project {project.get('project_key')}: {e}")
                
                print(f"[OK] Migrated {len(projects_data.get('projects', []))} projects")
            
            # Migrate access requests
            if os.path.exists(json_files['access_requests']):
                with open(json_files['access_requests'], 'r') as f:
                    requests_data = json.load(f)
                
                for request in requests_data.get('requests', []):
                    try:
                        # Get project_id from project_key (app_short_key)
                        project_cursor = conn.execute("""
                            SELECT project_id FROM projects WHERE project_key = ?
                        """, (request.get('app_short_key', ''),))
                        project_row = project_cursor.fetchone()
                        
                        if project_row:
                            conn.execute("""
                                INSERT OR IGNORE INTO access_requests 
                                (request_id, username, email, first_name, middle_name, last_name,
                                 project_id, reason, status, requested_date, processed_date, processed_by)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                request['request_id'], request['username'], request['email'],
                                request['first_name'], request.get('middle_name', ''), request['last_name'],
                                project_row[0], request.get('reason', ''), request['status'],
                                request.get('requested_date'), request.get('approved_date'),
                                request.get('approved_by')
                            ))
                            migrated_count += 1
                    except Exception as e:
                        print(f"[WARNING] Failed to migrate access request {request.get('request_id')}: {e}")
                
                print(f"[OK] Migrated {len(requests_data.get('requests', []))} access requests")
            
            # Create user-project relationships based on approved_apps
            if os.path.exists(json_files['users']):
                with open(json_files['users'], 'r') as f:
                    users_data = json.load(f)
                
                for user in users_data.get('users', []):
                    if user.get('approved_apps'):
                        # Get user_id
                        user_cursor = conn.execute("SELECT user_id FROM users WHERE username = ?", (user['username'],))
                        user_row = user_cursor.fetchone()
                        
                        if user_row:
                            user_id = user_row[0]
                            
                            for app_key in user['approved_apps']:
                                if app_key == '*':
                                    # Grant access to all projects
                                    conn.execute("""
                                        INSERT OR IGNORE INTO user_projects (user_id, project_id, access_level, granted_by)
                                        SELECT ?, project_id, 'admin', 'system' FROM projects
                                    """, (user_id,))
                                else:
                                    # Grant access to specific project
                                    conn.execute("""
                                        INSERT OR IGNORE INTO user_projects (user_id, project_id, access_level, granted_by)
                                        SELECT ?, project_id, 'user', 'admin' 
                                        FROM projects WHERE project_key = ?
                                    """, (user_id, app_key))
            
            conn.commit()
        
        print(f"[OK] Migration completed. Total records migrated: {migrated_count}")
        return True
    
    def backup_database(self, backup_path=None):
        """Create database backup"""
        if not backup_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"database/backups/msi_factory_backup_{timestamp}.db"
        
        # Ensure backup directory exists
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        
        with self.get_connection() as source_conn:
            with sqlite3.connect(backup_path) as backup_conn:
                source_conn.backup(backup_conn)
        
        print(f"[OK] Database backed up to: {backup_path}")
        return backup_path
    
    def get_database_stats(self):
        """Get database statistics"""
        stats = {}
        
        with self.get_connection() as conn:
            # Get table counts
            tables = [
                'users', 'projects', 'user_projects', 'access_requests',
                'msi_builds', 'system_logs', 'user_sessions', 'system_settings'
            ]
            
            for table in tables:
                cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                stats[f"{table}_count"] = cursor.fetchone()[0]
            
            # Get database size
            cursor = conn.execute("PRAGMA page_count")
            page_count = cursor.fetchone()[0]
            cursor = conn.execute("PRAGMA page_size")
            page_size = cursor.fetchone()[0]
            stats['database_size_bytes'] = page_count * page_size
            stats['database_size_mb'] = round(stats['database_size_bytes'] / (1024 * 1024), 2)
            
            # Get schema version
            cursor = conn.execute("""
                SELECT setting_value FROM system_settings 
                WHERE setting_key = 'database_schema_version'
            """)
            version_row = cursor.fetchone()
            stats['schema_version'] = version_row[0] if version_row else 'Unknown'
        
        return stats
    
    def execute_query(self, query, params=None):
        """Execute custom query"""
        with self.get_connection() as conn:
            if params:
                cursor = conn.execute(query, params)
            else:
                cursor = conn.execute(query)
            
            if query.strip().upper().startswith('SELECT'):
                return cursor.fetchall()
            else:
                conn.commit()
                return cursor.rowcount

def main():
    """Main function for command-line usage"""
    import sys
    
    db_manager = DatabaseManager()
    
    if len(sys.argv) < 2:
        print("MSI Factory Database Manager")
        print("Usage:")
        print("  python db_manager.py init        - Initialize database")
        print("  python db_manager.py migrate     - Migrate from JSON files")
        print("  python db_manager.py backup      - Create database backup")
        print("  python db_manager.py stats       - Show database statistics")
        return
    
    command = sys.argv[1].lower()
    
    if command == 'init':
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
        print(f"[OK] Backup created: {backup_path}")
    
    elif command == 'stats':
        stats = db_manager.get_database_stats()
        print("Database Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
    
    else:
        print(f"Unknown command: {command}")

if __name__ == '__main__':
    main()