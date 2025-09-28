"""
CMDB Manager Module
Handles all Configuration Management Database operations
"""

import pyodbc
from sqlalchemy import text
from database.connection_manager import execute_with_retry
from logger import get_logger, log_info, log_error
from core.database_operations import get_db_connection

def get_cmdb_dashboard_stats():
    """Get CMDB dashboard statistics"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get CMDB statistics
        cursor.execute("""
            SELECT
                COUNT(*) as total_servers,
                SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active_servers,
                AVG(CASE WHEN max_concurrent_apps > 0 THEN CAST(current_app_count AS FLOAT) / max_concurrent_apps * 100 ELSE 0 END) as avg_utilization
            FROM cmdb_servers
            WHERE is_active = 1
        """)

        stats_row = cursor.fetchone()

        # Get assigned servers count separately
        cursor.execute("""
            SELECT COUNT(DISTINCT server_id)
            FROM project_servers
            WHERE status = 'active'
        """)
        assigned_count = cursor.fetchone()[0] or 0

        cmdb_stats = {
            'total_servers': stats_row[0] or 0,
            'active_servers': stats_row[1] or 0,
            'assigned_servers': assigned_count,
            'avg_utilization': stats_row[2] or 0
        }

        # Get infrastructure distribution
        cursor.execute("""
            SELECT infra_type, COUNT(*) as count
            FROM cmdb_servers
            WHERE is_active = 1
            GROUP BY infra_type
        """)
        infra_distribution = {row[0]: row[1] for row in cursor.fetchall()}

        # Get regional distribution
        cursor.execute("""
            SELECT region, COUNT(*) as count
            FROM cmdb_servers
            WHERE is_active = 1
            GROUP BY region
        """)
        region_distribution = {row[0]: row[1] for row in cursor.fetchall()}

        # Get recent CMDB activity
        cursor.execute("""
            SELECT TOP 10
                sc.changed_date,
                sc.change_type,
                s.server_name,
                sc.changed_by,
                sc.change_reason
            FROM cmdb_server_changes sc
            INNER JOIN cmdb_servers s ON sc.server_id = s.server_id
            ORDER BY sc.changed_date DESC
        """)

        recent_cmdb_activity = []
        for row in cursor.fetchall():
            recent_cmdb_activity.append({
                'changed_date': row[0],
                'change_type': row[1],
                'server_name': row[2],
                'changed_by': row[3],
                'change_reason': row[4]
            })

        conn.close()

        return {
            'cmdb_stats': cmdb_stats,
            'infra_distribution': infra_distribution,
            'region_distribution': region_distribution,
            'recent_cmdb_activity': recent_cmdb_activity
        }

    except Exception as e:
        log_error(f'Error loading CMDB dashboard: {str(e)}')
        return None

def get_all_cmdb_servers():
    """Get all CMDB servers"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                s.server_id,
                s.server_name,
                s.hostname,
                s.ip_address,
                s.server_type,
                s.environment,
                s.region,
                s.os,
                s.infra_type,
                s.status,
                s.max_concurrent_apps,
                s.current_app_count,
                (SELECT COUNT(*) FROM project_servers WHERE server_id = s.server_id AND status = 'active') as assigned_projects
            FROM cmdb_servers s
            WHERE s.is_active = 1
            ORDER BY s.server_name
        """)

        servers = []
        for row in cursor.fetchall():
            servers.append({
                'server_id': row[0],
                'server_name': row[1],
                'hostname': row[2],
                'ip_address': row[3],
                'server_type': row[4],
                'environment': row[5],
                'region': row[6],
                'os': row[7],
                'infra_type': row[8],
                'status': row[9],
                'max_concurrent_apps': row[10],
                'current_app_count': row[11],
                'assigned_projects': row[12]
            })

        conn.close()
        return servers

    except Exception as e:
        log_error(f'Error loading CMDB servers: {str(e)}')
        return []

def add_cmdb_server(server_data, username):
    """Add a new server to CMDB"""
    try:
        def create_server_in_db(db_session):
            server_insert = """
                INSERT INTO cmdb_servers (
                    server_name, hostname, ip_address, server_type,
                    environment, region, os, os_version, infra_type,
                    cpu_cores, memory_gb, storage_gb,
                    max_concurrent_apps, status, created_by
                )
                OUTPUT INSERTED.server_id
                VALUES (
                    :server_name, :hostname, :ip_address, :server_type,
                    :environment, :region, :os, :os_version, :infra_type,
                    :cpu_cores, :memory_gb, :storage_gb,
                    :max_concurrent_apps, :status, :created_by
                )
            """

            result = db_session.execute(text(server_insert), {
                'server_name': server_data.get('server_name'),
                'hostname': server_data.get('hostname'),
                'ip_address': server_data.get('ip_address'),
                'server_type': server_data.get('server_type', 'Application'),
                'environment': server_data.get('environment'),
                'region': server_data.get('region'),
                'os': server_data.get('os'),
                'os_version': server_data.get('os_version', ''),
                'infra_type': server_data.get('infra_type', 'Virtual'),
                'cpu_cores': int(server_data.get('cpu_cores', 4)),
                'memory_gb': int(server_data.get('memory_gb', 8)),
                'storage_gb': int(server_data.get('storage_gb', 100)),
                'max_concurrent_apps': int(server_data.get('max_concurrent_apps', 5)),
                'status': 'active',
                'created_by': username
            })

            server_id = result.fetchone()[0]

            # Record the change
            change_insert = """
                INSERT INTO cmdb_server_changes (
                    server_id, change_type, changed_by, change_reason
                )
                VALUES (:server_id, :change_type, :changed_by, :change_reason)
            """

            db_session.execute(text(change_insert), {
                'server_id': server_id,
                'change_type': 'CREATE',
                'changed_by': username,
                'change_reason': f'Server {server_data.get("server_name")} added to CMDB'
            })

            return server_id

        server_id = execute_with_retry(create_server_in_db)
        log_info(f"CMDB server added successfully with ID: {server_id}")
        return True, server_id, f'Server "{server_data.get("server_name")}" added to CMDB successfully!'

    except Exception as e:
        log_error(f"Error adding CMDB server: {e}")
        return False, None, f"Error adding server: {str(e)}"

def get_cmdb_server_details(server_id):
    """Get detailed information about a specific server"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get server details
        cursor.execute("""
            SELECT
                server_id, server_name, hostname, ip_address, server_type,
                environment, region, os, os_version, infra_type,
                cpu_cores, memory_gb, storage_gb, max_concurrent_apps,
                current_app_count, status, created_date, created_by,
                modified_date, modified_by
            FROM cmdb_servers
            WHERE server_id = ?
        """, (server_id,))

        row = cursor.fetchone()
        if not row:
            conn.close()
            return None

        server = {
            'server_id': row[0],
            'server_name': row[1],
            'hostname': row[2],
            'ip_address': row[3],
            'server_type': row[4],
            'environment': row[5],
            'region': row[6],
            'os': row[7],
            'os_version': row[8],
            'infra_type': row[9],
            'cpu_cores': row[10],
            'memory_gb': row[11],
            'storage_gb': row[12],
            'max_concurrent_apps': row[13],
            'current_app_count': row[14],
            'status': row[15],
            'created_date': row[16],
            'created_by': row[17],
            'modified_date': row[18],
            'modified_by': row[19]
        }

        # Get assigned projects
        cursor.execute("""
            SELECT
                ps.assignment_id,
                ps.project_id,
                p.project_name,
                ps.environment,
                ps.deployment_type,
                ps.assigned_date,
                ps.assigned_by
            FROM project_servers ps
            INNER JOIN projects p ON ps.project_id = p.project_id
            WHERE ps.server_id = ? AND ps.status = 'active'
            ORDER BY ps.assigned_date DESC
        """, (server_id,))

        assignments = []
        for row in cursor.fetchall():
            assignments.append({
                'assignment_id': row[0],
                'project_id': row[1],
                'project_name': row[2],
                'environment': row[3],
                'deployment_type': row[4],
                'assigned_date': row[5],
                'assigned_by': row[6]
            })

        server['assignments'] = assignments

        # Get server change history
        cursor.execute("""
            SELECT TOP 20
                changed_date,
                change_type,
                changed_by,
                change_reason
            FROM cmdb_server_changes
            WHERE server_id = ?
            ORDER BY changed_date DESC
        """, (server_id,))

        change_history = []
        for row in cursor.fetchall():
            change_history.append({
                'changed_date': row[0],
                'change_type': row[1],
                'changed_by': row[2],
                'change_reason': row[3]
            })

        server['change_history'] = change_history

        conn.close()
        return server

    except Exception as e:
        log_error(f'Error loading server details for ID {server_id}: {str(e)}')
        return None

def get_server_assignments(server_id):
    """Get all project assignments for a server"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                ps.assignment_id,
                ps.project_id,
                p.project_name,
                p.project_key,
                ps.environment,
                ps.deployment_type,
                ps.assigned_date,
                ps.assigned_by,
                ps.status
            FROM project_servers ps
            INNER JOIN projects p ON ps.project_id = p.project_id
            WHERE ps.server_id = ?
            ORDER BY ps.status DESC, ps.assigned_date DESC
        """, (server_id,))

        assignments = []
        for row in cursor.fetchall():
            assignments.append({
                'assignment_id': row[0],
                'project_id': row[1],
                'project_name': row[2],
                'project_key': row[3],
                'environment': row[4],
                'deployment_type': row[5],
                'assigned_date': row[6],
                'assigned_by': row[7],
                'status': row[8]
            })

        conn.close()
        return assignments

    except Exception as e:
        log_error(f'Error fetching server assignments for ID {server_id}: {str(e)}')
        return []

def create_server_assignment(assignment_data, username):
    """Create a new server-project assignment"""
    try:
        def create_assignment_in_db(db_session):
            # Check if assignment already exists
            check_query = text("""
                SELECT COUNT(*) FROM project_servers
                WHERE server_id = :server_id
                AND project_id = :project_id
                AND environment = :environment
                AND status = 'active'
            """)

            existing = db_session.execute(check_query, {
                'server_id': assignment_data.get('server_id'),
                'project_id': assignment_data.get('project_id'),
                'environment': assignment_data.get('environment')
            }).fetchone()[0]

            if existing > 0:
                raise ValueError("This server is already assigned to this project/environment")

            # Create the assignment
            assignment_insert = """
                INSERT INTO project_servers (
                    server_id, project_id, environment,
                    deployment_type, assigned_by, status
                )
                OUTPUT INSERTED.assignment_id
                VALUES (
                    :server_id, :project_id, :environment,
                    :deployment_type, :assigned_by, 'active'
                )
            """

            result = db_session.execute(text(assignment_insert), {
                'server_id': assignment_data.get('server_id'),
                'project_id': assignment_data.get('project_id'),
                'environment': assignment_data.get('environment'),
                'deployment_type': assignment_data.get('deployment_type', 'primary'),
                'assigned_by': username
            })

            assignment_id = result.fetchone()[0]

            # Update server's current app count
            db_session.execute(
                text("""
                    UPDATE cmdb_servers
                    SET current_app_count = (
                        SELECT COUNT(*)
                        FROM project_servers
                        WHERE server_id = :server_id
                        AND status = 'active'
                    )
                    WHERE server_id = :server_id
                """),
                {'server_id': assignment_data.get('server_id')}
            )

            # Log the change
            db_session.execute(
                text("""
                    INSERT INTO cmdb_server_changes (
                        server_id, change_type, changed_by, change_reason
                    )
                    VALUES (:server_id, 'ASSIGN', :changed_by, :change_reason)
                """),
                {
                    'server_id': assignment_data.get('server_id'),
                    'changed_by': username,
                    'change_reason': f'Assigned to project {assignment_data.get("project_id")} for {assignment_data.get("environment")} environment'
                }
            )

            return assignment_id

        assignment_id = execute_with_retry(create_assignment_in_db)
        log_info(f"Server assignment created with ID: {assignment_id}")
        return True, assignment_id, "Server assigned successfully"

    except ValueError as ve:
        return False, None, str(ve)
    except Exception as e:
        log_error(f"Error creating server assignment: {e}")
        return False, None, f"Error creating assignment: {str(e)}"

def get_cmdb_utilization():
    """Get CMDB utilization metrics"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get utilization by server
        cursor.execute("""
            SELECT
                server_name,
                environment,
                region,
                max_concurrent_apps,
                current_app_count,
                CASE
                    WHEN max_concurrent_apps > 0
                    THEN (CAST(current_app_count AS FLOAT) / max_concurrent_apps * 100)
                    ELSE 0
                END as utilization_percent
            FROM cmdb_servers
            WHERE is_active = 1 AND status = 'active'
            ORDER BY utilization_percent DESC
        """)

        server_utilization = []
        for row in cursor.fetchall():
            server_utilization.append({
                'server_name': row[0],
                'environment': row[1],
                'region': row[2],
                'max_apps': row[3],
                'current_apps': row[4],
                'utilization': row[5]
            })

        # Get utilization summary by environment
        cursor.execute("""
            SELECT
                environment,
                COUNT(*) as total_servers,
                AVG(CAST(current_app_count AS FLOAT)) as avg_apps,
                AVG(CASE
                    WHEN max_concurrent_apps > 0
                    THEN (CAST(current_app_count AS FLOAT) / max_concurrent_apps * 100)
                    ELSE 0
                END) as avg_utilization
            FROM cmdb_servers
            WHERE is_active = 1 AND status = 'active'
            GROUP BY environment
        """)

        environment_summary = []
        for row in cursor.fetchall():
            environment_summary.append({
                'environment': row[0],
                'total_servers': row[1],
                'avg_apps': row[2],
                'avg_utilization': row[3]
            })

        conn.close()
        return {
            'server_utilization': server_utilization,
            'environment_summary': environment_summary
        }

    except Exception as e:
        log_error(f'Error fetching CMDB utilization: {str(e)}')
        return None

def get_cmdb_groups():
    """Get CMDB server groups and clusters"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get servers grouped by various attributes
        cursor.execute("""
            SELECT
                environment,
                region,
                server_type,
                COUNT(*) as server_count,
                STRING_AGG(server_name, ', ') as servers
            FROM cmdb_servers
            WHERE is_active = 1
            GROUP BY environment, region, server_type
            ORDER BY environment, region, server_type
        """)

        groups = []
        for row in cursor.fetchall():
            groups.append({
                'environment': row[0],
                'region': row[1],
                'server_type': row[2],
                'server_count': row[3],
                'servers': row[4]
            })

        conn.close()
        return groups

    except Exception as e:
        log_error(f'Error fetching CMDB groups: {str(e)}')
        return []