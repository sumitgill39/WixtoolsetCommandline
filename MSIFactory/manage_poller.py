#!/usr/bin/env python3
"""
Management script for JFrog Artifact Polling System
Provides commands to start, stop, status, and configure the polling service
"""

import sys
import os
import json
import pyodbc
from datetime import datetime
import argparse
from pathlib import Path
from artifact_poller import JFrogArtifactPoller

class PollerManager:
    """Manages the artifact polling system"""
    
    def __init__(self):
        self.db_connection_string = (
            "DRIVER={ODBC Driver 17 for SQL Server};"
            "SERVER=SUMEETGILL7E47\\MSSQLSERVER01;"
            "DATABASE=MSIFactory;"
            "Trusted_Connection=yes;"
        )
        
    def configure_component(self, component_id: int, branch_name: str, 
                           polling_enabled: bool = True):
        """Configure a component for polling"""
        try:
            conn = pyodbc.connect(self.db_connection_string)
            cursor = conn.cursor()
            
            # Update component with branch and polling settings
            cursor.execute("""
                UPDATE components
                SET branch_name = ?,
                    polling_enabled = ?
                WHERE component_id = ?
            """, (branch_name, polling_enabled, component_id))
            
            conn.commit()
            
            print(f"[OK] Component {component_id} configured:")
            print(f"  Branch: {branch_name}")
            print(f"  Polling: {'Enabled' if polling_enabled else 'Disabled'}")
            
            conn.close()
            
        except Exception as e:
            print(f"[ERROR] Error configuring component: {e}")
            
    def list_components(self):
        """List all components and their polling status"""
        try:
            conn = pyodbc.connect(self.db_connection_string)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    c.component_id,
                    c.component_name,
                    p.project_name,
                    c.branch_name,
                    c.polling_enabled,
                    c.last_poll_time,
                    c.last_artifact_version
                FROM components c
                INNER JOIN projects p ON c.project_id = p.project_id
                ORDER BY p.project_name, c.component_name
            """)
            
            rows = cursor.fetchall()
            
            print("\n" + "="*100)
            print("COMPONENT POLLING STATUS")
            print("="*100)
            print(f"{'ID':<5} {'Component':<25} {'Project':<20} {'Branch':<15} {'Polling':<10} {'Last Poll':<20} {'Version':<15}")
            print("-"*100)
            
            for row in rows:
                comp_id = row[0]
                comp_name = row[1][:24]
                proj_name = row[2][:19]
                branch = row[3][:14] if row[3] else 'Not set'
                polling = '[Y] Yes' if row[4] else '[N] No'
                last_poll = row[5].strftime('%Y-%m-%d %H:%M') if row[5] else 'Never'
                version = row[6][:14] if row[6] else 'None'
                
                print(f"{comp_id:<5} {comp_name:<25} {proj_name:<20} {branch:<15} {polling:<10} {last_poll:<20} {version:<15}")
            
            print("="*100)
            print(f"Total components: {len(rows)}")
            print(f"Polling enabled: {sum(1 for r in rows if r[4])}")
            print(f"Polling disabled: {sum(1 for r in rows if not r[4])}")
            
            conn.close()
            
        except Exception as e:
            print(f"[ERROR] Error listing components: {e}")
            
    def show_history(self, component_id: int = None, limit: int = 10):
        """Show artifact download history"""
        try:
            conn = pyodbc.connect(self.db_connection_string)
            cursor = conn.cursor()
            
            if component_id:
                cursor.execute("""
                    SELECT TOP(?) 
                        ah.download_time,
                        c.component_name,
                        ah.artifact_version,
                        ah.branch_name,
                        ah.download_path
                    FROM artifact_history ah
                    INNER JOIN components c ON ah.component_id = c.component_id
                    WHERE ah.component_id = ?
                    ORDER BY ah.download_time DESC
                """, (limit, component_id))
            else:
                cursor.execute("""
                    SELECT TOP(?) 
                        ah.download_time,
                        c.component_name,
                        ah.artifact_version,
                        ah.branch_name,
                        ah.download_path
                    FROM artifact_history ah
                    INNER JOIN components c ON ah.component_id = c.component_id
                    ORDER BY ah.download_time DESC
                """, (limit,))
            
            rows = cursor.fetchall()
            
            print("\n" + "="*120)
            print("ARTIFACT DOWNLOAD HISTORY")
            print("="*120)
            print(f"{'Time':<20} {'Component':<25} {'Version':<20} {'Branch':<15} {'Path':<40}")
            print("-"*120)
            
            for row in rows:
                time = row[0].strftime('%Y-%m-%d %H:%M:%S')
                comp = row[1][:24]
                version = row[2][:19]
                branch = row[3][:14] if row[3] else 'N/A'
                path = row[4][:39] if row[4] else 'N/A'
                
                print(f"{time:<20} {comp:<25} {version:<20} {branch:<15} {path:<40}")
            
            print("="*120)
            
            conn.close()
            
        except Exception as e:
            print(f"[ERROR] Error showing history: {e}")
            
    def show_queue(self):
        """Show MSI build queue status"""
        try:
            conn = pyodbc.connect(self.db_connection_string)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    q.queue_id,
                    c.component_name,
                    p.project_name,
                    q.status,
                    q.queued_time,
                    q.start_time,
                    q.end_time
                FROM msi_build_queue q
                INNER JOIN components c ON q.component_id = c.component_id
                INNER JOIN projects p ON q.project_id = p.project_id
                ORDER BY q.queued_time DESC
            """)
            
            rows = cursor.fetchall()
            
            print("\n" + "="*110)
            print("MSI BUILD QUEUE")
            print("="*110)
            print(f"{'ID':<5} {'Component':<25} {'Project':<20} {'Status':<15} {'Queued':<20} {'Started':<20} {'Ended':<20}")
            print("-"*110)
            
            for row in rows:
                queue_id = row[0]
                comp = row[1][:24]
                proj = row[2][:19]
                status = row[3]
                queued = row[4].strftime('%Y-%m-%d %H:%M') if row[4] else ''
                started = row[5].strftime('%Y-%m-%d %H:%M') if row[5] else 'Not started'
                ended = row[6].strftime('%Y-%m-%d %H:%M') if row[6] else 'In progress'
                
                # Color code status
                if status == 'completed':
                    status_display = f"[OK] {status}"
                elif status == 'failed':
                    status_display = f"[X] {status}"
                elif status == 'in_progress':
                    status_display = f"[>] {status}"
                else:
                    status_display = f"[=] {status}"
                
                print(f"{queue_id:<5} {comp:<25} {proj:<20} {status_display:<15} {queued:<20} {started:<20} {ended:<20}")
            
            print("="*110)
            
            # Show summary
            pending = sum(1 for r in rows if r[3] == 'pending')
            in_progress = sum(1 for r in rows if r[3] == 'in_progress')
            completed = sum(1 for r in rows if r[3] == 'completed')
            failed = sum(1 for r in rows if r[3] == 'failed')
            
            print(f"Summary: Pending: {pending} | In Progress: {in_progress} | Completed: {completed} | Failed: {failed}")
            
            conn.close()
            
        except Exception as e:
            print(f"[ERROR] Error showing queue: {e}")
            
    def update_config(self, key: str, value: str):
        """Update JFrog configuration"""
        try:
            config_path = Path("jfrog_config.json")
            
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
            else:
                config = {}
            
            # Update the configuration
            if '.' in key:
                # Handle nested keys like repositories.snapshots
                keys = key.split('.')
                current = config
                for k in keys[:-1]:
                    if k not in current:
                        current[k] = {}
                    current = current[k]
                current[keys[-1]] = value
            else:
                config[key] = value
            
            # Save configuration
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=4)
            
            print(f"[OK] Configuration updated: {key} = {value}")
            
        except Exception as e:
            print(f"[ERROR] Error updating configuration: {e}")

def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description='Manage JFrog Artifact Polling System')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Start polling command
    parser_start = subparsers.add_parser('start', help='Start the polling service')
    
    # Configure component command
    parser_config = subparsers.add_parser('configure', help='Configure component for polling')
    parser_config.add_argument('component_id', type=int, help='Component ID')
    parser_config.add_argument('branch', help='Git branch name (e.g., develop, feature/xyz)')
    parser_config.add_argument('--disable', action='store_true', help='Disable polling')
    
    # List components command
    parser_list = subparsers.add_parser('list', help='List all components and their status')
    
    # Show history command
    parser_history = subparsers.add_parser('history', help='Show artifact download history')
    parser_history.add_argument('--component', type=int, help='Filter by component ID')
    parser_history.add_argument('--limit', type=int, default=10, help='Number of records to show')
    
    # Show queue command
    parser_queue = subparsers.add_parser('queue', help='Show MSI build queue status')
    
    # Update config command
    parser_update = subparsers.add_parser('config', help='Update configuration')
    parser_update.add_argument('key', help='Configuration key (e.g., jfrog_url)')
    parser_update.add_argument('value', help='Configuration value')
    
    args = parser.parse_args()
    
    manager = PollerManager()
    
    if args.command == 'start':
        print("Starting JFrog Artifact Polling System...")
        poller = JFrogArtifactPoller()
        try:
            poller.start_polling()
        except KeyboardInterrupt:
            poller.stop()
            print("\nPolling stopped.")
            
    elif args.command == 'configure':
        manager.configure_component(
            args.component_id,
            args.branch,
            not args.disable
        )
        
    elif args.command == 'list':
        manager.list_components()
        
    elif args.command == 'history':
        manager.show_history(args.component, args.limit)
        
    elif args.command == 'queue':
        manager.show_queue()
        
    elif args.command == 'config':
        manager.update_config(args.key, args.value)
        
    else:
        parser.print_help()

if __name__ == "__main__":
    main()